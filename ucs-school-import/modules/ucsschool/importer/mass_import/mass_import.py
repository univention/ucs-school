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
Default mass import class.
"""

import datetime

from ucsschool.importer.exceptions import UcsSchoolImportError, UcsSchoolImportFatalError
from ucsschool.importer.factory import Factory
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.utils.logging import get_logger
from ucsschool.importer.utils.pre_read_pyhook import PreReadPyHook
from ucsschool.importer.utils.result_pyhook import ResultPyHook
from ucsschool.lib.models.utils import stopped_notifier
from ucsschool.lib.pyhooks import PyHooksLoader

try:
	from typing import Any, Optional, Type, TypeVar
	from ucsschool.importer.utils.import_pyhook import ImportPyHook
	ImportPyHookTV = TypeVar('ImportPyHookTV', bound=ImportPyHook)
except ImportError:
	pass


class MassImport(object):
	"""
	Create/modify/delete all objects from the input.

	Currently only implemented for users.
	"""

	pyhooks_base_path = "/usr/share/ucs-school-import/pyhooks"
	_pyhook_cache = {}

	def __init__(self, dry_run=True):  # type: (Optional[bool]) -> None
		"""
		:param bool dry_run: set to False to actually commit changes to LDAP
		"""
		self.dry_run = dry_run
		self.config = Configuration()
		self.logger = get_logger()
		self.factory = Factory()
		self.result_exporter = self.factory.make_result_exporter()
		self.password_exporter = self.factory.make_password_exporter()
		self.errors = list()
		self.user_import_stats_str = ''

	def mass_import(self):  # type: () -> None
		with stopped_notifier():
			self.import_computers()
			self.import_groups()
			self.import_inventory_numbers()
			self.import_networks()
			self.import_ous()
			self.import_printers()
			self.import_routers()
			self.import_users()

	def import_computers(self):
		pass

	def import_groups(self):
		pass

	def import_inventory_numbers(self):
		pass

	def import_networks(self):
		pass

	def import_ous(self):
		pass

	def import_printers(self):
		pass

	def import_routers(self):
		pass

	def import_users(self):  # type: () -> None
		self.logger.info("------ Importing users... ------")
		user_import = self.factory.make_user_importer(self.dry_run)
		exc = None
		try:
			user_import.progress_report(description='Running pre-read hooks: 0%.', percentage=0)
			self.call_pyhook(PreReadPyHook, 'pre_read')
			user_import.progress_report(description='Analyzing data: 1%.', percentage=1)
			imported_users = user_import.read_input()
			users_to_delete = user_import.detect_users_to_delete()
			user_import.delete_users(users_to_delete)  # 0% - 10%
			user_import.create_and_modify_users(imported_users)  # 90% - 100%
		except UcsSchoolImportError as exc:
			user_import.errors.append(exc)
			self.logger.exception(exc)
		except Exception as exc:
			user_import.errors.append(UcsSchoolImportFatalError(
				'An unknown error terminated the import job: {}'.format(exc)))
			self.logger.exception(exc)
		self.errors.extend(user_import.errors)
		self.user_import_stats_str = user_import.log_stats()
		if self.config["output"]["new_user_passwords"]:
			nup = datetime.datetime.now().strftime(self.config["output"]["new_user_passwords"])
			self.logger.info("------ Writing new users passwords to %s... ------", nup)
			self.password_exporter.dump(user_import, nup)
		if self.config["output"]["user_import_summary"]:
			uis = datetime.datetime.now().strftime(self.config["output"]["user_import_summary"])
			self.logger.info("------ Writing user import summary to %s... ------", uis)
			self.result_exporter.dump(user_import, uis)
		result_data = user_import.get_result_data()
		self.call_pyhook(ResultPyHook, 'user_result', result_data)
		self.logger.info("------ Importing users done. ------")
		if exc:
			raise exc

	def call_pyhook(self, hook_cls, func_name, *args, **kwargs):
		# type: (Type[ImportPyHookTV], str, *Any, **Any) -> None
		"""
		Run hook code
		* before starting to read the input file (PreReadPyHook).
		* after the import has been completed (ResultPyHook).

		:param hook_cls: class object - load and run hooks that are a
			subclass of this
		:type hook_cls: ucsschool.importer.utils.import_pyhook.ImportPyHook
		:param str func_name: name of method to run in each hook
		:param args: arguments to pass to hooks
		:param kwargs: arguments to pass to hooks
		"""
		if hook_cls not in self._pyhook_cache:
			path = self.config.get('hooks_dir_pyhook', self.pyhooks_base_path)
			pyloader = PyHooksLoader(path, hook_cls, self.logger)
			self._pyhook_cache[hook_cls] = pyloader.get_hook_objects()

		for func in self._pyhook_cache[hook_cls].get(func_name, []):
			self.logger.info("Running %s %s hook %s ...", hook_cls.__name__, func_name, func)
			func(*args, **kwargs)
