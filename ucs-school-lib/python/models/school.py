#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014 Univention GmbH
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

import ldap
from ldap.filter import escape_filter_chars

from univention.config_registry import handler_set

from ucsschool.lib.models.attributes import SchoolName, DCName, ShareFileServer, DisplayName
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models.group import BasicGroup, Group
from ucsschool.lib.models.dhcp import DHCPService
from ucsschool.lib.models.policy import DHCPDNSPolicy
from ucsschool.lib.models.misc import Container, OU
from ucsschool.lib.models.computer import AnyComputer, SchoolDCSlave, SchoolDC
from ucsschool.lib.models.utils import flatten, ucr, _, logger

class School(UCSSchoolHelperAbstractClass):
	name = SchoolName(_('School name'))
	dc_name = DCName(_('DC Name'))
	dc_name_administrative = DCName(_('DC Name administrative server'))
	class_share_file_server = ShareFileServer(_('Server for class shares'), udm_name='ucsschoolClassShareFileServer')
	home_share_file_server = ShareFileServer(_('Server for Windows home directories'), udm_name='ucsschoolHomeShareFileServer')
	display_name = DisplayName(_('Display name'))
	school = None

	def __init__(self, name=None, school=None, **kwargs):
		super(School, self).__init__(name=name, **kwargs)
		self.display_name = self.display_name or self.name

	def build_hook_line(self, hook_time, func_name):
		if func_name == 'create':
			return self._build_hook_line(self.name, self.get_dc_name(or_fallback=False))

	def get_district(self):
		if ucr.is_true('ucsschool/ldap/district/enable'):
			return self.name[:2]

	def get_own_container(self):
		district = self.get_district()
		if district:
			return 'ou=%s,%s' % (district, self.get_container())
		return self.get_container()

	@classmethod
	def get_container(cls, school=None):
		return ucr.get('ldap/base')

	@classmethod
	def cn_name(cls, name, default):
		ucr_var = 'ucsschool/ldap/default/container/%s' % name
		return ucr.get(ucr_var, default)

	def create_default_containers(self, lo):
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
			'user_path' : ['users', user_containers],
			'computer_path' : ['computers', ['server', ['dc']]],
			'network_path' : ['networks'],
			'group_path' : ['groups', group_containers],
			'dhcp_path' : ['dhcp'],
			'policy_path' : ['policies'],
			'share_path' : ['shares', [cn_classes]],
		}

		def _add_container(name, last_dn, base_dn, path, lo):
			if isinstance(name, (list, tuple)):
				base_dn = last_dn
				for cn in name:
					last_dn = _add_container(cn, last_dn, base_dn, path, lo)
			else:
				container = Container(name=name, school=self.name)
				setattr(container, path, '1')
				last_dn = container.create_in_container(base_dn, lo)
			return last_dn

		last_dn = self.dn
		path = None
		for path, containers in containers_with_path.iteritems():
			for cn in containers:
				last_dn = _add_container(cn, last_dn, self.dn, path, lo)

	def group_name(self, prefix_var, default_prefix):
		ucr_var = 'ucsschool/ldap/default/groupprefix/%s' % prefix_var
		name_part = ucr.get(ucr_var, default_prefix)
		school_part = self.name.lower()
		return '%s%s' % (name_part, school_part)

	def get_umc_policy_dn(self, name):
		# at least the default ones should exist due to the join script
		return ucr.get('ucsschool/ldap/default/policy/umc/%s' % name, 'cn=ucsschool-umc-%s-default,cn=UMC,cn=policies,%s' % (name, ucr.get('ldap/base')))

	def create_default_groups(self, lo):
		# DC groups
		administrative_group_container = 'cn=ucsschool,cn=groups,%s' % ucr.get('ldap/base')

		# DC-Edukativnetz
		# OU%s-DC-Edukativnetz
		# Member-Edukativnetz
		# OU%s-Member-Edukativnetz
		administrative_group_names = self.get_administrative_group_name('educational', domain_controller='both', ou_specific='both')
		if self.shall_create_administrative_objects():
			administrative_group_names.extend(self.get_administrative_group_name('administrative', domain_controller='both', ou_specific='both')) # same with Verwaltungsnetz
		for administrative_group_name in administrative_group_names:
			group = BasicGroup.cache(name=administrative_group_name, container=administrative_group_container)
			group.create(lo)

		# cn=ouadmins
		admin_group_container = 'cn=ouadmins,cn=groups,%s' % ucr.get('ldap/base')
		group = BasicGroup.cache(self.group_name('admins', 'admins-'), container=admin_group_container)
		group.create(lo)
		group.add_umc_policy(self.get_umc_policy_dn('admins'), lo)

		# cn=schueler
		group = Group.cache(self.group_name('pupils', 'schueler-'), self.name)
		group.create(lo)
		group.add_umc_policy(self.get_umc_policy_dn('pupils'), lo)

		# cn=lehrer
		group = Group.cache(self.group_name('teachers', 'lehrer-'), self.name)
		group.create(lo)
		group.add_umc_policy(self.get_umc_policy_dn('teachers'), lo)

		# cn=mitarbeiter
		if self.shall_create_administrative_objects():
			group = Group.cache(self.group_name('staff', 'mitarbeiter-'), self.name)
			group.create(lo)
			group.add_umc_policy(self.get_umc_policy_dn('staff'), lo)

	def get_dc_name_fallback(self, administrative=False):
		if administrative:
			return 'dc%sv-01' % self.name.lower() # this is the naming convention, a trailing v for Verwaltungsnetz DCs
		else:
			return 'dc%s-01' % self.name.lower()

	def get_dc_name(self, administrative=False, or_fallback=True):
		if ucr.is_true('ucsschool/singlemaster', False):
			return ucr.get('hostname')
		elif self.dc_name:
			if administrative:
				return '%sv' % self.dc_name
			else:
				return self.dc_name
		else:
			if or_fallback:
				return self.get_dc_name_fallback(administrative=administrative)
			else:
				return None

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
			logger.warning('Could not find %s. Using this host as ShareFileServer ("%s").' % (hostname, ucr.get('hostname')))
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

	def add_host_to_dc_group(self, lo):
		logger.info('School.add_host_to_dc_group(): ou_name=%r  dc_name=%r' % (self.name, self.dc_name))
		if self.dc_name:
			dc = SchoolDCSlave(name=self.dc_name, school=self.name)
			dc.create(lo)
			dc_udm_obj = dc.get_udm_object(lo)
			groups = self.get_administrative_group_name('educational', ou_specific='both', as_dn=True)
			for grp in groups:
				if grp not in dc_udm_obj['groups']:
					dc_udm_obj['groups'].append(grp)
			dc_udm_obj.modify()

	def shall_create_administrative_objects(self):
		return ucr.is_true('ucsschool/ldap/noneducational/create/objects', True)

	def create_dc_slave(self, lo, name, administrative=False):
		if administrative and not self.shall_create_administrative_objects():
			logger.warning('Not creating %s: An administrative DC shall not be created as by UCR variable %r' % (name, 'ucsschool/ldap/noneducational/create/objects'))
			return False
		if not self.exists(lo):
			logger.error('%r does not exist. Cannot create %s' % (self, name))
			return False
		if administrative:
			groups = self.get_administrative_group_name('administrative', ou_specific='both', as_dn=True)
		else:
			groups = self.get_administrative_group_name('educational', ou_specific='both', as_dn=True)
		logger.debug('DC shall become member of %r' % groups)

		dc = SchoolDCSlave(name=name, school=self.name, groups=groups)
		if dc.exists(lo):
			logger.info('%r exists. Setting groups, do not move to %r!' % (dc, self))
			# call dc.move() if really necessary to move
			return dc.modify(lo, move_if_necessary=False)
		else:
			existing_host = AnyComputer.get_first_udm_obj(lo, 'cn=%s' % escape_filter_chars(name))
			if existing_host:
				logger.error('Given host name "%s" is already in use and no domaincontroller slave system. Please choose another name.' % name)
				return False
			return dc.create(lo)

	def add_domain_controllers(self, lo):
		logger.info('School.add_domain_controllers(): ou_name=%r' % self.name)
		school_dcs = ucr.get('ucsschool/ldap/default/dcs', 'edukativ').split()
		for dc in school_dcs:
			administrative = dc == 'verwaltung'
			dc_name = self.get_dc_name(administrative=administrative)
			server = AnyComputer.get_first_udm_obj(lo, 'cn=%s' % escape_filter_chars(dc_name))
			logger.info('School.add_domain_controllers(): administrative=%r  dc_name=%s  self.dc_name=%r  server=%r' % (administrative, dc_name, self.dc_name, server))
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
				except Exception, e:
					logger.error('cannot read %s: %s' % (group_dn, e))
					return

				if hostlist:
					continue # if at least one DC has control over this OU then jump to next 'school_dcs' item ==> do not create default slave objects

				self.create_dc_slave(lo, dc_name, administrative=administrative)

			dhcp_service = self.get_dhcp_service(dc_name)
			dhcp_service.create(lo)
			dhcp_service.add_server(dc_name, lo)
			return True

	def get_dhcp_service(self, hostname=None):
		return DHCPService.cache(self.name.lower(), self.name, hostname=hostname, domainname=ucr.get('domainname'))

	def create_without_hooks(self, lo, validate):
		district = self.get_district()
		if district:
			ou = OU(name=district)
			ou.create_in_container(ucr.get('ldap/base'), lo)

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
			success = super(School, self).create_without_hooks(lo, validate)
			if not success:
				logger.warning('Creating %r failed (maybe it already exists?)! Trying to set it up nonetheless')
				self.modify_without_hooks(lo)

			# In a single server environment the default DHCP container must
			# be set to the DHCP container in the school ou. Otherwise newly
			# imported computers have the DHCP objects in the wrong DHCP container
			if ucr.is_true('ucsschool/singlemaster', False):
				if not ucr.get('dhcpd/ldap/base'):
					handler_set(['dhcpd/ldap/base=cn=dhcp,%s' % (self.dn)])
					ucr.load()

			self.create_default_containers(lo)
			self.create_default_groups(lo)
			self.add_host_to_dc_group(lo)
			if not self.add_domain_controllers(lo):
				return False
			if self.dc_name_administrative:
				self.create_dc_slave(lo, self.dc_name_administrative, administrative=True)
		finally:
			logger.debug('Resetting share file servers from None to %r and %r' % (saved_home_share_file_server, saved_class_share_file_server))
			self.class_share_file_server = saved_class_share_file_server
			self.home_share_file_server = saved_home_share_file_server
		self.class_share_file_server = self.get_class_share_file_server(lo)
		self.home_share_file_server = self.get_home_share_file_server(lo)
		logger.debug('Now it is %r and %r - %r should be modified accordingly' % (self.home_share_file_server, self.class_share_file_server, self))
		self.modify_without_hooks(lo)

		# if requested, then create dhcp_dns policy that clears univentionDhcpDomainNameServers at OU level
		# to prevent problems with "wrong" DHCP DNS policy connected to ldap base
		if ucr.is_true('ucsschool/import/generate/policy/dhcp/dns/clearou', False):
			policy = DHCPDNSPolicy(name='dhcp-dns-clear', school=self.name, empty_attributes=['univentionDhcpDomainNameServers'])
			policy.create(lo)
			policy.attach(self, lo)

		return success

	def _alter_udm_obj(self, udm_obj):
		udm_obj.options = ['UCSschool-School-OU']
		return super(School, self)._alter_udm_obj(udm_obj)

	@classmethod
	def get_from_oulist(cls, lo, oulist):
		ous = [x.strip() for x in oulist.split(',')]
		schools = []
		for ou in ous:
			logger.debug('All Schools: Getting OU %s' % ou)
			school = cls.from_dn(cls(name=ou).dn, None, lo)
			logger.debug('All Schools: Found school: %r' % school)
			schools.append(school)
		return schools

	@classmethod
	def from_binddn(cls, lo):
		logger.debug('All Schools: Showing all OUs which DN %s can read.' % lo.binddn)
		if lo.binddn.find('ou=') > 0:
			# we got an OU in the user DN -> school teacher or assistent
			# restrict the visibility to current school
			# (note that there can be schools with a DN such as ou=25g18,ou=25,dc=...)
			school_dn = lo.binddn[lo.binddn.find('ou='):]
			logger.debug('Schools from binddn: Found an OU in the LDAP binddn. Restricting schools to only show %s' % school_dn)
			school = cls.from_dn(school_dn, None, lo)
			logger.debug('Schools from binddn: Found school: %r' % school)
			return [school]
		else:
			logger.warning('Schools from binddn: Unable to identify OU of this account - showing all OUs!')
			return School.get_all(lo)

	@classmethod
	def get_all(cls, lo, filter_str=None, easy_filter=False, respect_local_oulist=True):
		oulist = ucr.get('ucsschool/local/oulist')
		if oulist and respect_local_oulist:
			logger.debug('All Schools: Schools overridden by UCR variable ucsschool/local/oulist')
			schools = cls.get_from_oulist(lo, oulist)
			if filter_str:
				filtered_school_dns = [filtered_school.dn for filtered_school in cls.get_all(lo, filter_str, easy_filter, respect_local_oulist=False)]
				schools = [school for school in schools if school.dn in filtered_school_dns]
			return schools
		else:
			return super(School, cls).get_all(lo, school=None, filter_str=filter_str, easy_filter=easy_filter)

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

