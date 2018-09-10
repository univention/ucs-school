# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2017-2018 Univention GmbH
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
CSV reader for CSV files created for HTTP-API import.
"""

from ucsschool.importer.configuration import Configuration
from ucsschool.importer.reader.csv_reader import CsvReader
from ucsschool.lib.models.user import Staff


class HttpApiCsvReader(CsvReader):
	def __init__(self):
		# __init__() cannot have arguments, as it has replaced
		# DefaultUserImportFactory.make_reader() and is instantiated from
		# UserImport.__init__() without arguments.
		# So we'll fetch the necessary information from the configuration.
		self.config = Configuration()
		filename = self.config["input"]["filename"]
		header_lines = self.config["csv"]["header_lines"]
		super(HttpApiCsvReader, self).__init__(filename, header_lines)
		self.config = Configuration()

	def handle_input(self, mapping_key, mapping_value, csv_value, import_user):
		"""
		Handle class names (prepend school name to class names).
		"""
		if mapping_value == 'school_classes':
			if not isinstance(import_user, Staff):  # ignore column if user is staff
				import_user.school_classes = {
					self.config['school']: ['{}-{}'.format(self.config['school'], sc.strip()) for sc in csv_value.split(',') if sc.strip()]
				}
			return True
		return super(HttpApiCsvReader, self).handle_input(mapping_key, mapping_value, csv_value, import_user)
