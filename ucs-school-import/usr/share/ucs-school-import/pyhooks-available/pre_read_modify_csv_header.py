# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2019 Univention GmbH
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
A pre-read hooks that changes the header of a input CSV file.

A mapping is read from the configuration file (csv:header_swap), the original
CSV file is backuped and the header is changed.

If a mapping key is not found in the input file, it is ignored.

Example::
	{
		"csv": {
			"header_swap": {
				"Schulen Ost": "Schulen",
				"Schulname": "Schulen",
				"Familienname": "Nachname"
			}
		}
	}
	header 1 before: "ID","Vorname","Nachname","Email","Schulen Ost"
	header 1 after : "ID","Vorname","Nachname","Email","Schulen"
	header 2 before: "ID","Familienname,"Vorname","Schulname"
	header 2 after : "ID","Nachname,"Vorname","Schulen"
"""

import csv
import codecs
import shutil
import datetime
from ucsschool.importer.exceptions import ConfigurationError
from ucsschool.importer.reader.csv_reader import CsvReader, UTF8Recoder
from ucsschool.importer.utils.pre_read_pyhook import PreReadPyHook
try:
	import typing
except ImportError:
	pass


class ModifyCsvHeader(PreReadPyHook):
	"""
	Hook is called before starting to read the input file to change the header
	of the CSV input file.
	"""
	priority = {
		'pre_read': 1000,
	}

	def pre_read(self):  # type: () -> None
		"""
		* get mapping from the configuration file (csv:header_swap)
		* backup original CSV file to {input:filename}.$date.bak.csv
		* modify CSV file (input:filename)

		:return: None
		"""
		if not self.config['csv'].get('header_swap'):
			raise ConfigurationError('Missing configuration key csv:header_swap.')

		ori_file_name = self.config['input']['filename']
		backup_file_name = '{}.{:%Y-%m-%d_%H:%M:%S}.bak.csv'.format(ori_file_name, datetime.datetime.now())
		self.logger.info('Copying %r to %r...', ori_file_name, backup_file_name)
		shutil.copy2(ori_file_name, backup_file_name)

		encoding = CsvReader.get_encoding(backup_file_name)
		with open(backup_file_name, 'r') as fp:
			dialect = csv.Sniffer().sniff(fp.readline())

		self.logger.info('Rewriting %r...', ori_file_name)
		with open(backup_file_name, 'r') as fpr, open(ori_file_name, 'w') as fpw:
			fpru = UTF8Recoder(fpr, encoding)
			encoder = codecs.getincrementalencoder(encoding)()
			writer = csv.writer(fpw, dialect=dialect)
			for row in csv.reader(fpru, dialect=dialect):
				writer.write([encoder.encode(r) for r in row])
		self.logger.info('Done.')
