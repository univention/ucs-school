# -*- coding: utf-8 -*-
#
# Univention UCS@School
"""
Default implementation of the Abstract Factory.
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


from ucsschool.lib.models.utils import ucr
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff

from ucsschool.importer.reader.csv_reader import CsvReader
from ucsschool.importer.writer.user_import_csv_result_exporter import UserImportCsvResultExporter
from ucsschool.importer.writer.csv_writer import CsvWriter
from ucsschool.importer.writer.new_user_password_csv_exporter import NewUserPasswordCsvExporter
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.mass_import.mass_import import MassImport
from ucsschool.importer.models.import_user import ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff
from ucsschool.importer.mass_import.user_import import UserImport
from ucsschool.importer.utils.username_handler import UsernameHandler


class DefaultFactory(object):
	"""
	Default implementation of the Abstract Factory.

	Subclass this and store the fully dotted class name in config["factory"]
	to make the importer code use your classes.
	"""
	def __init__(self):
		self.config = Configuration()

	def make_reader(self, **kwargs):
		"""
		Creates an input data reader.

		:param kwarg: list: passed to the reader constructor
		:return:
		"""
		if self.config["input"]["type"] == "csv":
			kwargs.update(dict(
				filename=self.config["input"]["filename"],
				header_lines=self.config["csv"]["header_lines"]))
			return CsvReader(**kwargs)
		else:
			raise NotImplementedError()

	def make_import_user(self, cur_user_roles, *arg, **kwargs):
		"""
		Creates a ImportUser of specific type, depending on its roles.

		:param cur_user_roles: list: [ucsschool.lib.roles, ..]
		:param arg: list: passed to constructor of created class
		:param kwarg: dict: passed to constructor of created class
		:return: ImportUser: object of ImportUser subclass
		"""
		if role_pupil in cur_user_roles:
			return ImportStudent(*arg, **kwargs)
		if role_teacher in cur_user_roles:
			if role_staff in cur_user_roles:
				return ImportTeachersAndStaff(*arg, **kwargs)
			else:
				return ImportTeacher(*arg, **kwargs)
		else:
			return ImportStaff(*arg, **kwargs)

	def make_mass_importer(self, dry_run=True):
		"""
		Creates a MassImport object.

		:param dry_run: bool: set to False to actually commit changes to LDAP
		:return: MassImport object
		"""
		return MassImport(dry_run=dry_run)

	def make_password_exporter(self, *arg, **kwargs):
		"""
		Creates a ResultExporter object that can dump passwords to disk.

		:param arg: list: passed to constructor of created class
		:param kwarg: dict: passed to constructor of created class
		:return: ucsschool.importer.writer.result_exporter.ResultExporter object
		"""
		# TODO
		return NewUserPasswordCsvExporter(*arg, **kwargs)

	def make_result_exporter(self, *arg, **kwargs):
		"""
		Creates a ResultExporter object.

		:param arg: list: passed to constructor of created class
		:param kwarg: dict: passed to constructor of created class
		:return: ucsschool.importer.writer.result_exporter.ResultExporter object
		"""
		return UserImportCsvResultExporter(*arg, **kwargs)

	def make_user_importer(self, dry_run=True):
		"""
		Creates a user importer.

		:param dry_run: bool: set to False to actually commit changes to LDAP
		:return: UserImport object
		"""
		return UserImport(dry_run=dry_run)

	def make_ucr(self):
		"""
		Get a initialized UCR instance.

		:return: ConfigRegistry object
		"""
		return ucr

	def make_username_handler(self, username_max_length):
		"""
		Get a UsernameHandler instance.

		:param username_max_length: int: created usernames must not be longer
		than this
		:return: UsernameHandler object
		"""
		return UsernameHandler(username_max_length)

	def make_user_writer(self, *arg, **kwargs):
		"""
		Creates a user writer object.

		:param arg: list: passed to constructor of created class
		:param kwarg: dict: passed to constructor of created class
		:return: ucsschool.importer.writer.BaseWriter object
		"""
		return CsvWriter(*arg, **kwargs)
