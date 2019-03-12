# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2019 Univention GmbH
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
CSV reader for CSV files using the new import format.
"""

from csv import reader as csv_reader, Sniffer, Error as CsvError
import codecs
import sys

from six import string_types
import magic

from ucsschool.importer.contrib.csv import DictReader
from ucsschool.importer.reader.base_reader import BaseReader
from ucsschool.importer.exceptions import ConfigurationError, InitialisationError, NoRole, UnknownRole, UnknownProperty
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from ucsschool.lib.models.user import Staff
import univention.admin.handlers.users.user as udm_user_module
import univention.admin.modules
try:
	from typing import Any, BinaryIO, Callable, Dict, Iterable, Iterator, List, Optional, Union
	from csv import Dialect
except ImportError:
	pass


class CsvReader(BaseReader):
	"""
	Reads CSV files and turns lines to ImportUser objects.
	"""
	_attrib_names = dict()  # type: Dict[str, Iterable[str]]  # cache for Attribute names
	_role_method = None  # type: Callable  # method to get users role
	_csv_roles_mapping = {
		"student": [role_pupil],
		"staff": [role_staff],
		"teacher": [role_teacher],
		"staffteacher": [role_teacher, role_staff],
		"teacher_and_staff": [role_teacher, role_staff],
	}  # known values for "__role" column
	_csv_roles_key = None  # type: str  # column name in the mapping configuration
	_csv_roles_value = "__role"  # mapping value, so column will be used as role

	encoding = "utf-8"

	def __init__(self, filename, header_lines=0, **kwargs):  # type: (str, Optional[int], **Any) -> None
		"""
		:param str filename: Path to file with user data.
		:param int header_lines: Number of lines before the actual data starts.
		:param dict kwargs: optional parameters for use in derived classes
		"""
		super(CsvReader, self).__init__(filename, header_lines, **kwargs)
		self.fieldnames = None  # type: Iterable[str]
		usersmod = univention.admin.modules.get("users/user")
		univention.admin.modules.init(self.lo, self.position, usersmod)

	@staticmethod
	def get_encoding(filename_or_file):  # type: (Union[str, BinaryIO]) -> str
		"""
		Get encoding of file ``filename_or_file``.

		Handles both magic libraries.

		:param filename_or_file: filename or open file
		:type filename_or_file: str or file
		:return: encoding of filename_or_file
		:rtype: str
		"""
		if isinstance(filename_or_file, string_types):
			with open(filename_or_file, 'rb') as fp:
				txt = fp.read()
		elif isinstance(filename_or_file, file):
			old_pos = filename_or_file.tell()
			txt = filename_or_file.read()
			filename_or_file.seek(old_pos)
		else:
			raise ValueError('Argument "filename_or_file" has unknown type {!r}.'.format(type(filename_or_file)))
		if hasattr(magic, 'from_file'):
			encoding = magic.Magic(mime_encoding=True).from_buffer(txt)
		elif hasattr(magic, 'detect_from_filename'):
			encoding = magic.detect_from_content(txt).encoding
		else:
			raise RuntimeError('Unknown version or type of "magic" library.')
		# auto detect utf-8 with BOM
		if encoding == 'utf-8' and txt.startswith(codecs.BOM_UTF8):
			encoding = 'utf-8-sig'
		return encoding

	def get_dialect(self, fp):  # type: (BinaryIO) -> Dialect
		"""
		Overwrite me to force a certain CSV dialect.

		:param file fp: open file to read from
		:return: CSV dialect
		:rtype: csv.Dialect
		"""
		delimiter = self.config.get("csv", {}).get("delimiter")
		return Sniffer().sniff(fp.readline(), delimiters=delimiter)

	def read(self, *args, **kwargs):  # type: (*Any, **Any) -> Iterator[Dict[unicode, unicode]]
		"""
		Generate dicts from a CSV file.

		:param args: ignored
		:param dict kwargs: if it has a dict `csv_reader_args`, that will be used as additional arguments for the :py:class:`DictReader` constructor.
		:return: iterator over list of dicts
		:rtype: Iterator
		"""
		with open(self.filename, "rb") as fp:
			try:
				dialect = self.get_dialect(fp)
			except CsvError as exc:
				raise InitialisationError, InitialisationError("Could not determine CSV dialect. Try setting the csv:delimiter configuration. Error: {}".format(exc)), sys.exc_info()[2]
			fp.seek(0)
			encoding = self.get_encoding(fp)
			self.logger.debug('Reading %r with encoding %r.', self.filename, encoding)
			if self.header_lines == 1:
				# let DictReader figure it out itself
				header = None
			else:
				# skip header_lines
				for line_ in range(self.header_lines):
					fp.readline()
				start = fp.tell()
				# no header names, detect number of rows

				fpu = UTF8Recoder(fp, encoding)
				_reader = csv_reader(fpu, dialect=dialect)
				line = _reader.next()
				fp.seek(start)
				header = map(str, range(len(line)))
			csv_reader_args = dict(fieldnames=header, dialect=dialect)
			csv_reader_args.update(kwargs.get("csv_reader_args", {}))
			fpu = UTF8Recoder(fp, encoding)
			reader = DictReader(fpu, **csv_reader_args)
			self.fieldnames = reader.fieldnames
			missing_columns = self._get_missing_columns()
			if missing_columns:
				raise ConfigurationError('Columns configured in csv:mapping missing: {}.'.format(
					', '.join(missing_columns)))
			for row in reader:
				self.entry_count = reader.line_num
				self.input_data = reader.row
				yield {
					unicode(key, 'utf-8').strip(): unicode(value or "", 'utf-8').strip()
					for key, value in row.iteritems()
				}

	def handle_input(
			self,
			mapping_key,  # type: str
			mapping_value,  # type: str
			csv_value,  # type: str
			import_user  # type: ImportUser
	):
		# type: (...) -> bool
		"""
		This is a hook into :py:meth:`map`.

		IMPLEMENT ME if you wish to handle certain columns from the CSV file
		yourself.

		:param str mapping_key: the key in config["csv"]["mapping"]
		:param str mapping_value: the value in config["csv"]["mapping"]
		:param str csv_value: the associated value from the CSV line
		:param ImportUser import_user: the object to modify
		:return: True if the field was handles here. It will be ignored in map(). False if map() should handle the field.
		:rtype: bool
		"""
		if mapping_value == "__ignore":
			return True
		elif mapping_value == "__action":
			import_user.action = csv_value
			return True
		elif mapping_value == self._csv_roles_value:
			self._role_method = self.get_roles_from_csv  # type: Callable
			return True
		elif mapping_value == "school_classes" and isinstance(import_user, Staff):
			# ignore column
			return True
		return False

	def get_roles(self, input_data):  # type: (Dict[str, Any]) -> Iterable[str]
		"""
		Detect the ucsschool.lib.roles from the input data or configuration.

		IMPLEMENT ME if the user role is not set in the configuration (file or
		by cmdline) or in the CSV mapped by `__role`.

		`__role` can be something else, if configured in
		:py:attr:`_csv_roles_key`.

		:param dict input_data: dict user from read()
		:return: list of roles [ucsschool.lib.roles, ..]
		:rtype: list(str)
		"""
		if self._role_method:
			return self._role_method(input_data)

		# try to get roles from CSV, if not found, use configuration / cmdline
		try:
			roles = self.get_roles_from_csv(input_data)
			self._role_method = self.get_roles_from_csv
		except NoRole:
			roles = self.get_roles_from_configuration(input_data)
			self._role_method = self.get_roles_from_configuration
		return roles

	def get_roles_from_configuration(self, input_data):
		try:
			return {
				"student": [role_pupil],
				"staff": [role_staff],
				"teacher": [role_teacher],
				"teacher_and_staff": [role_teacher, role_staff]
			}[self.config["user_role"]]
		except KeyError:
			raise NoRole("No role in configuration.", entry_count=self.entry_count)

	def get_roles_from_csv(self, input_data):  # type: (Dict[str, Any]) -> Iterable[str]
		if not self._csv_roles_key:
			# find column for role in mapping
			for k, v in self.config["csv"]["mapping"].items():
				if v == self._csv_roles_value:
					self._csv_roles_key = k
					break
			else:
				raise NoRole(
					'No {!r} column found in mapping configuration.'.format(self._csv_roles_key),
					entry_count=self.entry_count
				)
		role_str = input_data[self._csv_roles_key]
		try:
			roles = self._csv_roles_mapping[role_str]
		except KeyError:
			raise UnknownRole(
				'Unknown role {!r} found in {!r} column.'.format(role_str, self._csv_roles_key),
				entry_count=self.entry_count
			)
		return roles

	def map(self, input_data, cur_user_roles):  # type: (List[str], Iterable[str]) -> ImportUser
		"""
		Creates a ImportUser object from a users dict. Data will not be
		modified, just copied.

		:param dict input_data: user from read()
		:param cur_user_roles: [ucsschool.lib.roles, ..]
		:type cur_user_roles: list(str)
		:return: ImportUser instance
		:rtype: ImportUser
		"""
		import_user = self.factory.make_import_user(cur_user_roles)
		attrib_names = self._get_attrib_name(import_user)
		for k, v in self.config["csv"]["mapping"].items():
			if k not in input_data:
				# broken CSV or mapping
				continue
			if self.handle_input(k, v, input_data[k], import_user):
				# has been handled
				continue
			if v in attrib_names:
				# it is an Attribute
				setattr(import_user, v, input_data[k])
			else:
				# must be a UDM property
				try:
					prop_desc = udm_user_module.property_descriptions[v]
				except KeyError:
					raise UnknownProperty("Unknown UDM property: '{}'.".format(v), entry_count=self.entry_count, import_user=import_user)
				if prop_desc.multivalue:
					try:
						delimiter = self.config["csv"]["incell-delimiter"][k]
					except KeyError:
						delimiter = self.config["csv"].get("incell-delimiter", {}).get("default", ",")
					import_user.udm_properties[v] = input_data[k].split(delimiter)
				else:
					import_user.udm_properties[v] = input_data[k]
		self.logger.debug("%s attributes=%r udm_properties=%r action=%r", import_user, import_user.to_dict(), import_user.udm_properties, import_user.action)
		return import_user

	def get_data_mapping(self, input_data):  # type: (Iterable[str]) -> Dict[str, Any]
		"""
		Create a mapping from the configured input mapping to the actual
		input data.
		Used by `ImportUser.format_from_scheme()`.

		:param input_data: "raw" input data as stored in `ImportUser.input_data`
		:type input_data: list(str)
		:return: key->input_data-value mapping
		:rtype: dict
		"""
		if not self.fieldnames:
			self.read().next()
		dict_reader_mapping = dict(zip(self.fieldnames, input_data))
		res = dict()
		for k, v in self.config["csv"]["mapping"].items():
			try:
				res[v] = dict_reader_mapping[k]
			except KeyError:
				pass
		return res

	@classmethod
	def _get_attrib_name(cls, import_user):  # type: (ImportUser) -> Iterable[str]
		"""
		Cached retrieval of names of Attributes of an ImportUser.

		:param ImportUser import_user: an ImportUser object
		:return: names of Attributes
		:rtype: :func:`list`
		"""
		cls_name = import_user.__class__.__name__
		if cls_name not in cls._attrib_names:
			cls._attrib_names[cls_name] = import_user.to_dict().keys()
		return cls._attrib_names[cls_name]

	def _get_missing_columns(self):
		"""
		Find fieldnames that were configured in the csv:mapping but are
		missing in the input data.

		:return: list(str)
		"""
		return [
			key for key, value in self.config['csv']['mapping'].items()
			if (
				key not in self.fieldnames and
				value != '__ignore' and
				key not in self.config['csv'].get('allowed_missing_columns', [])
			)
		]


class UTF8Recoder(object):
	"""
	Iterator that reads an encoded stream and reencodes the input to UTF-8.
	Blatantly copied from docs.python.org/2/library/csv.html
	"""

	def __init__(self, f, encoding):  # type: (BinaryIO, str) -> None
		self.reader = codecs.getreader(encoding)(f)

	def __iter__(self):  # type: () -> UTF8Recoder
		return self

	def next(self):  # type: () -> str
		return self.reader.next().encode("utf-8")
