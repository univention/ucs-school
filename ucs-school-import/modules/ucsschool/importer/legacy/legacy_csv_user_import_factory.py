# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Factory implementation for import using CSV in legacy format.
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


from ucsschool.importer.default_user_import_factory import DefaultUserImportFactory
from ucsschool.importer.legacy.legacy_csv_reader import LegacyCsvReader
from ucsschool.importer.legacy.legacy_import_user import LegacyImportStaff, LegacyImportStudent,\
	LegacyImportTeacher, LegacyImportTeachersAndStaff, LegacyImportUser
from ucsschool.importer.legacy.legacy_user_import import LegacyUserImport
from ucsschool.importer.legacy.legacy_new_user_password_csv_exporter import LegacyNewUserPasswordCsvExporter
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff


class LegacyCsvUserImportFactory(DefaultUserImportFactory):

	def make_reader(self, **kwargs):
		"""
		Creates a reader for legacy CSV files.

		:param kwarg: list: passed to the reader constructor
		:return:
		"""
		kwargs.update(dict(
			filename=self.config["input"]["filename"],
			header_lines=self.config["csv"]["header_lines"]))
		return LegacyCsvReader(**kwargs)

	def make_import_user(self, cur_user_roles, *arg, **kwargs):
		"""
		Creates a LegacyImportUser of specific type.

		:param cur_user_roles: list: [ucsschool.lib.roles, ..]
		:param arg: list: passed to constructor of created class
		:param kwarg: dict: passed to constructor of created class
		:return: LegacyImportUser: object of LegacyImportUser subclass
		"""
		if not cur_user_roles:
			return LegacyImportUser(*arg, **kwargs)
		if role_pupil in cur_user_roles:
			return LegacyImportStudent(*arg, **kwargs)
		if role_teacher in cur_user_roles:
			if role_staff in cur_user_roles:
				return LegacyImportTeachersAndStaff(*arg, **kwargs)
			else:
				return LegacyImportTeacher(*arg, **kwargs)
		else:
			return LegacyImportStaff(*arg, **kwargs)

	def make_password_exporter(self, *arg, **kwargs):
		"""
		Creates a ResultExporter object that can dump passwords to disk.

		:param arg: list: passed to constructor of created class
		:param kwarg: dict: passed to constructor of created class
		:return: ucsschool.importer.writer.result_exporter.ResultExporter object
		"""
		return LegacyNewUserPasswordCsvExporter(*arg, **kwargs)

	def make_user_importer(self, dry_run=True):
		"""
		Creates a user importer.

		:param dry_run: bool: set to False to actually commit changes to LDAP
		:return: UserImport object
		"""
		return LegacyUserImport(dry_run=dry_run)
