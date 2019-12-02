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

from typing import Any, AsyncIterator, Dict, List, Optional, Type

from ldap.dn import str2dn

from udm_rest_client import UDM, NoObject as UdmNoObject, UdmObject

from ..roles import role_computer_room, role_school_class, role_workgroup
from .attributes import (
    Attribute,
    Description,
    GroupName,
    Hosts,
    Roles,
    SchoolClassName,
    Users,
)
from .base import RoleSupportMixin, UCSSchoolHelperAbstractClass, UCSSchoolModel
from .misc import OU, Container
from .policy import UMCPolicy
from .share import ClassShare, WorkGroupShare
from .utils import _, ucr


class _MayHaveSchoolPrefix(object):

	def get_relative_name(self) -> str:
		# schoolname-1a => 1a
		if self.school and self.name.lower().startswith('%s-' % self.school.lower()):
			return self.name[len(self.school) + 1:]
		return self.name

	def get_replaced_name(self, school: str) -> str:
		if self.name != self.get_relative_name():
			return '%s-%s' % (school, self.get_relative_name())
		return self.name


class _MayHaveSchoolSuffix(object):

	def get_relative_name(self) -> str:
		# schoolname-1a => 1a
		if self.school and self.name.lower().endswith('-%s' % self.school.lower()) or self.name.lower().endswith(' %s' % self.school.lower()):
			return self.name[:-(len(self.school) + 1)]
		return self.name

	def get_replaced_name(self, school: str) -> str:
		if self.name != self.get_relative_name():
			delim = self.name[len(self.get_relative_name())]
			return '%s%s%s' % (self.get_relative_name(), delim, school)
		return self.name


class Group(RoleSupportMixin, UCSSchoolHelperAbstractClass):
	name: str = GroupName(_('Name'))
	description: str = Description(_('Description'))
	users: List[UCSSchoolModel] = Users(_('Users'))
	ucsschool_roles: List[str] = Roles(_('Roles'), aka=['Roles'])

	@classmethod
	def get_container(cls, school: str) -> str:
		return cls.get_search_base(school).groups

	@classmethod
	def is_school_group(cls, school: str, group_dn: str) -> bool:
		return cls.get_search_base(school).isGroup(group_dn)

	@classmethod
	def is_school_workgroup(cls, school: str, group_dn: str) -> bool:
		return cls.get_search_base(school).isWorkgroup(group_dn)

	@classmethod
	def is_school_class(cls, school: str, group_dn: str) -> bool:
		return cls.get_search_base(school).isClass(group_dn)

	@classmethod
	def is_computer_room(cls, school: str, group_dn: str) -> bool:
		return cls.get_search_base(school).isRoom(group_dn)

	def self_is_workgroup(self) -> bool:
		return self.is_school_workgroup(self.school, self.dn)

	def self_is_class(self) -> bool:
		return self.is_school_class(self.school, self.dn)

	def self_is_computerroom(self) -> bool:
		return self.is_computer_room(self.school, self.dn)

	@classmethod
	async def get_class_for_udm_obj(cls, udm_obj: UdmObject, school: str) -> Type[UCSSchoolModel]:
		if cls.is_school_class(school, udm_obj.dn):
			return SchoolClass
		elif cls.is_computer_room(school, udm_obj.dn):
			return ComputerRoom
		elif cls.is_school_workgroup(school, udm_obj.dn):
			return WorkGroup
		elif cls.is_school_group(school, udm_obj.dn):
			return SchoolGroup
		return cls

	async def add_umc_policy(self, policy_dn: str, lo: UDM) -> None:
		if not policy_dn or policy_dn.lower() == 'none':
			self.logger.warning('No policy added to %r', self)
			return
		try:
			policy = await UMCPolicy.from_dn(policy_dn, self.school, lo)
		except UdmNoObject:
			self.logger.warning('Object to be referenced does not exist (or is no UMC-Policy): %s', policy_dn)
		else:
			policy.attach(self, lo)

	class Meta:
		udm_module = 'groups/group'
		name_is_unique = True


