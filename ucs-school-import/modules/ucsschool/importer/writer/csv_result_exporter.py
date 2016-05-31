# -*- coding: utf-8 -*-
#
# Univention UCS@School
"""
Write the result of a user import job to a CSV file.
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
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.importer.exceptions import UcsSchoolImportError
from ucsschool.importer.writer.result_exporter import ResultExporter
from ucsschool.lib.roles import role_pupil


class CsvResultExporter(ResultExporter):
	field_names = ("line", "success", "error", "action", "role", "username", "schools", "firstname", "lastname",
		"birthday", "email", "disabled", "classes", "source_uid", "record_uid", "error_msg")

	def __init__(self, *arg, **kwargs):
		"""
		Create a CSV file writer.

		:param arg: list: ignored
		:param kwargs: dict: set "dialect" to the desired CSV dialect (as
		supported by the Python CSV library). If unset will try to detect
		dialect of input file or fall back to "excel".
		"""
		super(CsvResultExporter, self).__init__(*arg, **kwargs)
		self.factory = Factory()

	def get_iter(self, user_import):
		"""
		Iterator over all ImportUsers and errors of the user import.
		First errors, then added, modified and deleted users.

		:param user_import: UserImport object used for the import
		:return: iterator: both ImportUsers and UcsSchoolImportError objects
		"""
		li = user_import.errors
		map(li.extend, user_import.added_users.values())
		map(li.extend, user_import.modified_users.values())
		map(li.extend, user_import.deleted_users.values())
		return li

	def get_writer(self):
		"""
		Object that will write the data to disk/network in the desired format.

		:return: an object that knows how to write data
		"""
		return self.factory.make_user_writer(field_names=self.field_names)

	def serialize(self, obj):
		"""
		Make a dict of attr_name->strings from an import object.

		:param obj: object to serialize
		:return: dict: attr_name->strings that will be used to write the
		output file
		"""
		if isinstance(obj, ImportUser):
			user = obj
		elif isinstance(obj, UcsSchoolImportError):
			user = obj.import_user
		else:
			raise TypeError("Expected ImportUser or UcsSchoolImportError, got {}. Repr: {}".format(type(obj), repr(obj)))
		if not user:
			# error during reading of input data
			user = self.factory.make_import_user([role_pupil])  # set some role
			user.roles = []  # remove role

		return dict(
			line=max(getattr(user, "entry_count", -1), getattr(obj, "entry", -1)),
			success=int(bool(isinstance(obj, ImportUser))),
			error=int(bool(isinstance(obj, UcsSchoolImportError))),
			action=user.action,
			role=user.role_sting if user.roles else "",
			username=user.name,
			schools=" ".join(user.schools) if user.schools else user.school,
			firstname=user.firstname,
			lastname=user.lastname,
			birthday=user.birthday,
			email=user.email,
			disabled="0" if user.disabled == "none" else "1",
			classes=getattr(user, "school_class", ""),
			source_uid=user.source_uid,
			record_uid=user.record_uid,
			error_msg=str(obj) if isinstance(obj, UcsSchoolImportError) else ""
			)
