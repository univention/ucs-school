# -*- coding: utf-8 -*-
#
# Univention UCS@school
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
Base class of all input readers.
"""

from ucsschool.importer.exceptions import UcsSchoolImportSkipImportRecord
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.utils.logging import get_logger
from ucsschool.importer.factory import Factory
from ucsschool.importer.utils.post_read_pyhook import PostReadPyHook
from ucsschool.importer.utils.ldap_connection import get_admin_connection, get_readonly_connection
from ucsschool.lib.pyhooks import PyHooksLoader

try:
	from typing import Dict, List
except ImportError:
	pass


class BaseReader(object):
	"""
	Base class of all input readers.

	Subclasses must override get_roles(), map() and read().
	"""

	pyhooks_base_path = "/usr/share/ucs-school-import/pyhooks"
	_post_read_pyhook_cache = None

	def __init__(self, filename, header_lines=0, **kwargs):
		"""
		:param str filename: Path to file with user data.
		:param int header_lines: Number of lines before the actual data starts.
		:param dict kwargs: optional parameters for use in derived classes
		"""
		self.config = Configuration()
		self.logger = get_logger()
		self.lo, self.position = get_readonly_connection() if self.config['dry_run'] else get_admin_connection()
		self.filename = filename
		self.header_lines = header_lines
		self.import_users = self.read()
		self.factory = Factory()
		self.ucr = self.factory.make_ucr()
		self.entry_count = 0    # line/node in input data
		self.input_data = None  # input data, as raw as possible/sensible

	def __iter__(self):
		return self

	def next(self):
		"""
		Generates ImportUsers from input data.

		:return: ImportUser
		:rtype: ImportUser
		"""
		while True:
			input_dict = self.import_users.next()
			self.logger.debug("Input %d: %r -> %r", self.entry_count, self.input_data, input_dict)
			try:
				self.call_post_read_hook(self.entry_count, self.input_data, input_dict)
				break
			except UcsSchoolImportSkipImportRecord as exc:
				self.logger.info("Skipping input line %d as requested by PostReadPyHook: %s", self.entry_count, exc)

		cur_user_roles = self.get_roles(input_dict)
		cur_import_user = self.map(input_dict, cur_user_roles)
		cur_import_user.entry_count = self.entry_count
		cur_import_user.input_data = self.input_data
		cur_import_user.prepare_uids()
		return cur_import_user

	def call_post_read_hook(self, entry_count, input_data, input_dict):
		# type: (int, List[str], Dict[str, str]) -> None
		"""
		Run code after an entry has been read and saved in
		input_data and input_dict. This hook may alter input_data
		and input_dict to modify the input data.

		:param int entry_count: index of the data entry (e.g. line of the CSV file)
		:param list[str] input_data: input data as raw as possible (e.g. raw CSV columns). The input_data may be changed.
		:param input_dict: input data mapped to column names. The input_dict may be changed.
		:type input_dict: dict[str, str]
		"""
		if self._post_read_pyhook_cache is None:
			path = self.config.get('hooks_dir_pyhook', self.pyhooks_base_path)
			pyloader = PyHooksLoader(path, PostReadPyHook, self.logger)
			self._post_read_pyhook_cache = pyloader.get_hook_objects(self.lo)

		func_name = 'entry_read'
		for func in self._post_read_pyhook_cache.get(func_name, []):
			self.logger.info("Running %s hook %s for entry %s...", func_name, func, entry_count)
			func(entry_count, input_data, input_dict)

	def get_roles(self, input_data):
		"""
		IMPLEMENT ME
		Detect the ucsschool.lib.roles from the input data.

		:param dict input_data: dict user from read()
		:return: [ucsschool.lib.roles, ..]
		:rtype: list(str)
		"""
		raise NotImplementedError()

	def map(self, input_data, cur_user_roles):
		"""
		IMPLEMENT ME
		Creates a ImportUser object from a users dict (self.cur_entry). Data
		will not be	modified, just copied.

		:param dict input_data: user from read()
		:param cur_user_roles: [ucsschool.lib.roles, ..]
		:type cur_user_roles: list(str)
		:return: ImportUser
		:rtype: ImportUser
		"""
		raise NotImplementedError()

	def read(self, *args, **kwargs):
		"""
		IMPLEMENT ME
		Generator that returns dicts of read users
		Sets self.entry_count and self.input_data on each read.

		:param tuple args: arguments for implemented reader
		:param dict kwargs: arguments for implemented reader
		:return: iter([user, ...])
		:rtype: Iterator
		"""
		raise NotImplementedError()

	def get_data_mapping(self, input_data):
		"""
		IMPLEMENT ME
		Create a mapping from the configured input mapping to the actual
		input data. This is configuration and input format specific. See
		csv_reader for an example.
		Used by ImportUser.format_from_scheme().

		:param input_data: raw input data as stored in ImportUser.input_data
		:type input_data: list(str)
		:return: key->input_data-value mapping
		:rtype: dict
		"""
		return {}
