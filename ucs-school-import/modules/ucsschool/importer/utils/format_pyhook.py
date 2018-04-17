# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Base class for all Python based format hooks.
"""
# Copyright 2017-2018 Univention GmbH
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

from ucsschool.lib.pyhooks import PyHook
from ucsschool.importer.utils.logging import get_logger


class FormatPyHook(PyHook):
	#
	# The base class' __init__() provides a logger instance:
	#
	# self.logger      # Python logging instance
	#

	# If multiple hook classes are found, hook functions with higher
	# priority numbers run before those with lower priorities. None disables
	# a function.
	priority = {
		'patch_fields_staff': None,
		'patch_fields_student': None,
		'patch_fields_teacher': None,
		'patch_fields_teacher_and_staff': None,
	}
	# The hook will be run only for property names in this list.
	properties = ()

	def __init__(self, *args, **kwargs):
		super(FormatPyHook, self).__init__(*args, **kwargs)
		self.logger = get_logger()  # Python logging instance

	def patch_fields_staff(self, property_name, fields):
		"""
		Run code before formatting an property using a schema in
		format_from_scheme().

		:param str property_name: Name of property_name that will be formatted
		:param dict fields: dictionary with the users attributes and
		udm_properties
		:return: fields dictionary that be used by format_from_scheme()
		:rtype: dict
		"""
		return fields

	def patch_fields_student(self, property_name, fields):
		"""
		Run code before formatting an property using a schema in
		format_from_scheme().

		:param str property_name: Name of property_name that will be formatted
		:param dict fields: dictionary with the users attributes and
		udm_properties
		:return: fields dictionary that be used by format_from_scheme()
		:rtype: dict
		"""
		return fields

	def patch_fields_teacher(self, property_name, fields):
		"""
		Run code before formatting an property using a schema in
		format_from_scheme().

		:param str property_name: Name of property_name that will be formatted
		:param dict fields: dictionary with the users attributes and
		udm_properties
		:return: fields dictionary that be used by format_from_scheme()
		:rtype: dict
		"""
		return fields

	def patch_fields_teacher_and_staff(self, property_name, fields):
		"""
		Run code before formatting a property using a schema in
		format_from_scheme().

		:param str property_name: Name of property_name that will be formatted
		:param dict fields: dictionary with the users attributes and
		udm_properties
		:return: fields dictionary that be used by format_from_scheme()
		:rtype: dict
		"""
		return fields
