#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Class to export test user data from TestUserCreator to CSV.
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

from ucsschool.importer.writer.csv_writer import CsvWriter
from ucsschool.importer.writer.result_exporter import ResultExporter


class TestUserCsvExporter(ResultExporter):
	field_names = ("Schulen", "Benutzertyp", "Vorname", "Nachname", "Klassen", "Beschreibung", "Telefon")

	def __init__(self, email=False, *args, **kwargs):
		if not email:
			self.field_names += ("EMail", )
		super(TestUserCsvExporter, self).__init__(*args, **kwargs)

	def get_iter(self, user_import):
		# TestUserCreator.make_users() is already a generator
		return user_import

	def get_writer(self):
		return CsvWriter(field_names=self.field_names)

	def serialize(self, user):
		if user["Klassen"]:
			sc = ""
			for school, classes in user["Klassen"].items():
				sc = ",".join([sc, ",".join(["{}-{}".format(school, cls) for cls in classes])])
			user["Klassen"] = sc.strip(",")
		else:
			user["Klassen"] = ""
		user["Schulen"] = ",".join(user["Schulen"])
		for k, v in user.items():
			user[k] = v.encode("utf-8")
		return user
