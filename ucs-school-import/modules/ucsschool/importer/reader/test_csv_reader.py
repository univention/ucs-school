# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
CSV reader for CSV files created by TestUserCsvExporter.
"""
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

from ucsschool.importer.configuration import Configuration
from ucsschool.importer.reader.csv_reader import CsvReader


class TestCsvReader(CsvReader):
	"""
	This class has been deprecated. Please use "CsvReader" instead. It now
	also handles a "__role" column (replace "__type" in the mapping
	configuration with "__role").
	"""
	_role_method = CsvReader.get_roles_from_csv
	_csv_roles_value = '__type'

	def __init__(self):
		# __init__() cannot have arguments, as it has replaced
		# DefaultUserImportFactory.make_reader() and is instantiated from
		# UserImport.__init__() without arguments.
		# So we'll fetch the necessary information from the configuration.
		self.config = Configuration()
		filename = self.config["input"]["filename"]
		header_lines = self.config["csv"]["header_lines"]
		super(TestCsvReader, self).__init__(filename, header_lines)
		self.logger.warn(
			'The "TestCsvReader" class has been deprecated. Please use "CsvReader" and use "__role" instead of "__type"'
			' in the mapping configuration.'
		)
