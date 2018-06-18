# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Create LDAP connections for import.
"""
# Copyright 2016-2018 Univention GmbH
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


from univention.admin import uldap
from ucsschool.importer.exceptions import LDAPWriteAccessDenied, UcsSchoolImportFatalError

_admin_connection = None
_admin_position = None
_machine_connection = None
_machine_position = None
_read_only_admin_connection = None
_read_only_admin_position = None


def get_admin_connection():
	"""Read-write cn=admin connection."""
	global _admin_connection, _admin_position
	if not _admin_connection or not _admin_position:
		try:
			_admin_connection, _admin_position = uldap.getAdminConnection()
		except IOError:
			raise UcsSchoolImportFatalError("This script must be executed on a DC Master.")
	return _admin_connection, _admin_position


def get_machine_connection():
	"""Read-write machine connection."""
	global _machine_connection, _machine_position
	if not _machine_connection or not _machine_position:
		_machine_connection, _machine_position = uldap.getMachineConnection()
	return _machine_connection, _machine_position


class ReadOnlyAccess(uldap.access):
	"""
	LDAP access class that prevents LDAP write access.

	Must be a descendant of uldap.access, or UDM will raise a TypeError.
	"""
	def __init__(self, *args, **kwargs):
		self._real_lo, self._real_po = get_admin_connection()
		self._real_lo.allow_modify = 1

	def __getattr__(self, item):
		if item in ('add', 'modify', 'rename', 'delete'):
			raise LDAPWriteAccessDenied()
		return getattr(self._real_lo, item)

	def add(self, *args, **kwargs):
		raise LDAPWriteAccessDenied()

	def modify(self, *args, **kwargs):
		raise LDAPWriteAccessDenied()

	def rename(self, *args, **kwargs):
		raise LDAPWriteAccessDenied()

	def delete(self, *args, **kwargs):
		raise LDAPWriteAccessDenied()


def get_readonly_connection():
	"""Read-only cn=admin connection."""
	global _read_only_admin_connection, _read_only_admin_position
	if not _read_only_admin_connection or not _read_only_admin_position:
		lo_rw = ReadOnlyAccess()
		_read_only_admin_connection, _read_only_admin_position = lo_rw, lo_rw._real_po
	return _read_only_admin_connection, _read_only_admin_position
