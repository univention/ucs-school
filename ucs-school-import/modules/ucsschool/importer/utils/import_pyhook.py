# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2017-2019 Univention GmbH
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
Base class for all Python based import hooks.
"""

from ucsschool.lib.pyhooks import PyHook
from ucsschool.importer.utils.logging import get_logger
from ucsschool.importer.utils.ldap_connection import get_admin_connection, get_readonly_connection
try:
	from typing import Any, Optional
	import logging.Logger
	import univention.admin.uldap.access
except ImportError:
	pass


class ImportPyHook(PyHook):
	"""
	Base class for Python based import hooks.

	Hooks are only executed during dry-runs, if the class attribute
	:py:attr:`supports_dry_run` is set to `True` (default is `False`). Hooks
	should to not modify LDAP objects during a dry run.

	:py:attr:`self.lo` is a read-write cn=admin connection in a real run,
	read-only cn=admin connection during a dry-run.
	"""
	supports_dry_run = False  # if True hook will be executed during a dry-run

	def __init__(self, lo=None, dry_run=False, *args, **kwargs):
		# type: (Optional[univention.admin.uldap.access], Optional[bool], *Any, **Any) -> None
		"""
		:param univention.admin.uldap.access lo: optional LDAP connection object
		:param bool dry_run: whether hook is executed during a dry-run
		"""
		super(ImportPyHook, self).__init__(*args, **kwargs)
		self.dry_run = dry_run  # True if executed during a dry-run
		if lo is None:
			self.lo = get_readonly_connection()[0] if self.dry_run else get_admin_connection()[0]
		else:
			self.lo = lo  # reuse LDAP object
		self.logger = get_logger()  # Python logging instance
