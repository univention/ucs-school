# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2020 Univention GmbH
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

import os.path
from typing import List, Optional

from ldap.filter import filter_format
from udm_rest_client import UDM, NoObject as UdmNoObject, UdmObject

from ..roles import role_school_class_share, role_workgroup_share
from .attributes import Roles, SchoolClassAttribute, ShareName
from .base import RoleSupportMixin, SuperOrdinateType, UCSSchoolModel, UCSSchoolHelperAbstractClass
from .utils import _, ucr


class Share(UCSSchoolHelperAbstractClass):
	name: str = ShareName(_('Name'))
	school_group = SchoolClassAttribute(_('School class'), required=True, internal=True)  # type: SchoolClass

	@classmethod
	def from_school_group(cls, school_group):
		return cls(name=school_group.name, school=school_group.school, school_group=school_group)
	from_school_class = from_school_group  # legacy

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).shares

	async def do_create(self, udm_obj: UdmObject, lo: UDM) -> None:
		gid: int = (await self.school_group.get_udm_object(lo)).props.gidNumber
		udm_obj.props.host = await self.get_server_fqdn(lo)
		udm_obj.props.path = self.get_share_path()
		udm_obj.props.writeable = True
		udm_obj.props.sambaName = None  # UDM HTTP API fails on empty string
		udm_obj.props.sambaWriteable = True
		udm_obj.props.sambaBrowseable = True
		udm_obj.props.sambaForceGroup = '+%s' % self.name
		udm_obj.props.sambaCreateMode = '0770'
		udm_obj.props.sambaDirectoryMode = '0770'
		udm_obj.props.owner = 0
		udm_obj.props.group = gid
		udm_obj.props.directorymode = '0770'
		if ucr.is_false('ucsschool/default/share/nfs', True):
			try:
				udm_obj.options.remove('nfs')  # deactivate NFS
			except ValueError:
				pass
		self.logger.info('Creating share on "%s"', udm_obj.props.host)
		return await super(Share, self).do_create(udm_obj, lo)

	def get_share_path(self) -> str:
		if ucr.is_true('ucsschool/import/roleshare', True):
			return '/home/%s/groups/%s' % (self.school_group.school, self.name)
		else:
			return '/home/groups/%s' % self.name

	async def do_modify(self, udm_obj: UdmObject, lo: UDM) -> None:
		old_name = self.get_name_from_dn(self.old_dn)
		if old_name != self.name:
			head, tail = os.path.split(udm_obj.props.path)
			tail = self.name
			udm_obj.props.path = os.path.join(head, tail)
			if udm_obj.props.sambaName == old_name:
				udm_obj.props.sambaName = self.name
			if udm_obj.props.sambaForceGroup == '+%s' % old_name:
				udm_obj.props.sambaForceGroup = '+%s' % self.name
		return await super(Share, self).do_modify(udm_obj, lo)

	@staticmethod
	async def get_server_udm_object(dn: str, lo: UDM) -> Optional[UdmObject]:
		mod = lo.get("computers/domaincontroller_slave")
		try:
			return await mod.get(dn)
		except UdmNoObject:
			pass
		mod = lo.get("computers/domaincontroller_master")
		try:
			return await mod.get(dn)
		except UdmNoObject:
			return None

	async def get_server_fqdn(self, lo: UDM) -> Optional[str]:
		domainname = ucr.get('domainname')
		school = await self.get_school_obj(lo)
		school_dn = school.dn

		# fetch serverfqdn from OU
		# TODO: change this also in 4.4
		from .school import School
		school: School = await School.from_dn(school_dn, None, lo)
		school_udm_obj = await school.get_udm_object(lo)
		class_share_file_server_dn: str = school_udm_obj.props.ucsschoolClassShareFileServer
		if class_share_file_server_dn:
			server_udm = await self.get_server_udm_object(class_share_file_server_dn, lo)
			server_domain_name = server_udm.props.domain
			if not server_domain_name:
				server_domain_name = domainname
			result = server_udm.props.name
			if result:
				return '%s.%s' % (result, server_domain_name)

		# get alternative server (defined at ou object if a dc slave is responsible for more than one ou)
		# TODO: this is broken! get uldap instance here
		raise NotImplementedError("TODO: I think univentionLDAPAccessWrite has no UDM property.")
		ou_attr_ldap_access_write = lo.get(school_dn, ['univentionLDAPAccessWrite'])
		alternative_server_dn = None
		if len(ou_attr_ldap_access_write) > 0:
			alternative_server_dn = ou_attr_ldap_access_write['univentionLDAPAccessWrite'][0]
			if len(ou_attr_ldap_access_write) > 1:
				self.logger.warning('more than one corresponding univentionLDAPAccessWrite found at ou=%s', self.school)

		# build fqdn of alternative server and set serverfqdn
		if alternative_server_dn:
			alternative_server_attr = lo.get(alternative_server_dn, ['uid'])
			if len(alternative_server_attr) > 0:
				alternative_server_uid = alternative_server_attr['uid'][0]
				alternative_server_uid = alternative_server_uid.replace('$', '')
				if len(alternative_server_uid) > 0:
					return '%s.%s' % (alternative_server_uid, domainname)

		# fallback
		return '%s.%s' % (school.get_dc_name_fallback(), domainname)

	class Meta:
		udm_module = 'shares/share'


class WorkGroupShare(RoleSupportMixin, Share):
	"""
	This method was overwritten to identify WorkGroupShares and distinct them
	from other shares of the school.
	If at some point a lookup is implemented that uses the role attribute which
	is reliable this code can be removed.
	Bug #48428
	"""
	ucsschool_roles = Roles(_('Roles'), aka=['Roles'])
	default_roles = [role_workgroup_share]
	_school_in_name_prefix = True

	@classmethod
	async def get_all(cls, lo: UDM, school: str = None, filter_str: str = None, easy_filter: str = False, superordinate: SuperOrdinateType = None) -> List[UCSSchoolModel]:
		shares = await super(WorkGroupShare, cls).get_all(lo, school, filter_str, easy_filter, superordinate)
		filtered_shares = []
		search_base = cls.get_search_base(school)
		grp_mod = lo.get('groups/group')
		for share in shares:
			filter_s = filter_format('name=%s', (share.name,))
			async for group in grp_mod.search(filter_s, base=search_base.groups):
				if search_base.isWorkgroup(group.dn):
					filtered_shares.append(share)
		return filtered_shares


class ClassShare(RoleSupportMixin, Share):
	ucsschool_roles = Roles(_('Roles'), aka=['Roles'])
	default_roles = [role_school_class_share]
	_school_in_name_prefix = True

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).classShares

	def get_share_path(self):
		if ucr.is_true('ucsschool/import/roleshare', True):
			return '/home/%s/groups/klassen/%s' % (self.school_group.school, self.name)
		else:
			return '/home/groups/klassen/%s' % self.name
