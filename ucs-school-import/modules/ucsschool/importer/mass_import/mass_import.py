# -*- coding: utf-8 -*-
#
# Univention UCS@School
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

from ucsschool.importer.factory import Factory
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.utils.logging2udebug import get_logger


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
		self.writer = self.factory.make_writer(self.config["csv_output"])

	def mass_import(self):
		self.logger.info("------ Importing users... ------")
		self.import_users()
		self.logger.info("------ Importing users done. ------")
		# TODO: support import of other objects

	def import_users(self):
		user_import = self.factory.make_user_importer(self.dry_run)
		imported_users = user_import.read_input()
		user_import.create_and_modify_users(imported_users)
		if self.config["no_delete"]:
			self.logger.info("------ Skipping user deletion (no_delete=%r) ------", self.config["no_delete"])
		else:
			users_to_delete = user_import.detect_users_to_delete()
			user_import.delete_users(users_to_delete)
		user_import.log_stats()
		self.writer.output(imported_users, user_import.deleted_users)
