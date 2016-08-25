# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
CSV reader for CSV files created by TestUserCsvExporter.
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

from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.reader.csv_reader import CsvReader
from ucsschool.importer.exceptions import UnkownRole


class TestCsvReader(CsvReader):
	roles_mapping = {
		"student": [role_pupil],
		"staff": [role_staff],
		"teacher": [role_teacher],
		"staffteacher": [role_teacher, role_staff]
	}

	def __init__(self):
		# __init__() cannot have arguments, as it has replaced
		# DefaultUserImportFactory.make_reader() and is instantiated from
		# UserImport.__init__() without arguments.
		# So we'll fetch the necessary information from the configuration.
		self.config = Configuration()
		filename = self.config["input"]["filename"]
		header_lines = self.config["csv"]["header_lines"]
		super(TestCsvReader, self).__init__(filename, header_lines)

	def handle_input(self, mapping_key, mapping_value, csv_value, import_user):
		"""
		Handle user type.
		"""
		if mapping_value == "__type":
			return True
		return super(TestCsvReader, self).handle_input(mapping_key, mapping_value, csv_value, import_user)

	def get_roles(self, input_data):
		"""
		Get role from CSV.
		"""
		try:
			return super(TestCsvReader, self).get_roles(input_data)
		except UnkownRole:
			pass

		roles = list()
		for k, v in self.config["csv"]["mapping"].items():
			if v == "__type":
				role_str = input_data[k]
				roles = self.roles_mapping[role_str]
				break
		return roles
