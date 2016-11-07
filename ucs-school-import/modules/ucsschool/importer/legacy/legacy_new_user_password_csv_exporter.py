# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Write the passwords of newly created users to a CSV file.
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

from csv import excel_tab

from ucsschool.importer.writer.new_user_password_csv_exporter import NewUserPasswordCsvExporter
from ucsschool.importer.configuration import Configuration


class LegacyNewUserPasswordCsvExporter(NewUserPasswordCsvExporter):
	"""
	Export passwords of new users to a CSV file.

	Recreate line from legacy import script:
	OUTFILE.write("%s\t%s\t%s" % (person.login, password, line))
	"""
	field_names = ("username", "password", "action", "name", "lastname", "firstname", "school", "school_class", "ignore", "email", "is_teacher", "activate", "is_staff")

	def __init__(self, *arg, **kwargs):
		super(LegacyNewUserPasswordCsvExporter, self).__init__(*arg, **kwargs)
		self.config = Configuration()

	def get_writer(self):
		"""
		Change to CSV dialect with tabs and don't write a header line.
		"""
		writer = self.factory.make_user_writer(field_names=self.field_names, dialect=excel_tab)
		writer.write_header = lambda x: None  # no header line
		return writer

	def serialize(self, user):
		res = dict(username=user.name, password=user.password)
		input_data = list(user.input_data)
		line = zip(self.field_names[2:], input_data)
		res.update(line)
		return res
