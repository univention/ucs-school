# -*- coding: utf-8 -*-
#
# Univention UCS@School
"""
CSV reader for CSV files using the new import format.
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

from csv import reader as csv_reader, Sniffer
import codecs

from ucsschool.importer.contrib.csv import DictReader
from ucsschool.importer.reader.base_reader import BaseReader
from ucsschool.importer.exceptions import UnkownRole
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from ucsschool.lib.models.user import Staff


class CsvReader(BaseReader):
	_attrib_names = dict()  # cache for Attribute names
	encoding = "utf-8"

	@classmethod
	def get_dialect(cls, fp):
		"""
		Overwrite me to force a certain CSV dialect.

		:param fp: open file to read from
		:return: csv.dialect
		"""
		return Sniffer().sniff(fp.read(1024))

	def read(self, *args, **kwargs):
		"""
		Generate dicts from a CSV file.

		:param args: ignored
		:param kwargs: dict: if it has a dict "csv_reader_args", that will be
		used as additional arguments for the DictReader constructor.
		:return: iter(dict)
		"""
		with open(self.filename, "rb") as fp:
			dialect = self.get_dialect(fp)
			fp.seek(0)
			if self.header_lines == 1:
				header = None
			else:
				# skip header_lines
				for line_ in range(self.header_lines):
					fp.readline()
				start = fp.tell()
				# no header names, detect number of rows

				fpu = UTF8Recoder(fp, self.encoding)
				reader = csv_reader(fpu, dialect=dialect)
				line = reader.next()
				fp.seek(start)
				header = map(str, range(len(line)))
			csv_reader_args = dict(fieldnames=header, dialect=dialect)
			csv_reader_args.update(kwargs.get("csv_reader_args", {}))
			fpu = UTF8Recoder(fp, self.encoding)
			reader = DictReader(fpu, **csv_reader_args)
			for row in reader:
				self.entry_count = reader.line_num
				self.input_data = reader.row
				yield {unicode(key, 'utf-8'): unicode(value or "", 'utf-8') for key, value in row.iteritems()}

	def handle_input(self, mapping_key, mapping_value, csv_value, import_user):
		"""
		This is a hook into map().
		IMPLEMENT ME if you wish to handle certain columns from the CSV file
		yourself.

		:param mapping_key: str: the key in config["csv"]["mapping"]
		:param mapping_value: str: the value in config["csv"]["mapping"]
		:param csv_value: str: the associated value from the CSV line
		:param import_user: ImportUser: the object to modify
		:return: bool: True if the field was handles here. It will be ignored
		in map(). False if map() should handle the field.
		"""
		if mapping_value == "__ignore":
			return True
		elif mapping_value == "__action":
			import_user.action = csv_value
			return True
		elif mapping_value == "school_class" and isinstance(import_user, Staff):
			# ignore column
			return True
		return False

	def get_roles(self, input_data):
		"""
		IMPLEMENT ME if the user role is not set in the configuration file or
		by cmdline.
		Detect the ucsschool.lib.roles from the input data.

		:param input_data: dict user from read()
		:return: list: [ucsschool.lib.roles, ..]
		"""
		try:
			return {
				"student": [role_pupil],
				"staff": [role_staff],
				"teacher": [role_teacher],
				"teacher_and_staff": [role_teacher, role_staff]
			}[self.config["user_role"]]
		except KeyError:
			raise UnkownRole("No role in configuration.", entry=self.entry_count)

	def map(self, input_data, cur_user_roles):
		"""
		Creates a ImportUser object from a users dict. Data will not be
		modified, just copied.

		:param input_data: dict: user from read()
		:param cur_user_roles: list: [ucsschool.lib.roles, ..]
		:return: ImportUser
		"""
		import_user = self.factory.make_import_user(cur_user_roles)
		attrib_names = self._get_attrib_name(import_user)
		for k, v in self.config["csv"]["mapping"].items():
			if self.handle_input(k, v, input_data[k], import_user):
				# has been handled
				continue
			if v in attrib_names:
				# it is an Attribute
				setattr(import_user, v, input_data[k])
			else:
				# must be a UDM property
				import_user.udm_properties[v] = input_data[k]
		self.logger.debug("%s udm_properties=%r", import_user, import_user.udm_properties)
		return import_user

	@classmethod
	def _get_attrib_name(cls, import_user):
		"""
		Cached retrieval of names of Attributes of an ImportUser.

		:param import_user: an ImportUser object
		:return: list: names of Attributes
		"""
		cls_name = import_user.__class__.__name__
		if cls_name not in cls._attrib_names:
			cls._attrib_names[cls_name] = import_user.to_dict().keys()
		return cls._attrib_names[cls_name]


class UTF8Recoder(object):
	"""
	Iterator that reads an encoded stream and reencodes the input to UTF-8.
	Blatantly copied from docs.python.org/2/library/csv.html
	"""
	def __init__(self, f, encoding):
		self.reader = codecs.getreader(encoding)(f)

	def __iter__(self):
		return self

	def next(self):
		return self.reader.next().encode("utf-8")
