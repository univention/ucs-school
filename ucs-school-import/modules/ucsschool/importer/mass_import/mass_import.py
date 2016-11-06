# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Default mass import class.
"""
# Copyright 2016 Univention GmbH
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

import datetime

from ucsschool.importer.factory import Factory
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.utils.logging import get_logger
from ucsschool.lib.models.utils import stopped_notifier


class MassImport(object):
	"""
	Create/modify/delete all objects from the input.

	Currently only implemented for users.
	"""

	def __init__(self, dry_run=True):
		"""
		:param dry_run: bool: set to False to actually commit changes to LDAP
		"""
		self.dry_run = dry_run
		self.config = Configuration()
		self.logger = get_logger()
		self.factory = Factory()
		self.result_exporter = self.factory.make_result_exporter()
		self.password_exporter = self.factory.make_password_exporter()
		self.errors = list()

	def mass_import(self):
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

	def import_users(self):
		self.logger.info("------ Importing users... ------")
		user_import = self.factory.make_user_importer(self.dry_run)
		imported_users = user_import.read_input()
		users_to_delete = user_import.detect_users_to_delete()
		user_import.delete_users(users_to_delete)
		user_import.create_and_modify_users(imported_users)
		self.errors.extend(user_import.errors)
		user_import.log_stats()
		if self.config["output"]["new_user_passwords"]:
			nup = datetime.datetime.now().strftime(self.config["output"]["new_user_passwords"])
			self.logger.info("------ Writing new users passwords to %s... ------", nup)
			self.password_exporter.dump(user_import, nup)
		if self.config["output"]["user_import_summary"]:
			uis = datetime.datetime.now().strftime(self.config["output"]["user_import_summary"])
			self.logger.info("------ Writing user import summary to %s... ------", uis)
			self.result_exporter.dump(user_import, uis)
		self.logger.info("------ Importing users done. ------")
