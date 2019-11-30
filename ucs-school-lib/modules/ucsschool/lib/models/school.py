# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2019 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

from typing import List

import ldap
import univention.admin.modules
import univention.admin.objects
from ldap.dn import escape_dn_chars
from ldap.filter import escape_filter_chars, filter_format
from univention.admin.uexceptions import noObject
from univention.config_registry import handler_set

from ..roles import (
	create_ucsschool_role_string,
	role_dc_slave_admin,
	role_dc_slave_edu,
	role_school,
	role_school_admin_group,
	role_school_domain_group,
	role_school_staff_group,
	role_school_student_group,
	role_school_teacher_group,
)
from .attributes import (
	Attribute,
	DCName,
	DisplayName,
	Roles,
	SchoolName,
	ShareFileServer,
)
from .base import RoleSupportMixin, UCSSchoolHelperAbstractClass
from .computer import AnyComputer, SchoolDC, SchoolDCSlave
from .dhcp import DHCPService
from .group import BasicGroup, BasicSchoolGroup, Group
from .misc import OU, Container
from .policy import DHCPDNSPolicy
from .utils import _, flatten, ucr


class School(RoleSupportMixin, UCSSchoolHelperAbstractClass):
	name: str = SchoolName(_('School name'))
	dc_name: str = DCName(_('DC Name'))
	dc_name_administrative: str = DCName(_('DC Name administrative server'))
	class_share_file_server: str = ShareFileServer(_('Server for class shares'), udm_name='ucsschoolClassShareFileServer')
	home_share_file_server: str = ShareFileServer(_('Server for Windows home directories'), udm_name='ucsschoolHomeShareFileServer')
	display_name: str = DisplayName(_('Display name'))
	school: str = None
	educational_servers: List[str] = Attribute(_('Educational servers'), unlikely_to_change=True)
	administrative_servers: List[str] = Attribute(_('Administrative servers'), unlikely_to_change=True)
	ucsschool_roles: List[str] = Roles(_('Roles'), aka=['Roles'])

	default_roles = [role_school]
	_school_in_name = True

	def __init__(self, name=None, school=None, alter_dhcpd_base=None, **kwargs):
		super(School, self).__init__(name=name, **kwargs)
		self.display_name = self.display_name or self.name
		self.alter_dhcpd_base = alter_dhcpd_base if alter_dhcpd_base is not None else not bool(ucr.get('dhcpd/ldap/base', ''))

	async def validate(self, lo, validate_unlikely_changes=False):
		await super(School, self).validate(lo, validate_unlikely_changes)
		if self.dc_name and self.dc_name == self.dc_name_administrative:
			self.add_error('dc_name', _('Hostname of educational DC and administrative DC must not be equal'))
			self.add_error('dc_name_administrative', _('Hostname of educational DC and administrative DC must not be equal'))
		if self.dc_name:
			ldap_filter_str = ''
			if ucr.is_true('ucsschool/singlemaster'):
				ldap_filter_str = filter_format(
					'(&(objectClass=univentionDomainController)(cn=%s)(univentionServerRole=backup))',
					[self.dc_name.lower()])
			else:
				ldap_filter_str = filter_format(
					'(&(objectClass=univentionDomainController)(cn=%s)(|(univentionServerRole=backup)(univentionServerRole=master)))',
					[self.dc_name.lower()])
			dcs = lo.search(ldap_filter_str)
			if len(dcs) and ucr.is_true('ucsschool/singlemaster'):
				self.add_error('dc_name', 'The educational DC for the school must not be a backup server')
			elif len(dcs):
				self.add_error('dc_name', 'The educational DC for the school must not be a backup or master server')

	def get_district(self):
		if ucr.is_true('ucsschool/ldap/district/enable'):
			return self.name[:2]

	def get_own_container(self):
		district = self.get_district()
		if district:
			return 'ou=%s,%s' % (escape_dn_chars(district), self.get_container())
		return self.get_container()

	@classmethod
	def get_container(cls, school=None):
		return ucr.get('ldap/base')

	@classmethod
	def cn_name(cls, name, default):
		ucr_var = 'ucsschool/ldap/default/container/%s' % name
		return ucr.get(ucr_var, default)

	async def create_default_containers(self, lo):
		cn_pupils = self.cn_name('pupils', 'schueler')
		cn_teachers = self.cn_name('teachers', 'lehrer')
		cn_admins = self.cn_name('admins', 'admins')
		cn_classes = self.cn_name('class', 'klassen')
		cn_rooms = self.cn_name('rooms', 'raeume')
		user_containers = [cn_pupils, cn_teachers, cn_admins]
		group_containers = [cn_pupils, [cn_classes], cn_teachers, cn_rooms]
		if self.shall_create_administrative_objects():
			cn_staff = self.cn_name('staff', 'mitarbeiter')
			cn_teachers_staff = self.cn_name('teachers-and-staff', 'lehrer und mitarbeiter')
			user_containers.extend([cn_staff, cn_teachers_staff])
			group_containers.append(cn_staff)
		containers_with_path = {
			'printer_path': ['printers'],
			'user_path': ['users', user_containers],
			'computer_path': ['computers', ['server', ['dc']]],
			'network_path': ['networks'],
			'group_path': ['groups', group_containers],
			'dhcp_path': ['dhcp'],
			'policy_path': ['policies'],
			'share_path': ['shares', [cn_classes]],
		}

		async def _add_container(name, last_dn, base_dn, path, lo):
			if isinstance(name, (list, tuple)):
				base_dn = last_dn
				for cn in name:
					last_dn = await _add_container(cn, last_dn, base_dn, path, lo)
			else:
				container = Container(name=name, school=self.name)
				setattr(container, path, '1')
				container.position = base_dn
				last_dn = container.dn
				if not await container.exists(lo):
					last_dn = await container.create(lo, False)
			return last_dn

		last_dn = self.dn
		path = None
		for path, containers in containers_with_path.items():
			for cn in containers:
				last_dn = await _add_container(cn, last_dn, self.dn, path, lo)

	def group_name(self, prefix_var, default_prefix):
		ucr_var = 'ucsschool/ldap/default/groupprefix/%s' % prefix_var
		name_part = ucr.get(ucr_var, default_prefix)
		school_part = self.name.lower()
		return '%s%s' % (name_part, school_part)

	def get_umc_policy_dn(self, name):
		# at least the default ones should exist due to the join script
		return ucr.get('ucsschool/ldap/default/policy/umc/%s' % name, 'cn=ucsschool-umc-%s-default,cn=UMC,cn=policies,%s' % (name, ucr.get('ldap/base')))

	async def create_default_groups(self, lo):
		# DC groups
		administrative_group_container = 'cn=ucsschool,cn=groups,%s' % ucr.get('ldap/base')

		# DC-Edukativnetz
		# OU%s-DC-Edukativnetz
		# Member-Edukativnetz
		# OU%s-Member-Edukativnetz
		administrative_group_names = self.get_administrative_group_name('educational', domain_controller='both', ou_specific='both')
		if self.shall_create_administrative_objects():
			administrative_group_names.extend(self.get_administrative_group_name('administrative', domain_controller='both', ou_specific='both'))  # same with Verwaltungsnetz
		for administrative_group_name in administrative_group_names:
			group = BasicGroup.cache(name=administrative_group_name, container=administrative_group_container)
			group.create(lo)

		# cn=ouadmins
		admin_group_container = 'cn=ouadmins,cn=groups,%s' % ucr.get('ldap/base')
		group = BasicSchoolGroup.cache(self.group_name('admins', 'admins-'), self.name, container=admin_group_container)
		group.ucsschool_roles = [create_ucsschool_role_string(role_school_admin_group, self.name)]
		group.create(lo)
		await group.add_umc_policy(self.get_umc_policy_dn('admins'), lo)
		try:
			udm_obj = group.get_udm_object(lo)
		except noObject:
			self.logger.error('Could not load OU admin group %r for adding "school" value', group.dn)
		else:
			admin_option = 'ucsschoolAdministratorGroup'
			if admin_option not in udm_obj.options:
				udm_obj.options.append(admin_option)
			udm_obj['school'] = [self.name]
			udm_obj.modify()

		# cn=schueler
		group = Group.cache(self.group_name('pupils', 'schueler-'), self.name)
		group.ucsschool_roles = [create_ucsschool_role_string(role_school_student_group, self.name)]
		group.create(lo)
		await group.add_umc_policy(self.get_umc_policy_dn('pupils'), lo)

		# cn=lehrer
		group = Group.cache(self.group_name('teachers', 'lehrer-'), self.name)
		group.ucsschool_roles = [create_ucsschool_role_string(role_school_teacher_group, self.name)]
		group.create(lo)
		await group.add_umc_policy(self.get_umc_policy_dn('teachers'), lo)

		# cn=mitarbeiter
		if self.shall_create_administrative_objects():
			group = Group.cache(self.group_name('staff', 'mitarbeiter-'), self.name)
			group.ucsschool_roles = [create_ucsschool_role_string(role_school_staff_group, self.name)]
			group.create(lo)
			await group.add_umc_policy(self.get_umc_policy_dn('staff'), lo)

		# cn=Domain Users %s
		group = Group.cache("Domain Users %s" % (self.name,), self.name)
		group.ucsschool_roles = [create_ucsschool_role_string(role_school_domain_group, self.name)]
		group.create(lo)
		if ucr.is_true('ucsschool/import/attach/policy/default-umc-users', True):
			await group.add_umc_policy("cn=default-umc-users,cn=UMC,cn=policies,%s" % (ucr.get('ldap/base'),), lo)

	def get_dc_name_fallback(self, administrative=False):
		if administrative:
			return 'dc%sv-01' % self.name.lower()  # this is the naming convention, a trailing v for Verwaltungsnetz DCs
		else:
			return 'dc%s-01' % self.name.lower()

	def get_dc_name(self, administrative=False):
		if ucr.is_true('ucsschool/singlemaster', False):
			return ucr.get('hostname')
		elif self.dc_name:
			if administrative:
				return '%sv' % self.dc_name
			else:
				return self.dc_name
		else:
			return self.get_dc_name_fallback(administrative=administrative)

	def get_share_fileserver_dn(self, set_by_self, lo):
		if set_by_self:
			set_by_self = self.get_name_from_dn(set_by_self) or set_by_self
		hostname = set_by_self or self.get_dc_name()
		if hostname == self.get_dc_name_fallback():
			# does not matter if exists or not - dc object will be created later
			host = SchoolDC(name=hostname, school=self.name)
			return host.dn

		host = AnyComputer.get_first_udm_obj(lo, 'cn=%s' % escape_filter_chars(hostname))
		if host:
			return host.dn
		else:
			self.logger.warning('Could not find %s. Using this host as ShareFileServer ("%s").', hostname, ucr.get('hostname'))
			return ucr.get('ldap/hostdn')

	def get_class_share_file_server(self, lo):
		return self.get_share_fileserver_dn(self.class_share_file_server, lo)

	def get_home_share_file_server(self, lo):
		return self.get_share_fileserver_dn(self.home_share_file_server, lo)

	def get_administrative_group_name(self, group_type, domain_controller=True, ou_specific=False, as_dn=False):
		if domain_controller == 'both':
			return flatten([self.get_administrative_group_name(group_type, True, ou_specific, as_dn), self.get_administrative_group_name(group_type, False, ou_specific, as_dn)])
		if ou_specific == 'both':
			return flatten([self.get_administrative_group_name(group_type, domain_controller, False, as_dn), self.get_administrative_group_name(group_type, domain_controller, True, as_dn)])
		if group_type == 'administrative':
			name = 'Verwaltungsnetz'
		else:
			name = 'Edukativnetz'
		if domain_controller:
			name = 'DC-%s' % name
		else:
			name = 'Member-%s' % name
		if ou_specific:
			name = 'OU%s-%s' % (self.name.lower(), name)
		if as_dn:
			return 'cn=%s,cn=ucsschool,cn=groups,%s' % (name, ucr.get('ldap/base'))
		else:
			return name

	def get_administrative_server_names(self, lo):
		dn = self.get_administrative_group_name('administrative', ou_specific=True, as_dn=True)
		# TODO: this should also be done in 4.4
		mod = univention.admin.modules.get('groups/group')
		udm_obj = mod.get(dn)
		return udm_obj['hosts']

	def get_educational_server_names(self, lo):
		dn = self.get_administrative_group_name('educational', ou_specific=True, as_dn=True)
		# TODO: this should also be done in 4.4
		mod = univention.admin.modules.get('groups/group')
		udm_obj = mod.get(dn)
		return udm_obj['hosts']

	async def add_host_to_dc_group(self, lo):
		self.logger.info('School.add_host_to_dc_group(): ou_name=%r  dc_name=%r', self.name, self.dc_name)
		if self.dc_name:
			dc_name_l = self.dc_name.lower()
			dc_udm_obj = None
			mb_dcs = lo.search(filter_format('(&(objectClass=univentionDomainController)(cn=%s)(|(univentionServerRole=backup)(univentionServerRole=master)))', [self.dc_name.lower()]))
			if len(mb_dcs):
				return  # We do not modify the groups of master or backup servers.
				# Should be validated, but stays here as well in case validation was deactivated
			po = univention.admin.uldap.position(lo.base)  # Sadly we need this here to access non school specific computers. TODO: Use Daniels simple API if merged into product
			univention.admin.modules.update()
			mod = univention.admin.modules.get('computers/domaincontroller_slave')
			if not mod.initialized:
				univention.admin.modules.init(lo, po, mod)
			slave_dcs = lo.search('(&(objectClass=univentionDomainController)(cn={})(univentionServerRole=slave))'.format(dc_name_l))
			if len(slave_dcs):
				dn, attr = slave_dcs[0]
				dc_udm_obj = univention.admin.objects.get(mod, None, lo, po, dn)
				dc_udm_obj.open()
			if not dc_udm_obj:
				roles = [create_ucsschool_role_string(role_dc_slave_edu, self.name)]
				dc = SchoolDCSlave(name=self.dc_name, school=self.name, ucsschool_roles=roles)
				await dc.create(lo)
				dc_udm_obj = await dc.get_udm_object(lo)
			else:
				dc = await SchoolDCSlave.from_udm_obj(SchoolDCSlave.get_first_udm_obj(lo, 'cn={}'.format(self.dc_name)), self.name, lo)
				if dc:
					dc.ucsschool_roles = [create_ucsschool_role_string(role_dc_slave_edu, self.name)]
					await dc.modify(lo)
			groups = self.get_administrative_group_name('educational', ou_specific='both', as_dn=True)
			for grp in groups:
				if grp not in dc_udm_obj['groups']:
					dc_udm_obj['groups'].append(grp)
			await dc_udm_obj.modify()

	def shall_create_administrative_objects(self):
		return ucr.is_true('ucsschool/ldap/noneducational/create/objects', True)

	async def create_dc_slave(self, lo, name, administrative=False):
		if administrative and not self.shall_create_administrative_objects():
			self.logger.warning('Not creating %s: An administrative DC shall not be created as by UCR variable %r', name, 'ucsschool/ldap/noneducational/create/objects')
			return False
		if not await self.exists(lo):
			self.logger.error('%r does not exist. Cannot create %s', self, name)
			return False
		if administrative:
			groups = self.get_administrative_group_name('administrative', ou_specific='both', as_dn=True)
		else:
			groups = self.get_administrative_group_name('educational', ou_specific='both', as_dn=True)
		self.logger.debug('DC shall become member of %r', groups)

		roles = [create_ucsschool_role_string(role_dc_slave_admin if administrative else role_dc_slave_edu, self.name)]
		dc = SchoolDCSlave(name=name, school=self.name, groups=groups, ucsschool_roles=roles)
		if await dc.exists(lo):
			self.logger.info('%r exists. Setting groups, do not move to %r!', dc, self)
			# call dc.move() if really necessary to move
			return dc.modify(lo, move_if_necessary=False)
		else:
			existing_host = AnyComputer.get_first_udm_obj(lo, 'cn=%s' % escape_filter_chars(name))
			if existing_host:
				self.logger.error('Given host name "%s" is already in use and no domaincontroller slave system. Please choose another name.', name)
				return False
			return dc.create(lo)

	def add_domain_controllers(self, lo):
		self.logger.info('School.add_domain_controllers(): ou_name=%r', self.name)
		school_dcs = ucr.get('ucsschool/ldap/default/dcs', 'edukativ').split()
		for dc in school_dcs:
			administrative = dc == 'verwaltung'
			dc_name = self.get_dc_name(administrative=administrative)
			server = AnyComputer.get_first_udm_obj(lo, 'cn=%s' % escape_filter_chars(dc_name))
			self.logger.info('School.add_domain_controllers(): administrative=%r  dc_name=%s  self.dc_name=%r  server=%r', administrative, dc_name, self.dc_name, server)
			if not server and not self.dc_name:
				if administrative:
					administrative_type = 'administrative'
				else:
					administrative_type = 'educational'
				group_dn = self.get_administrative_group_name(administrative_type, ou_specific=True, as_dn=True)
				try:
					hostlist = lo.get(group_dn, ['uniqueMember']).get('uniqueMember', [])
				except ldap.NO_SUCH_OBJECT:
					hostlist = []
				except Exception as exc:
					self.logger.error('cannot read %s: %s', group_dn, exc)
					return

				if hostlist:
					continue  # if at least one DC has control over this OU then jump to next 'school_dcs' item ==> do not create default slave objects

				self.create_dc_slave(lo, dc_name, administrative=administrative)

			dhcp_service = self.get_dhcp_service(dc_name)
			dhcp_service.create(lo)
			dhcp_service.add_server(dc_name, lo)
			return True

	def get_dhcp_service(self, hostname=None):
		return DHCPService.cache(self.name.lower(), self.name, hostname=hostname, domainname=ucr.get('domainname'))

	async def create_without_hooks(self, lo, validate):
		district = self.get_district()
		if district:
			ou = OU(name=district)
			ou.position = ucr.get('ldap/base')
			await ou.create(lo, False)

		# setting class_share_file_server and home_share_file_server:
		# 1. set to None
		# 2. create school
		# 3. (maybe) create file_servers <- that is why this is necessary
		# 4. set file_servers
		# 5. modify school
		saved_class_share_file_server = self.class_share_file_server
		saved_home_share_file_server = self.home_share_file_server
		self.class_share_file_server = None
		self.home_share_file_server = None

		try:
			success = await super(School, self).create_without_hooks(lo, validate)
			if not success:
				self.logger.warning('Creating %r failed (maybe it already exists?)! Trying to set it up nonetheless', self)
				await self.modify_without_hooks(lo)

			if self.alter_dhcpd_base and ucr.is_true('ucsschool/singlemaster', False):
				handler_set(['dhcpd/ldap/base=cn=dhcp,%s' % (self.dn)])
				ucr.load()

			await self.create_default_containers(lo)
			await self.create_default_groups(lo)
			await self.add_host_to_dc_group(lo)
			if not self.add_domain_controllers(lo):
				return False
			if self.dc_name_administrative:
				await self.create_dc_slave(lo, self.dc_name_administrative, administrative=True)
				dhcp_service = self.get_dhcp_service(self.dc_name_administrative)
				dhcp_service.create(lo)
				dhcp_service.add_server(self.dc_name_administrative, lo)
		finally:
			self.logger.debug('Resetting share file servers from None to %r and %r', saved_home_share_file_server, saved_class_share_file_server)
			self.class_share_file_server = saved_class_share_file_server
			self.home_share_file_server = saved_home_share_file_server
		self.class_share_file_server = self.get_class_share_file_server(lo)
		self.home_share_file_server = self.get_home_share_file_server(lo)
		self.logger.debug('Now it is %r and %r - %r should be modified accordingly', self.home_share_file_server, self.class_share_file_server, self)
		await self.modify_without_hooks(lo)

		# if requested, then create dhcp_dns policy that clears univentionDhcpDomainNameServers at OU level
		# to prevent problems with "wrong" DHCP DNS policy connected to ldap base
		if ucr.is_true('ucsschool/import/generate/policy/dhcp/dns/clearou', False):
			policy = DHCPDNSPolicy(name='dhcp-dns-clear', school=self.name, empty_attributes=['univentionDhcpDomainNameServers'])
			await policy.create(lo)
			policy.attach(self, lo)

		return success

	def get_schools(self):
		return {self.name}

	async def _alter_udm_obj(self, udm_obj):
		udm_obj.options.append('UCSschool-School-OU')
		return await super(School, self)._alter_udm_obj(udm_obj)

	@classmethod
	async def from_binddn(cls, lo):
		cls.logger.debug('All local schools: Showing all OUs which DN %s can read.', lo.binddn)
		# get all schools of the user which are present on this server
		user_schools = lo.search(base=lo.binddn, scope='base', attr=['ucsschoolSchool'])[0][1].get('ucsschoolSchool', [])
		if user_schools:
			schools = []
			for ou in user_schools:
				try:
					schools.append(await cls.from_dn(cls(name=ou).dn, None, lo))
				except noObject:
					pass
			return cls._filter_local_schools(schools, lo)

		if 'ou=' in lo.binddn:
			# user has no ucsschoolSchool attribute (not migrated yet)
			# we got an OU in the user DN -> school teacher or assistent
			# restrict the visibility to current school
			# (note that there can be schools with a DN such as ou=25g18,ou=25,dc=...)
			school_dn = lo.binddn[lo.binddn.find('ou='):]
			cls.logger.debug('Schools from binddn: Found an OU in the LDAP binddn. Restricting schools to only show %s', school_dn)
			school = await cls.from_dn(school_dn, None, lo)
			cls.logger.debug('Schools from binddn: Found school: %r', school)
			return cls._filter_local_schools([school], lo)

		cls.logger.warning('Schools from binddn: Unable to identify OU of this account - showing all local OUs!')
		return await School.get_all(lo)

	@classmethod
	async def from_udm_obj(cls, udm_obj, school, lo):
		obj = await super(School, cls).from_udm_obj(udm_obj, school, lo)
		obj.educational_servers = obj.get_educational_server_names(lo)
		obj.administrative_servers = obj.get_administrative_server_names(lo)
		return obj

	@classmethod
	async def get_all(cls, lo, filter_str=None, easy_filter=False, respect_local_oulist=True):
		schools = await super(School, cls).get_all(lo, school=None, filter_str=filter_str, easy_filter=easy_filter)
		oulist = ucr.get('ucsschool/local/oulist')
		if oulist and respect_local_oulist:
			cls.logger.debug('All Schools: Schools overridden by UCR variable ucsschool/local/oulist')
			ous = [x.strip() for x in oulist.split(',')]
			schools = [school for school in schools if school.name in ous]
		return cls._filter_local_schools(schools, lo)

	@classmethod
	def _filter_local_schools(cls, schools, lo):
		if ucr.get('server/role') in ('domaincontroller_master', 'domaincontroller_backup'):
			return schools
		return [school for school in schools if any(ucr.get('ldap/hostdn', '').lower() == x.lower() for x in school.get_administrative_server_names(lo) + school.get_educational_server_names(lo))]

	@classmethod
	def _attrs_for_easy_filter(cls):
		return super(cls, School)._attrs_for_easy_filter() + ['displayName']

	@classmethod
	def invalidate_cache(cls):
		from ucsschool.lib.models.user import User
		super(School, cls).invalidate_cache()
		User._samba_home_path_cache.clear()

	def __str__(self):
		return self.name

	class Meta:
		udm_module = 'container/ou'
		udm_filter = 'objectClass=ucsschoolOrganizationalUnit'
		ldap_name_part = 'ou'
