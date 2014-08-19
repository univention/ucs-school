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

from ldap.dn import str2dn

from univention.admin.uexceptions import noObject

from ucsschool.lib.models.attributes import GroupName, Description, Attribute, SchoolClassName, Hosts
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models.misc import OU, Container
from ucsschool.lib.models.share import ClassShare
from ucsschool.lib.models.policy import UMCPolicy
from ucsschool.lib.models.utils import ucr, _, logger

class _MayHaveSchoolPrefix(object):
	def get_relative_name(self):
		# schoolname-1a => 1a
		if self.name.startswith('%s-' % self.school):
			return self.name[len(self.school) + 1:]
		return self.name

class Group(UCSSchoolHelperAbstractClass):
	name = GroupName(_('Name'))
	description = Description(_('Description'))

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).groups

	@classmethod
	def is_school_group(cls, school, group_dn):
		return cls.get_search_base(school).isGroup(group_dn)

	@classmethod
	def is_school_class(cls, school, group_dn):
		return cls.get_search_base(school).isClass(group_dn)

	@classmethod
	def is_computer_room(cls, school, group_dn):
		return cls.get_search_base(school).isRoom(group_dn)

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		if cls.is_school_class(school, udm_obj.dn):
			return SchoolClass
		elif cls.is_computer_room(school, udm_obj.dn):
			return ComputerRoom
		return cls

	def add_umc_policy(self, policy_dn, lo):
		if not policy_dn or policy_dn.lower() == 'none':
			logger.warning('No policy added to %r' % self)
			return
		try:
			policy = UMCPolicy.from_dn(policy_dn, self.school, lo)
		except noObject:
			logger.warning('Object to be referenced does not exist (or is no UMC-Policy): %s' % policy_dn)
		else:
			policy.attach(self, lo)

	def build_hook_line(self, hook_time, func_name):
		code = self._map_func_name_to_code(func_name)
		if code != 'M':
			return self._build_hook_line(
					code,
					self.school,
					self.name,
					self.description,
				)
		else:
			# This is probably a bug. See ucs-school-import and Bug #34736
			old_name = self.get_name_from_dn(self.old_dn)
			new_name = self.name
			if old_name != new_name:
				return self._build_hook_line(
						code,
						old_name,
						new_name,
					)

	class Meta:
		udm_module = 'groups/group'
		name_is_unique = True

class BasicGroup(Group):
	school = None
	container = Attribute(_('Container'), required=True)

	def __init__(self, name=None, school=None, **kwargs):
		if 'container' not in kwargs:
			kwargs['container'] = 'cn=groups,%s' % ucr.get('ldap/base')
		super(BasicGroup, self).__init__(name=name, school=school, **kwargs)

	def create_without_hooks(self, lo, validate):
		# prepare LDAP: create containers where this basic group lives if necessary
		container_dn = self.get_own_container()[:-len(ucr.get('ldap/base'))-1]
		containers = str2dn(container_dn)
		super_container_dn = ucr.get('ldap/base')
		for container_info in reversed(containers):
			dn_part, cn = container_info[0][0:2]
			if dn_part.lower() == 'ou':
				container = OU(name=cn)
			else:
				container = Container(name=cn, school='', group_path='1')
			super_container_dn = container.create_in_container(super_container_dn, lo)
		return super(BasicGroup, self).create_without_hooks(lo, validate)

	def get_own_container(self):
		return self.container

	def build_hook_line(self, hook_time, func_name):
		return None

	@classmethod
	def get_container(cls, school=None):
		return ucr.get('ldap/base')

class SchoolClass(Group, _MayHaveSchoolPrefix):
	name = SchoolClassName(_('Name'))

	def create_without_hooks(self, lo, validate):
		super(SchoolClass, self).create_without_hooks(lo, validate) # success = ?
		self.create_share(lo) # success = success and ?
		return True # success?

	def create_share(self, lo):
		share = ClassShare.from_school_class(self)
		return share.create(lo)

	def modify_without_hooks(self, lo, validate=True, move_if_necessary=None):
		share = ClassShare.from_school_class(self)
		if self.old_dn:
			old_name = self.get_name_from_dn(self.old_dn)
			if old_name != self.name:
				# recreate the share.
				# if the name changed
				# from_school_class will have initialized
				# share.old_dn incorrectly
				share = ClassShare(name=old_name, school=self.school, school_class=self)
				share.name = self.name
		success = super(SchoolClass, self).modify_without_hooks(lo, validate, move_if_necessary)
		if success:
			if share.exists(lo):
				success = share.modify(lo)
			else:
				success = self.create_share(lo)
		return success

	def remove_without_hooks(self, lo):
		success = super(SchoolClass, self).remove_without_hooks(lo)
		share = ClassShare.from_school_class(self)
		success = success and share.remove(lo)
		return success

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).classes

	def to_dict(self):
		ret = super(SchoolClass, self).to_dict()
		ret['name'] = self.get_relative_name()
		return ret

class ComputerRoom(Group, _MayHaveSchoolPrefix):
	hosts = Hosts(_('Hosts'))

	def to_dict(self):
		ret = super(ComputerRoom, self).to_dict()
		ret['name'] = self.get_relative_name()
		return ret

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).rooms

