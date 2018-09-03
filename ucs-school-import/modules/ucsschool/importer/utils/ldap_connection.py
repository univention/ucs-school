# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
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

"""
Create LDAP connections for import.
"""

from univention.admin import uldap
from ucsschool.importer.exceptions import LDAPWriteAccessDenied, UcsSchoolImportFatalError

try:
	from typing import Tuple
	import univention.admin.uldap
	import univention.admin.handlers
	LoType = univention.admin.uldap.access
	PoType = univention.admin.uldap.position
	UdmObjectType = univention.admin.handlers.simpleLdap
except ImportError:
	pass

_admin_connection = None
_admin_position = None
_machine_connection = None
_machine_position = None
_unprivileged_connection = None
_unprivileged_position = None
_read_only_admin_connection = None
_read_only_admin_position = None


def get_admin_connection():  # type: () -> (Tuple[LoType, PoType])
	"""
	Read-write cn=admin connection.

	:rtype: tuple(univention.admin.uldap.access, univention.admin.uldap.position)
	"""
	global _admin_connection, _admin_position
	if not _admin_connection or not _admin_position:
		try:
			_admin_connection, _admin_position = uldap.getAdminConnection()
		except IOError:
			raise UcsSchoolImportFatalError("This script must be executed on a DC Master.")
	return _admin_connection, _admin_position


def get_machine_connection():  # type: () -> (Tuple[LoType, PoType])
	"""
	Read-write machine connection.

	:rtype: tuple(univention.admin.uldap.access, univention.admin.uldap.position)
	"""
	global _machine_connection, _machine_position
	if not _machine_connection or not _machine_position:
		_machine_connection, _machine_position = uldap.getMachineConnection()
	return _machine_connection, _machine_position


def get_unprivileged_connection():  # type: () -> (Tuple[LoType, PoType])
	"""
	Unprivileged read-write connection.

	:rtype: tuple(univention.admin.uldap.access, univention.admin.uldap.position)
	"""
	global _unprivileged_connection, _unprivileged_position
	if not _unprivileged_connection or not _unprivileged_position:
		with open('/etc/ucsschool-import/ldap_unprivileged.secret') as fp:
			dn_pw = fp.read()
		dn, base, pw = dn_pw.strip().split(':')
		_unprivileged_connection = uldap.access(base=base, binddn=dn, bindpw=pw)
		_unprivileged_position = uldap.position(_unprivileged_connection.base)
	return _unprivileged_connection, _unprivileged_position


class ReadOnlyAccess(uldap.access):
	"""
	LDAP access class that prevents LDAP write access.

	Must be a descendant of :py:class:`univention.admin.uldap.access`, or UDM
	will raise a :py:exc:`TypeError`.
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


def get_readonly_connection():  # type: () -> (Tuple[LoType, PoType])
	"""
	Read-only cn=admin connection.

	:rtype: tuple(univention.admin.uldap.access, univention.admin.uldap.position)
	"""
	global _read_only_admin_connection, _read_only_admin_position
	if not _read_only_admin_connection or not _read_only_admin_position:
		lo_rw = ReadOnlyAccess()
		_read_only_admin_connection, _read_only_admin_position = lo_rw, lo_rw._real_po
	return _read_only_admin_connection, _read_only_admin_position
