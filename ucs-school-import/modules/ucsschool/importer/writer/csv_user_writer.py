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

from csv import DictWriter

from ucsschool.importer.configuration import Configuration
from ucsschool.importer.factory import Factory
from ucsschool.importer.writer.writer import Writer


class CsvUserWriter(Writer):
	def __init__(self, field_names, dialect=None):
		"""
		Create a CSV file writer.

		:param field_names: list: names of the columns
		:param dialect: csv.dialect: If unset will try to detect
		dialect of input file or fall back to "excel".
		"""
		super(CsvUserWriter, self).__init__()
		self.field_names = field_names
		self.dialect = dialect

		if not self.dialect:
			# try to use the same dialect as was used by the import - if it
			# was a CSV import
			config = Configuration()
			if config["input"]["type"] == "csv":
				reader = Factory().make_reader()
				with open(config["input"]["filename"], "rb") as fp:
					self.dialect = reader.get_dialect(fp)
			else:
				self.dialect = "excel"
		self.writer = None

	def open(self, filename, mode="wb"):
		"""
		Open the output file.

		:param filename:  str: filename to write data to
		:param mode: str: passed to used open() method
		:return: DictWriter
		"""
		fp = open(filename, mode)
		self.writer = DictWriter(fp, fieldnames=self.field_names, dialect=self.dialect)
		return fp

	def write_header(self, header):
		"""
		Write a header line before the main data.

		:param header: object to write as header (ignored)
		:return: None
		"""
		self.writer.writeheader()

	def write_obj(self, obj):
		"""
		Write object to output.

		:param obj: dict: data to write
		:return: None
		"""
		return self.writer.writerow(obj)
