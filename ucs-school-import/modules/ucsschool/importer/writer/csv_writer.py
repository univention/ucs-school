# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2018 Univention GmbH
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

"""
Write the result of a user import job to a CSV file.
"""

from csv import DictWriter, excel, QUOTE_ALL
import os
from stat import S_IRUSR, S_IWUSR

from ucsschool.importer.writer.base_writer import BaseWriter


class CsvWriter(BaseWriter):

	def __init__(self, field_names, dialect=None):
		"""
		Create a CSV file writer.

		:param field_names: names of the columns
		:type field_names: list(str)
		:param csv.Dialect dialect: If unset will try to detect dialect of input file or fall back to "excel".
		"""
		super(CsvWriter, self).__init__()
		self.field_names = field_names
		self.dialect = dialect

		if not self.dialect:
			self.dialect = excel()
			self.dialect.doublequote = True
			self.dialect.quoting = QUOTE_ALL

		self.writer = None

	def open(self, filename, mode="wb"):
		"""
		Open the output file.

		:param str filename: filename to write data to
		:param str mode: passed to builtin :py:func:`open()` method
		:return: DictWriter instance
		:rtype: csv.DictWriter
		"""
		with open(filename, mode) as fd:
			os.fchmod(fd.fileno(), S_IRUSR | S_IWUSR)
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

		:param dict obj: data to write
		:return: None
		"""
		return self.writer.writerow(obj)
