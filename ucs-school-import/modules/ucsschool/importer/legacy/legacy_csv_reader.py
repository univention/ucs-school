# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
CSV reader for CSV files using the legacy import format.
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

import csv

from ucsschool.importer.reader.csv_reader import CsvReader
from ucsschool.importer.exceptions import UnkownRole
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff


class LegacyCsvReader(CsvReader):
	def handle_input(self, mapping_key, mapping_value, csv_value, import_user):
		"""
		Mark __is_staff and __is_teacher as already handled (in get_roles()).
		Handle __activate (reverse meaning of user.disabled).
		"""
		if mapping_value in ["__is_staff", "__is_teacher"]:
			return True
		elif mapping_value == "__activate":
			if csv_value == "0":
				import_user.disabled = "all"
			else:
				import_user.disabled = "none"
			return True
		return super(LegacyCsvReader, self).handle_input(mapping_key, mapping_value, csv_value, import_user)

	def get_roles(self, input_data):
		"""
		Detect the ucsschool.lib.roles from the input data.

		:param input_data: dict user from read()
		:return: list: [ucsschool.lib.roles, ..]
		"""
		try:
			return super(LegacyCsvReader, self).get_roles(input_data)
		except UnkownRole:
			pass

		roles = list()
		for k, v in self.config["csv"]["mapping"].items():
			if v == "__is_teacher" and input_data[k] == "1":
				roles.append(role_teacher)
			elif v == "__is_staff" and input_data[k] == "1":
				roles.append(role_staff)
		if not roles:
			roles.append(role_pupil)
		return roles
