# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Module for authorization checks for the ucsschool lib.
"""
# Copyright 2016-2020 Univention GmbH
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

try:
	# noinspection PyUnresolvedReferences
	from typing import List, Optional
except ImportError:
	pass

DELIMITER = ' '


class RoleCapability:
	"""
	Represents a capacity that is attached to a role.
	The difference is the optional target role component.
	"""

	def __init__(self, name, display_name, target_role):  # type: (str, str, str) -> RoleCapability
		self._name = name
		self._display_name = display_name
		self._target_role = target_role

	@classmethod
	def from_str(cls, capability_str):  # type: (str) -> RoleCapability
		"""
		Parses a capability string how it would be attached to a ucsschool/role object in UDM.
		Example with whitespace delimiter: 'ucsschool/password_reset teacher'
		"""
		if DELIMITER in capability_str:
			name, target_role = capability_str.split(DELIMITER)
			return cls(name, name, target_role)
		else:
			return cls(capability_str, capability_str, '')

	def __eq__(self, other):
		return self._name == other.name and self._target_role == other.target_role

	def __repr__(self):
		return self.__str__()

	def __str__(self):
		return "{}{}{}".format(self._name, DELIMITER, self._target_role)

	@property
	def name(self):
		return self._name

	@property
	def target_role(self):
		return self._target_role

	def targets_role(self, role):  # type: (ContextRole) -> bool
		"""
		Checks if this RoleCapability targets a given role.
		True if the roles name equals the target_role or the target_role string is empty.
		False otherwise.
		"""
		return self._target_role in ('', role.name)


class ContextRole:
	"""
	Represents a role that is attached to a specific ucsschool object.
	Example: teacher:school:DEMOSCHOOL
	It is an instance of a ucschool/role UDM object
	"""

	def __init__(self, name, display_name, capabilities, context, context_type='school'):  # type: (str, str, List[RoleCapability], str, Optional[str])
		self._name = name
		self._display_name = display_name
		self._capabilities = capabilities
		self._context = context
		self._context_type = context_type

	def has_capability(self, capability_name):  # type: (str) -> bool
		"""
		Checks if the ContextRole has a RoleCapability with a given name.
		"""
		return any(True for cap in self._capabilities if cap.name == capability_name)

	def get_capabilities(self, capability_name):  # type: (str) -> List[RoleCapability]
		"""
		Returns all RoleCapabilities with the given name that are attached to the ContextRole.
		"""
		return [cap for cap in self._capabilities if cap.name == capability_name]

	@property
	def name(self):
		return self._name

	@property
	def capabilities(self):  # type: () -> List[RoleCapability]
		return self._capabilities

	@property
	def context(self):
		return self._context


def is_authorized(actor_context_roles, object_context_roles, capability_name):  # type: (List[ContextRole], List[ContextRole], str) -> bool
	"""
	This function takes a list ContextRoles of the actor, a list of ContextRoles of the object and a capability name.
	If the actor is authorized to perform the given capability on the object True is returned. Otherwise False.
	"""
	effective_roles = []
	for role in actor_context_roles:
		a_capabilities = role.get_capabilities(capability_name)
		if not a_capabilities:  # We are just interested in roles that have the capability
			continue
		# We have to check that the roles that have the specified capability
		# also match in the context and target_role with any given ContextRole of the object
		affected_roles = [o_role for o_role in object_context_roles if role.context == o_role.context and any(
			True for cap in a_capabilities if cap.targets_role(o_role))]
		if affected_roles:
			effective_roles.append(role)
	# special handling will land here
	return len(effective_roles) > 0

