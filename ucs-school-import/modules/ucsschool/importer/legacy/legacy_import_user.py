# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
ImportUser subclass for import using legacy CSV format.
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

from ldap.filter import filter_format

from univention.admin.uexceptions import noObject
from ucsschool.lib.models import Staff, Student, Teacher, TeachersAndStaff
from ucsschool.importer.models.import_user import ImportStaff, ImportStudent, ImportTeacher, \
	ImportTeachersAndStaff, ImportUser
from ucsschool.importer.exceptions import UnkownAction


class LegacyImportUser(ImportUser):

	def make_disabled(self):
		"""
		Handled in LegacyCsvReader.handle_input(). Overwriting here, so
		changes in ImportUser do not change behavior of LegacyImportUser.
		"""

	def make_firstname(self):
		"""
		Do not normalize given names.
		"""
		if self.firstname:
			return
		elif "firstname" in self.config["scheme"]:
			self.firstname = self.format_from_scheme("firstname", self.config["scheme"]["firstname"])
		else:
			self.firstname = ""

	def make_lastname(self):
		"""
		Do not normalize family names.
		"""
		if self.lastname:
			return
		elif "lastname" in self.config["scheme"]:
			self.lastname = self.format_from_scheme("lastname", self.config["scheme"]["lastname"])
		else:
			self.lastname = ""

	def make_username(self):
		super(LegacyImportUser, self).make_username()
		self.old_name = self.name  # for LegacyNewUserPasswordCsvExporter.serialize()
		self.name = self.name.lower()

	def run_checks(self, check_username=False):
		"""
		Action must already be configured in CSV.
		"""
		super(LegacyImportUser, self).run_checks()

		if self.action and self.action not in ["A", "D", "M"]:
			raise UnkownAction("Unknown action '{}'.".format(self.action))

	@classmethod
	def get_by_import_id_or_username(cls, connection, source_uid, record_uid, username, superordinate=None):
		"""
		Retrieve a LegacyImportUser.
		Will find it using either source_uid and record_uid or if unset
		with the username.

		:param connection: uldap object
		:param source_uid: str: source DB identifier
		:param record_uid: str: source record identifier
		:param username: str: username
		:param superordinate: str: superordinate
		:return: object of ImportUser subclass from LDAP or raises noObject
		"""
		filter_s = filter_format(
			"(&(objectClass=ucsschoolType)"
			"(|"
			"(&(ucsschoolSourceUID=%s)(ucsschoolRecordUID=%s))"
			"(&(!(ucsschoolSourceUID=*))(!(ucsschoolRecordUID=*))(uid=%s))"
			"))",
			(source_uid, record_uid, username))
		obj = cls.get_only_udm_obj(connection, filter_s, superordinate=superordinate)
		if not obj:
			raise noObject("No user with source_uid={0}, record_uid={1} or username={2} found.".format(source_uid, record_uid, username))
		return cls.from_udm_obj(obj, None, connection)

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		"""
		IMPLEMENTME if you subclass!
		"""
		klass = super(LegacyImportUser, cls).get_class_for_udm_obj(udm_obj, school)
		if issubclass(klass, TeachersAndStaff):
			return LegacyImportTeachersAndStaff
		elif issubclass(klass, Teacher):
			return LegacyImportTeacher
		elif issubclass(klass, Staff):
			return LegacyImportStaff
		elif issubclass(klass, Student):
			return LegacyImportStudent
		else:
			return None


class LegacyImportStudent(LegacyImportUser, ImportStudent):
	pass


class LegacyImportStaff(LegacyImportUser, ImportStaff):
	pass


class LegacyImportTeacher(LegacyImportUser, ImportTeacher):
	pass


class LegacyImportTeachersAndStaff(LegacyImportUser, ImportTeachersAndStaff):
	pass
