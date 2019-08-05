#!/usr/bin/python2.7

# Copyright (C) 2019 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# source code of this program is made available
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
# /usr/share/common-licenses/AGPL-3. If not, see <http://www.gnu.org/licenses/>.

"""
UDM hook to set UCS@schools `ucsschool_roles` attribute on client computer
and central memberserver objects.
"""

import inspect
from six import iteritems
from univention.admin.hook import simpleHook  # pylint: disable=no-name-in-module,import-error
from ucsschool.lib.models.utils import ucr
try:
	from ucsschool.lib.roles import (
		create_ucsschool_role_string, role_ip_computer, role_linux_computer, role_mac_computer, role_memberserver,
		role_ubuntu_computer, role_win_computer
	)
	from ucsschool.lib.models import School
	_NO_SCHOOL_LIB = False
except ImportError:
	_NO_SCHOOL_LIB = True
else:
	_UDM_MODULE_NAME2OC_ROLE = {
		'computers/domaincontroller_backup': ('ucsschoolServer', 'ignore'),  # ignore, done in join script
		'computers/domaincontroller_master': ('ucsschoolServer', 'ignore'),  # ignore, done in join script
		'computers/domaincontroller_slave': ('ucsschoolServer', 'ignore'),  # ignore, done in join script
		'computers/memberserver': ('ucsschoolServer', 'member'),  # only centrals are handled, others ignored
		'computers/linux': ('ucsschoolComputer', role_linux_computer),
		'computers/macos': ('ucsschoolComputer', role_mac_computer),
		'computers/windows': ('ucsschoolComputer', role_win_computer),
		'computers/ipmanagedclient': ('ucsschoolComputer', role_ip_computer),
		'computers/ubuntu': ('ucsschoolComputer', role_ubuntu_computer),
	}
try:
	from typing import Dict, List, Set, Tuple, Union  # pylint: disable=unused-import
	AddType = Tuple[str, List[str]]  # pylint: disable=invalid-name
	ModType = Tuple[str, List[str], List[str]]  # pylint: disable=invalid-name
except ImportError:
	pass


class UcsschoolRoleComputers(simpleHook):
	"""
	UDM hook to set UCS@schools `ucsschool_roles` attribute on client computer
	and central memberserver objects.
	"""
	type = 'UcsschoolRoleComputers'

	def __init__(self, *args, **kwargs):
		super(UcsschoolRoleComputers, self).__init__(*args, **kwargs)
		self.is_master_or_backup = ucr['server/role'] in ('domaincontroller_master', 'domaincontroller_backup')

	def hook_ldap_addlist(self, obj, al=None):
		al = al or []
		if _NO_SCHOOL_LIB or not self.is_master_or_backup:
			return al
		return self.add_ocs_and_ucschool_roles(obj, al, 'add')

	def hook_ldap_modlist(self, obj, ml=None):
		ml = ml or []
		if _NO_SCHOOL_LIB or not self.is_master_or_backup:
			return ml
		return self.add_ocs_and_ucschool_roles(obj, ml, 'mod')

	def add_ocs_and_ucschool_roles(self, obj, aml, operation):
		# type: (univention.admin.handlers.simpleComputer, List[Union[AddType, ModType]], str) -> List[Union[AddType, ModType]]
		"""
		Append `objectClass` and `ucsschoolRole` entries to add/change list.

		:param univention.admin.handlers.simpleComputer obj: UDM computer object
		:param list(tuple(str)) aml: LDAP add or modify list
		:param str operation: 'add' to append 2-tuple, 'mod' to append 3-tuple
		:return: (possibly) modified add/change list
		:rtype: list(tuple(str))
		"""
		udm_module_name = getattr(type(obj), 'module', inspect.getmodule(obj).module)
		oc, role_str = _UDM_MODULE_NAME2OC_ROLE[udm_module_name]

		if role_str == 'ignore':
			return aml

		all_schools = dict((school.name, school.dn) for school in School.get_all(obj.lo))
		existing_ocs, existing_roles = self._existing_ocs_roles(obj, aml)

		if oc not in existing_ocs:
			if operation == 'add':
				aml.append(('objectClass', [oc]))
			else:
				aml.append(('objectClass', [], [oc]))

		obj_schools = self._get_schools(obj, all_schools)
		if role_str == 'member':
			# only central memberservers are handled here
			if obj_schools == ['-']:
				role_str = role_memberserver
			else:
				return aml

		roles = {create_ucsschool_role_string(role_str, school) for school in obj_schools}
		missing_roles = roles - existing_roles
		if missing_roles:
			if operation == 'add':
				aml.append(('ucsschoolRole', list(missing_roles)))
			else:
				aml.append(('ucsschoolRole', [], list(missing_roles)))
		return aml

	@staticmethod
	def _get_schools(obj, all_schools):
		# type: (univention.admin.handlers.simpleComputer, Dict[str, str]) -> List[str]
		"""
		Return school name (OU) if obj is located inside one, else '-'.

		:param univention.admin.handlers.simpleComputer obj: UDM computer object
		:return: school name (OU) if obj is located inside one, else '-'
		:rtype: str
		"""
		if obj.has_key('school'):
			schools = obj.get('school')
		else:
			schools = []
		obj_dn = obj.dn or obj.position.getDn()
		for school_name, school_dn in iteritems(all_schools):
			if obj_dn.endswith(school_dn):
				schools.append(school_name)
				break
		if not schools:
			schools = ['-']
		return schools

	@staticmethod
	def _existing_ocs_roles(obj, aml):
		# type: (univention.admin.handlers.simpleComputer, List[Union[AddType, ModType]]) -> Tuple[Set[str], Set[str]]
		"""Get objectClasses and ucsschoolRoles from obj."""
		existing_ocs = set(obj.oldattr.get('objectClass', []))
		existing_roles = set(obj.get('ucsschoolRole', []))
		for things in aml:
			attr = things[0]
			val = things[-1]
			if attr == 'objectClass':
				existing_ocs.update(val)
			elif attr == 'ucsschoolRole':
				existing_roles.update(val)
		return existing_ocs, existing_roles
