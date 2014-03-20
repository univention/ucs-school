#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  UCS@school Batch Upload
#
# Copyright 2014 Univention GmbH
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

import os
import os.path
import uuid # for random string
import csv
from datetime import datetime
import re
import locale

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import file_upload, simple_response
from univention.config_registry import ConfigRegistry
import univention.admin.modules as udm_modules

from ucsschool.lib.schoolldap import SchoolBaseModule, SchoolSearchBase, open_ldap_connection

_ = Translation('ucs-school-umc-csv-import').translate

ucr = ConfigRegistry()
ucr.load()

class FileInfo(object):
	def __init__(self, filename, school, user_klass, dialect, has_header):
		self.filename = filename
		self.school = school
		self.user_klass = user_klass
		self.dialect = dialect
		self.has_header = has_header

class User(object):
	columns = []
	column_labels = {}

	def __init__(self, lo, attrs):
		self._user_dn = None
		self._error_msg = None
		for column in self.columns:
			value = attrs.get(column)
			setattr(self, column, value)
		self.username = self.guess_username(lo)
		if 'action' not in attrs:
			if self.exists(lo):
				self.action = 'modify'
			else:
				self.action = 'create'
		self.errors = {}
		self.warnings = {}

	def get_user_dn(self, lo):
		if self._user_dn is None:
			try:
				udm_obj = udm_modules.lookup('users/user', None, lo, scope='sub', base=ucr.get('ldap/base'), filter='uid=%s' % self.username)[0]
				self._user_dn = udm_obj.dn
			except IndexError:
				self._user_dn = False
		return self._user_dn

	def exists(self, lo):
		return self.get_user_dn(lo) is not False

	def exists_but_not_in_school(self, lo, school):
		user_dn = self.get_user_dn(lo)
		if user_dn:
			return ('ou=%s,' % school) not in user_dn
		return False

	def guess_username(self, lo):
		if self.username:
			return self.username
		firstname = ''
		if self.firstname:
			firstname = self.firstname.split()[0].lower() + '.'
		lastname = ''
		if self.lastname:
			lastname = self.lastname.split()[-1].lower()
		return firstname + lastname

	@classmethod
	def get_ldap_base(cls, search_base):
		return search_base.users

	@classmethod
	def find_column(self, column, i):
		for column_name, column_labels in self.column_labels.iteritems():
			if column in column_labels:
				return column_name
		return 'unused%d' % i

	@classmethod
	def get_columns_for_assign(cls):
		columns = [{'name' : 'unused', 'label' : _('Unused')}]
		columns.extend(cls.get_columns(cls.columns))
		return columns

	@classmethod
	def get_columns_for_spreadsheet(cls, column_names):
		columns = [{'name' : 'action', 'label' : _('Action')}]
		columns.extend(cls.get_columns(column_names))
		columns.append({'name' : 'line', 'label' : _('Line')})
		return columns

	@classmethod
	def get_columns(cls, column_names):
		columns = []
		for column in column_names:
			if column in cls.column_labels:
				columns.append({'name' : column, 'label' : cls.column_labels[column][0]})
		return columns

	def validate(self, lo, school):
		self.errors.clear()
		self.warnings.clear()
		if self.exists_but_not_in_school(lo, school):
			self.add_error('username', _('The username is already used somewhere outside the school. It may not be taken twice and has to be changed.'))

	def add_warning(self, attribute, warning_message):
		warnings = self.warnings.setdefault(attribute, [])
		if warning_message not in warnings:
			warnings.append(warning_message)

	def add_error(self, attribute, error_message):
		errors = self.errors.setdefault(attribute, [])
		if error_message not in errors:
			errors.append(error_message)

	def commit(self):
		self._error_msg = None
		if self.errors:
			for error in self.errors:
				self._error_msg = error[0]
			return False
		return True

	def get_error_msg(self):
		if self._error_msg is None:
			return None
		markup_username = '<strong>%s</strong>' % self.username
		if self.action == 'create':
			first_sentence = _('%s could not be created.') % markup_username
		elif self.action == 'delete':
			first_sentence = _('%s could not be deleted.') % markup_username
		else:
			first_sentence = _('%s could not be changed.') % markup_username
		return first_sentence + ' ' + self._error_msg

	def to_dict(self):
		attrs = dict([column, getattr(self, column) or ''] for column in self.columns)
		attrs['errors'] = self.errors
		attrs['warnings'] = self.warnings
		return attrs

class Student(User):
	columns = ['action', 'username', 'firstname', 'lastname', 'birthday', 'class', 'email', 'line']
	column_labels = {
		'username' : (_('Username'), 'Username'),
		'firstname' : (_('First name'), 'First name'),
		'lastname' : (_('Last name'), 'Last name'),
		'birthday' : (_('Birthday'), 'Birthday'),
		'class' : (_('Class'), 'Class'),
		'email' : (_('Email'), 'Email'),
		# no line!
		# no action!
	}

	def validate(self, lo, school):
		super(Student, self).validate(lo, school)
		if self.__dict__['class'] == '3b':
			self.add_warning('class', 'The class "3b" does not exist... (fake warning)')

	@classmethod
	def from_udm_obj(cls, user_obj, lo, **kwargs):
		attrs = {
			'username' : user_obj['username'],
			'firstname' : user_obj['firstname'],
			'lastname' : user_obj['lastname'],
			'birthday' : user_obj['birthday'],
			'email' : user_obj['mailPrimaryAddress'],
		}
		attrs.update(kwargs)
		return cls(lo, attrs)

	@classmethod
	def get_ldap_base(cls, search_base):
		return search_base.students

