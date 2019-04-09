# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2016-2019 Univention GmbH
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
Base class for all Python based Post-Read-Pyhooks.
"""

from ucsschool.importer.utils.import_pyhook import ImportPyHook


class PostReadPyHook(ImportPyHook):
	"""
	Hook that is called directly after data has been read from CSV/...

	The base class' :py:meth:`__init__()` provides the following attributes:

	* self.lo          # LDAP object
	* self.logger      # Python logging instance

	If multiple hook classes are found, hook functions with higher
	priority numbers run before those with lower priorities. None disables
	a function (no need to remove it / comment it out).

	(1) Hooks are only executed during dry-runs, if the class attribute
	:py:attr:`supports_dry_run` is set to `True` (default is `False`). Hooks
	with `supports_dry_run == True` must not modify LDAP objects.
	Therefore the LDAP connection object self.lo will be a read-only connection
	during a dry-run.
	(2) Read-write cn=admin connection in a real run, read-only cn=admin
	connection during a dry-run.
	"""
	priority = {
		'entry_read': None,
		'all_entries_read': None,
	}

	def entry_read(self, entry_count, input_data, input_dict):
		"""
		Run code after an entry has been read and saved in
		input_data and input_dict. This hook may alter input_data
		and input_dict to modify the input data. This function may
		raise the exception UcsSchoolImportSkipImportRecord to ignore
		the read import data.

		:param int entry_count: index of the data entry (e.g. line of the CSV file)
		:param list[str] input_data: input data as raw as possible (e.g. raw CSV columns). The input_data may be changed.
		:param input_dict: input data mapped to column names. The input_dict may be changed.
		:type input_dict: dict[str, str]
		:return: None
		:raises UcsSchoolImportSkipImportRecord: if an entry (e.g. a CSV line) should be skipped
		"""
		return None

	def all_entries_read(self, imported_users, errors):
		"""
		Run code after all entries have been read. ImportUser objects for all
		lines are passed to the hook. Also errors are passed. Please note that
		the "entry_read" hook method may skip one or several input records, so
		they may be missing in imported_users.
		errors contains a list of catched errors/exceptions.

		:param list[ImportUser] imported_users: list of ImportUser objects created from the input records
		:param list[Exception] errors: list of exceptions that are caught during processing the input records
		:return: None
		"""
		return None