class BasicGroup(Group):
	school: str = None
	container: str = Attribute(_('Container'), required=True)

	def __init__(self, name: str = None, school: str = None, **kwargs):
		if 'container' not in kwargs:
			kwargs['container'] = 'cn=groups,%s' % ucr.get('ldap/base')
		super(BasicGroup, self).__init__(name=name, school=school, **kwargs)

	async def create_without_hooks(self, lo: UDM, validate: bool) -> bool:
		# prepare LDAP: create containers where this basic group lives if necessary
		container_dn = self.get_own_container()[:-len(ucr.get('ldap/base')) - 1]
		containers = str2dn(container_dn)
		super_container_dn = ucr.get('ldap/base')
		for container_info in reversed(containers):
			dn_part, cn = container_info[0][0:2]
			if dn_part.lower() == 'ou':
				container = OU(name=cn)
			else:
				container = Container(name=cn, school='', group_path='1')
			container.position = super_container_dn
			super_container_dn = await container.create(lo, False)
		return await super(BasicGroup, self).create_without_hooks(lo, validate)

	def get_own_container(self) -> Optional[str]:
		return self.container

	@classmethod
	def get_container(cls, school: str = None) -> str:
		return ucr.get('ldap/base')


class BasicSchoolGroup(BasicGroup):
	school: str = Group.school


class SchoolGroup(Group, _MayHaveSchoolSuffix):
	pass


class SchoolClass(Group, _MayHaveSchoolPrefix):
	name: str = SchoolClassName(_('Name'))

	default_roles: List[str] = [role_school_class]
	_school_in_name_prefix = True
	ShareClass = ClassShare

	async def create_without_hooks(self, lo: UDM, validate: bool) -> bool:
		success = await super(SchoolClass, self).create_without_hooks(lo, validate)
		if await self.exists(lo):
			success = success and await self.create_share(lo)
		return success

	async def create_share(self, lo: UDM) -> bool:
		share = self.ShareClass.from_school_group(self)
		return await share.exists(lo) or await share.create(lo)

	async def modify_without_hooks(self, lo: UDM, validate: bool = True, move_if_necessary: bool = None) -> bool:
		share = self.ShareClass.from_school_group(self)
		if self.old_dn:
			old_name = self.get_name_from_dn(self.old_dn)
			if old_name != self.name:
				# recreate the share.
				# if the name changed
				# from_school_group will have initialized
				# share.old_dn incorrectly
				share = self.ShareClass(name=old_name, school=self.school, school_group=self)
				share.name = self.name
		success = await super(SchoolClass, self).modify_without_hooks(lo, validate, move_if_necessary)
		if success:
			if await share.exists(lo):
				success = await share.modify(lo)
			else:
				success = await self.create_share(lo)
		return success

	async def remove_without_hooks(self, lo: UDM) -> bool:
		success = await super(SchoolClass, self).remove_without_hooks(lo)
		share = self.ShareClass.from_school_group(self)
		success = success and await share.remove(lo)
		return success

	@classmethod
	def get_container(cls, school: str) -> str:
		return cls.get_search_base(school).classes

	def to_dict(self) -> Dict[str, Any]:
		ret = super(SchoolClass, self).to_dict()
		ret['name'] = self.get_relative_name()
		return ret

	@classmethod
	async def get_class_for_udm_obj(cls, udm_obj: UdmObject, school: str) -> Optional[Type[UCSSchoolModel]]:
		if not cls.is_school_class(school, udm_obj.dn):
			return  # is a workgroup
		return cls


class WorkGroup(SchoolClass, _MayHaveSchoolPrefix):
	default_roles: List[str] = [role_workgroup]
	ShareClass = WorkGroupShare

	@classmethod
	def get_container(cls, school: str) -> str:
		return cls.get_search_base(school).workgroups

	@classmethod
	async def get_class_for_udm_obj(cls, udm_obj: UdmObject, school: str) -> Optional[Type[UCSSchoolModel]]:
		if not cls.is_school_workgroup(school, udm_obj.dn):
			return
		return cls


class ComputerRoom(Group, _MayHaveSchoolPrefix):
	hosts: List[str] = Hosts(_('Hosts'))

	users: List[UCSSchoolModel] = None
	default_roles: List[str] = [role_computer_room]

	def to_dict(self) -> Dict[str, Any]:
		ret = super(ComputerRoom, self).to_dict()
		ret['name'] = self.get_relative_name()
		return ret

	@classmethod
	def get_container(cls, school: str) -> str:
		return cls.get_search_base(school).rooms

	async def get_computers(self, ldap_connection: UDM) -> AsyncIterator[UCSSchoolModel]:
		from ucsschool.lib.models.computer import SchoolComputer
		for host in self.hosts:
			try:
				yield await SchoolComputer.from_dn(host, self.school, ldap_connection)
			except UdmNoObject:
				continue

	def get_schools_from_udm_obj(self, udm_obj: UdmObject) -> str:
		# fixme: no idea how to find out old school
		return self.school