class Instance(SchoolBaseModule):
	def init(self):
		super(Instance, self).init()
		self.file_map = {}

	@file_upload
	def save_csv(self, request):
		result = {}
		file_id = str(uuid.uuid4())
		school = request.body['school']
		user_type = request.body['type']
		user_klass = User
		if user_type == 'student':
			user_klass = Student
		filename = request.options[0]['tmpfile']
		MODULE.process('Processing %s' % filename)
		sniffer = csv.Sniffer()
		with open(filename, 'rb') as f:
			lines = f.readlines()
			content = '\n'.join(lines)
		try:
			if lines:
				MODULE.process('First line is:\n%s' % lines[0].strip())
			dialect = sniffer.sniff(content)
			dialect.strict = True
			has_header = False
			if sniffer.has_header(content):
				MODULE.process('Seems to be a header...')
				has_header = True
			reader = csv.reader(lines, dialect)
			columns = []
			first_lines = []
			for line in reader:
				if not columns:
					if has_header:
						columns = line
						continue
					else:
						columns = ['unused%d' % x for x in range(len(line))]
				if len(first_lines) < 10:
					first_lines.append(line)
				# go through all lines to validate csv format
			columns = [user_klass.find_column(column, i) for i, column in enumerate(columns)]
			MODULE.process('First line translates to columns: %r' % columns)
		except csv.Error as exc:
			MODULE.warn('Malformatted CSV file? %s' % exc)
			result['success'] = False
			# result['message'] = ''
			self.finished(request.id, [result])
		else:
			self.file_map[file_id] = FileInfo(filename, school, user_klass, dialect, has_header)
			result['success'] = True
			result['filename'] = filename
			result['file_id'] = file_id
			result['available_columns'] = user_klass.get_columns_for_assign()
			result['given_columns'] = columns
			result['first_lines'] = first_lines
			self.finished(request.id, [result])

	@simple_response
	def show(self, file_id, columns):
		result = {}
		file_info = self.file_map[file_id]
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		search_base = SchoolSearchBase([], file_info.school)
		existing_users = udm_modules.lookup('users/user', None, lo, scope='sub', base=file_info.user_klass.get_ldap_base(search_base))
		with open(file_info.filename, 'rb') as f:
			lines = f.readlines()
			if file_info.has_header:
				lines = lines[1:]
		reader = csv.DictReader(lines, columns, dialect=file_info.dialect)
		users = []
		line_no = 1
		if file_info.has_header:
			line_no = 2
		for line in reader:
			attrs = {'line' : line_no}
			attrs.update(line)
			user = file_info.user_klass(lo, attrs)
			user.validate(lo, file_info.school)
			users.append(user.to_dict())
			line_no += 1
		mentioned_usernames = map(lambda u: u['username'], users)
		for user in existing_users:
			if user['username'] not in mentioned_usernames:
				user = file_info.user_klass.from_udm_obj(user, lo, action='delete')
				users.append(user.to_dict())
		result['users'] = users
		date_pattern = '{fullYear}-{month}-{day}'
		if locale.getlocale()[0] == 'de':
			date_pattern = '{day}.{month}.{fullYear}'
		python_date_format = None
		if 'birthday' in columns:
			for user in users:
				birthday = user['birthday']
				if birthday:
					if python_date_format is None:
						if re.match(r'^\d{2}.\d{2}.\d{2}$', birthday):
							python_date_format = '%d.%m.%y'
							date_pattern = 'dd.MM.yy'
						elif re.match(r'^\d{2}.\d{2}.\d{4}$', birthday):
							python_date_format = '%d.%m.%Y'
							date_pattern = 'dd.MM.yyyy'
						elif re.match(r'^\d{2}-\d{2}-\d{2}$', birthday):
							python_date_format = '%y.%m.%d'
							date_pattern = 'yy-MM-dd'
						elif re.match(r'^\d{4}-\d{2}-\d{2}$', birthday):
							python_date_format = '%Y.%m.%d'
							date_pattern = 'yyyy-MM-dd'
					else:
						try:
							user['birthday'] = datetime.strptime(birthday, '%Y-%m-%d').strftime(python_date_format)
						except (TypeError, ValueError):
							pass
		if 'username' not in columns:
			columns.insert(0, 'username')
		result['date_pattern'] = date_pattern
		result['columns'] = file_info.user_klass.get_columns_for_spreadsheet(columns)
		return result

	@simple_response
	def recheck_users(self, file_id, user_attrs):
		file_info = self.file_map[file_id]
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		users = []
		for attrs in user_attrs:
			user = file_info.user_klass(lo, attrs)
			user.validate(lo, file_info.school)
			users.append(user.to_dict())
		return users

	@simple_response
	def import_users(self, file_id, user_attrs):
		file_info = self.file_map[file_id]
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		errors = []
		for attrs in user_attrs:
			user = file_info.user_klass(lo, attrs)
			user.validate(lo, file_info.school)
			if not user.commit():
				errors.append(user.get_error_msg())
		os.unlink(file_info.filename)
		del self.file_map[file_id]
		return errors

	@simple_response
	def ping(self):
		return True

	def destroy(self):
		for file_info in self.file_map.itervalues():
			filename = file_info.filename
			if os.path.exists(filename):
				os.unlink(filename)
		return super(Instance, self).destroy()

