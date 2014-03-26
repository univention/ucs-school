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
import random
import csv
from datetime import datetime
import re
import locale
import traceback
import ldap.filter

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import file_upload, simple_response, multi_response
from univention.management.console.modules.mixins import ProgressMixin
from univention.config_registry import ConfigRegistry
import univention.admin.modules as udm_modules
import univention.admin.uldap as udm_uldap
from univention.admin.filter import conjunction, expression
from univention.admin.uexceptions import noObject

from ucsschool.lib.schoolldap import SchoolBaseModule, SchoolSearchBase, open_ldap_connection

_ = Translation('ucs-school-umc-csv-import').translate

ucr = ConfigRegistry()
ucr.load()

def generate_password():
	length = 8
	charlist = 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!"$%&/()=?'
	passwd = ''
	for i in range(length):
		passwd += charlist[random.randrange(0, len(charlist))]
	return passwd

class FileInfo(object):
	def __init__(self, filename, school, user_klass, dialect, has_header, delete_not_mentioned, date_format=None, columns=None):
		self.filename = filename
		self.school = school
		self.user_klass = user_klass
		self.dialect = dialect
		self.has_header = has_header
		self.delete_not_mentioned = delete_not_mentioned
		self.date_format = date_format
		self.columns = columns

class User(object):
	columns = ['action', 'username', 'firstname', 'lastname', 'birthday', 'email', 'line']
	column_labels = {
		'username' : (_('Username'), 'Username'),
		'firstname' : (_('First name'), 'First name'),
		'lastname' : (_('Last name'), 'Last name'),
		'birthday' : (_('Birthday'), 'Birthday'),
		'email' : (_('Email'), 'Email'),
		# no line!
		# no action!
	}
	required_columns = ['action', 'username', 'firstname', 'lastname']
	should_not_change_columns = ['firstname', 'lastname', 'birthday', 'email']

	additional_columns = [] # may be overwritten
	additional_column_labels = {} # may be overwritten
	additional_required_columns = [] # may be overwritten
	additional_should_not_change_columns = [] # may be overwritten

	supports_school_classes = False

	def __init__(self, lo, school, date_format, attrs):
		self._udm_obj_searched = False
		self._udm_obj = None
		self._error_msg = None
		if school:
			school = ldap.filter.escape_filter_chars(school)
		self.school = school
		self._search_base = SchoolSearchBase([], self.school)
		self.date_format = date_format
		for column in self.get_columns():
			value = attrs.get(column)
			if column in ['birthday']:
				value = self.format_date(value)
			if isinstance(value, basestring):
				value = ldap.filter.escape_filter_chars(value)
			setattr(self, column, value)
		self.username = self.guess_username(lo)
		if 'action' not in attrs:
			if self.exists(lo):
				self.action = 'modify'
			else:
				self.action = 'create'
		self.errors = {}
		self.warnings = {}

	def unformat_date(self, value):
		try:
			return datetime.strptime(value, self.date_format).strftime('%Y-%m-%d')
		except (TypeError, ValueError):
			return value

	def format_date(self, value):
		try:
			return datetime.strptime(value, '%Y-%m-%d').strftime(self.date_format)
		except (TypeError, ValueError):
			return value

	def exists(self, lo):
		return self.get_udm_object(lo) is not None

	def exists_but_not_in_school(self, lo):
		if self.exists(lo):
			return ('ou=%s,' % self.school) not in self.get_udm_object(lo).dn
		return False

	def guess_username(self, lo):
		# already provided. use this one
		if self.username:
			return self.username

		# search database
		hints = []
		if self.lastname:
			hints.append(expression('lastname', self.lastname))
			if self.firstname:
				hints.append(expression('firstname', self.firstname))
			if self.birthday:
				hints.append(expression('birthday', self.unformat_date(self.birthday)))
		if hints:
			ldap_filter = conjunction('&', hints)
			try:
				udm_obj = udm_modules.lookup('users/user', None, lo, scope='sub', base=ucr.get('ldap/base'), filter=str(ldap_filter))[0]
			except IndexError:
				pass
			else:
				return udm_obj['username']

		# generate a reasonable one
		firstname = ''
		if self.firstname:
			firstname = self.firstname.split()[0].lower() + '.'
		lastname = ''
		if self.lastname:
			lastname = self.lastname.split()[-1].lower()
		return firstname + lastname

	def get_dn(self, lo):
		udm_obj = self.get_udm_object(lo)
		if udm_obj:
			return udm_obj.dn

	def merge_additional_group_changes(self, lo, changes, group_cache, all_found_classes, without_school_classes=False):
		if self.action not in ['create', 'modify']:
			return
		dn = self.get_dn(lo)
		all_groups = self.groups_for_ucs_school(lo, group_cache, all_found_classes, without_school_classes=without_school_classes)
		my_groups = self.groups_used(lo, group_cache)
		for group in all_groups:
			if group in my_groups:
				continue
			group_change = changes.setdefault(group, {'add' : [], 'remove' : []})
			group_change['remove'].append(dn)
		for group in my_groups:
			group_change = changes.setdefault(group, {'add' : [], 'remove' : []})
			group_change['add'].append(dn)

	def get_specific_groups(self):
		return []

	@classmethod
	def bulk_group_change(cls, lo, group_changes, group_cache):
		for group_dn, group_changes in group_changes.iteritems():
			group_obj = cls.get_or_create_group(group_dn, lo, group_cache)
			group_obj.open()
			group_users = group_obj['users'][:]
			for remove in group_changes['remove']:
				if remove in group_users:
					group_users.remove(remove)
			for add in group_changes['add']:
				if add not in group_users:
					group_users.append(add)
			group_obj['users'] = group_users
			group_obj.modify()

	@classmethod
	def get_user_base_from_search_base(cls, search_base):
		return search_base.users

	@classmethod
	def is_header(cls, line, dialect):
		real_column = 0
		if line:
			reader = csv.reader([line], dialect)
			columns = reader.next()
			for column in columns:
				found_column = cls.find_column(column, 0)
				if not found_column.startswith('unused'):
					real_column += 1
		# at least 2: Prevent false positives because of someone
		# called Mr. Line
		return real_column > 1

	@classmethod
	def get_columns(cls):
		columns = []
		columns.extend(cls.columns)
		columns.extend(cls.additional_columns)
		return columns

	@classmethod
	def get_column_labels(cls):
		column_labels = {}
		column_labels.update(cls.column_labels)
		column_labels.update(cls.additional_column_labels)
		return column_labels

	@classmethod
	def get_required_columns(cls):
		required_columns = []
		required_columns.extend(cls.required_columns)
		required_columns.extend(cls.additional_required_columns)
		return required_columns

	@classmethod
	def get_should_not_change_columns(cls):
		should_not_change_columns = []
		should_not_change_columns.extend(cls.should_not_change_columns)
		should_not_change_columns.extend(cls.additional_should_not_change_columns)
		return should_not_change_columns

	@classmethod
	def find_column(self, column, i):
		for column_name, column_labels in self.get_column_labels().iteritems():
			if column in column_labels:
				return column_name
		return 'unused%d' % i

	@classmethod
	def get_columns_for_assign(cls):
		columns = [{'name' : 'unused', 'label' : _('Unused')}]
		columns.extend(cls.get_columns_for_frontend(cls.get_columns()))
		return columns

	@classmethod
	def get_columns_for_spreadsheet(cls, column_names):
		columns = [{'name' : 'action', 'label' : _('Action')}]
		columns.extend(cls.get_columns_for_frontend(column_names))
		columns.append({'name' : 'line', 'label' : _('Line')})
		return columns

	@classmethod
	def get_columns_for_frontend(cls, column_names):
		columns = []
		for column in column_names:
			if column in cls.get_column_labels():
				columns.append({'name' : column, 'label' : cls.get_column_label(column)})
		return columns

	@classmethod
	def get_column_label(cls, column):
		try:
			return cls.get_column_labels()[column][0]
		except (KeyError, IndexError):
			return column

	def validate(self, lo):
		self.errors.clear()
		self.warnings.clear()
		for column in self.get_required_columns():
			if getattr(self, column) is None:
				self.add_error(column, _('"%s" is required. Please provide this information.') % self.get_column_label(column))
		if self.exists(lo):
			if self.action == 'create':
				self.add_error('action', _('The user already exists and cannot be created. Please change the username to one that does not yet exist or change the action to be taken.'))
			if self.exists_but_not_in_school(lo):
				self.add_error('username', _('The username is already used somewhere outside the school. It may not be taken twice and has to be changed.'))
			elif self.action == 'modify':
				# do not do this if the user exists somewhere
				udm_obj = self.get_udm_object(lo)
				from_udm_obj = self.from_udm_obj(udm_obj, lo, self.school, self.date_format)
				for column in self.get_should_not_change_columns():
					new_value = getattr(self, column)
					old_value = getattr(from_udm_obj, column)
					if old_value:
						if new_value != old_value:
							self.add_warning(column, _('The value changed from %(old)s. This seems unlikely.') % {'old' : old_value})
		else:
			if self.action == 'modify':
				self.add_error('action', _('The user does not yet exist and cannot be modified. Please change the username to one that exists or change the action to be taken.'))
			if self.action == 'delete':
				self.add_error('action', _('The user does not yet exist and cannot be deleted. Please change the username to one that exists or change the action to be taken.'))

	def add_warning(self, attribute, warning_message):
		warnings = self.warnings.setdefault(attribute, [])
		if warning_message not in warnings:
			warnings.append(warning_message)

	def add_error(self, attribute, error_message):
		errors = self.errors.setdefault(attribute, [])
		if error_message not in errors:
			errors.append(error_message)

	def commit(self, lo, group_cache):
		self.validate(lo)
		self._error_msg = None
		if self.errors:
			for field, errors in self.errors.iteritems():
				self._error_msg = errors[0]
			return False
		try:
			if self.action == 'create':
				self.commit_create(lo, group_cache)
			elif self.action == 'modify':
				self.commit_modify(lo, group_cache)
			elif self.action == 'delete':
				self.commit_delete(lo)
		except Exception as exc:
			MODULE.warn('Something went wrong. %s' % traceback.format_exc())
			self._error_msg = str(exc)
			return False
		else:
			return True

	def get_user_base(self):
		return self.get_user_base_from_search_base(self._search_base)

	def get_group_base(self):
		return self._search_base.groups

	def primary_group(self, lo, group_cache):
		dn = 'cn=Domain Users %s,%s' % (self.school, self.get_group_base())
		return self.get_or_create_group(dn, lo, group_cache).dn

	def commit_create(self, lo, group_cache):
		pos = udm_uldap.position(ucr.get('ldap/base'))
		pos.setDn(self.get_user_base())
		udm_obj = udm_modules.get('users/user').object(None, lo, pos)
		udm_obj.open()
		udm_obj['username'] = self.username
		udm_obj['password'] = generate_password()
		udm_obj['primaryGroup'] = self.primary_group(lo, group_cache)
		self._alter_udm_obj(udm_obj, lo, group_cache)
		udm_obj.create()
		return udm_obj

	def commit_modify(self, lo, group_cache):
		udm_obj = self.get_udm_object(lo)
		udm_obj.open()
		self._alter_udm_obj(udm_obj, lo, group_cache)
		udm_obj.modify()
		rdn = lo.explodeDn(udm_obj.dn)[0]
		dest = '%s,%s' % (rdn, self.get_user_base())
		if dest != udm_obj.dn:
			udm_obj.move(dest)
		return udm_obj

	def _alter_udm_obj(self, udm_obj, lo, group_cache):
		udm_obj['firstname'] = self.firstname
		udm_obj['lastname'] = self.lastname
		birthday = self.birthday
		if birthday:
			birthday = self.unformat_date(birthday)
			udm_obj['birthday'] = birthday
		if self.email:
			udm_obj['mailPrimaryAddress'] = self.email
		# not done here. instead in bulk_group_change() for performance reasons
		# and to avoid problems with overwriting unrelated groups
		# udm_obj['groups'] = ...

	def commit_delete(self, lo):
		udm_obj = self.get_udm_object(lo)
		if udm_obj:
			udm_obj.remove()
		return udm_obj

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

	def get_udm_object(self, lo):
		if self.username is None:
			return None
		if self._udm_obj_searched is False:
			try:
				self._udm_obj = udm_modules.lookup('users/user', None, lo, scope='sub', base=ucr.get('ldap/base'), filter='uid=%s' % self.username)[0]
			except IndexError:
				return None
			self._udm_obj_searched = True
		return self._udm_obj

	def to_dict(self):
		attrs = dict([column, getattr(self, column) or ''] for column in self.get_columns())
		attrs['errors'] = self.errors
		attrs['warnings'] = self.warnings
		return attrs

	def groups_for_ucs_school(self, lo, group_cache, all_found_classes, without_school_classes=False):
		group_dns = []
		group_dns.append('cn=Domain Users %s,%s' % (self.school, self.get_group_base()))
		group_dns.append('cn=schueler-%s,%s' % (self.school, self.get_group_base()))
		group_dns.append('cn=lehrer-%s,%s' % (self.school, self.get_group_base()))
		group_dns.append('cn=mitarbeiter-%s,%s' % (self.school, self.get_group_base()))

		if not without_school_classes:
			for school_class_group in all_found_classes:
				group_dns.append(school_class_group.dn)

		for group_dn in group_dns:
			self.get_or_create_group(group_dn, lo, group_cache)

		return group_dns

	def groups_used(self, lo, group_cache):
		group_dns = []
		group_dns.append('cn=Domain Users %s,%s' % (self.school, self.get_group_base()))
		group_dns.extend(self.get_specific_groups())

		for group_dn in group_dns:
			self.get_or_create_group(group_dn, lo, group_cache)

		return group_dns

	@classmethod
	def from_udm_obj(cls, user_obj, lo, school, date_format, columns=None, **kwargs):
		attrs = {
			'username' : user_obj['username'],
			'firstname' : user_obj['firstname'],
			'lastname' : user_obj['lastname'],
			'birthday' : user_obj['birthday'],
			'email' : user_obj['mailPrimaryAddress'],
		}
		if columns:
			attrs = dict((key, value) for key, value in attrs.iteritems() if key in columns)
		attrs.update(kwargs)
		return cls(lo, school, date_format, attrs)

	@classmethod
	def get_or_create_group(cls, group_dn, lo, group_cache):
		if group_cache is None:
			group_cache = {}
		if group_dn not in group_cache:
			MODULE.info('getting group %s' % group_dn)
			if lo is not None:
				try:
					group_obj = udm_modules.lookup('groups/group', None, lo, scope='base', base=group_dn)[0]
				except (IndexError, noObject):
					MODULE.process('Group "%s" not found. Creating...' % group_dn)
					group_parts = lo.explodeDn(group_dn)
					group_name = lo.explodeDn(group_parts[0], 1)[0]
					group_container = ','.join(group_parts[1:])
					pos = udm_uldap.position(ucr.get('ldap/base'))
					pos.setDn(group_container)
					group_obj = udm_modules.get('groups/group').object(None, lo, pos)
					group_obj.open()
					group_obj['name'] = group_name
					group_obj.create()
				group_cache[group_dn] = group_obj
		return group_cache[group_dn]

	def get_or_create_school_class_group(self, school_class, lo, group_cache):
		group_dn = 'cn=%s-%s,cn=klassen,cn=schueler,%s' % (self.school, school_class, self.get_group_base())
		return self.get_or_create_group(group_dn, lo, group_cache)

class Student(User):
	additional_columns = ['school_class']
	additional_column_labels = {
		'school_class' : (_('Class'), 'Class'),
	}
	supports_school_classes = True

	@classmethod
	def from_udm_obj(cls, user_obj, lo, school, date_format, columns=None, **kwargs):
		school_class = None
		if columns is None or 'school_class' in columns:
			user_obj.open()
			for group in user_obj['groups']:
				try:
					school_class_name, c1, c2 = lo.explodeDn(group, 1)[:3]
					if c1 == 'klassen' and c2 == 'schueler':
						school_class = school_class_name.split('-')[-1]
						break
				except ValueError:
					pass
			kwargs['school_class'] = school_class
		return super(Student, cls).from_udm_obj(user_obj, lo, school, date_format, columns, **kwargs)

	@classmethod
	def get_user_base_from_search_base(cls, search_base):
		return search_base.students

	def get_specific_groups(self):
		groups = []
		groups.append('cn=schueler-%s,%s' % (self.school, self.get_group_base()))
		if self.school_class:
			groups.append('cn=%s-%s,cn=klassen,cn=schueler,%s' % (self.school, self.school_class, self.get_group_base()))
		return groups

class Teacher(User):
	additional_columns = ['school_class']
	additional_column_labels = {
		'school_class' : (_('Class'), 'Class'),
	}
	supports_school_classes = True

	@classmethod
	def from_udm_obj(cls, user_obj, lo, school, date_format, columns=None, **kwargs):
		school_classes = []
		if columns is None or 'school_class' in columns:
			user_obj.open()
			for group in user_obj['groups']:
				try:
					school_class_name, c1, c2 = lo.explodeDn(group, 1)[:3]
					if c1 == 'klassen' and c2 == 'schueler':
						school_classes.append(school_class_name.split('-')[-1])
				except ValueError:
					pass
		kwargs['school_class'] = ','.join(school_classes)
		return super(Teacher, cls).from_udm_obj(user_obj, lo, school, date_format, columns, **kwargs)

	@classmethod
	def get_user_base_from_search_base(cls, search_base):
		return search_base.teachers

	def get_specific_groups(self):
		groups = []
		groups.append('cn=lehrer-%s,%s' % (self.school, self.get_group_base()))
		if self.school_class:
			for school_class in self.school_class.split(','):
				groups.append('cn=%s-%s,cn=klassen,cn=schueler,%s' % (self.school, self.school_class, self.get_group_base()))
		return groups

class Staff(User):
	@classmethod
	def get_user_base_from_search_base(cls, search_base):
		return search_base.staff

	def get_specific_groups(self):
		groups = []
		groups.append('cn=mitarbeiter-%s,%s' % (self.school, self.get_group_base()))
		return groups

class TeacherAndStaff(Teacher):
	@classmethod
	def get_user_base_from_search_base(cls, search_base):
		return search_base.teachersAndStaff

	def get_specific_groups(self):
		groups = super(TeacherAndStaff, self).get_specific_groups()
		groups.append('cn=mitarbeiter-%s,%s' % (self.school, self.get_group_base()))
		return groups

class Instance(SchoolBaseModule, ProgressMixin):
	def init(self):
		super(Instance, self).init()
		self.file_map = {}

	@file_upload
	def save_csv(self, request):
		result = {}
		file_id = generate_password()
		school = request.body['school']
		user_type = request.body['type']
		delete_not_mentioned = bool(request.body.get('delete_not_mentioned'))
		user_klass = User
		if user_type == 'student':
			user_klass = Student
		elif user_type == 'teacher':
			user_klass = Teacher
		elif user_type == 'staff':
			user_klass = Staff
		elif user_type == 'teachersAndStaff':
			user_klass = TeacherAndStaff
		filename = request.options[0]['tmpfile']
		MODULE.process('Processing %s' % filename)
		sniffer = csv.Sniffer()
		with open(filename, 'rb') as f:
			lines = f.readlines()
			content = '\n'.join(lines)
		try:
			first_line = ''
			if lines:
				first_line = lines[0].strip()
				MODULE.process('First line is:\n%s' % first_line)
			try:
				# be strict regarding delimiters. I have seen the
				# sniffer returning 'b' as the delimiter in some cases
				dialect = sniffer.sniff(content, delimiters=' ,;\t')
				dialect.strict = True
			except csv.Error:
				# Something went wrong. But the sniffer is not exact
				# try it again the hard way: delimiter=, quotechar="
				MODULE.warn('Error while sniffing csv dialect... fallback to excel')
				dialect = csv.get_dialect('excel')

			# Is the first line the header or already a user?
			# sniffer.has_header(content)
			# is not very acurate. We know how a header looks like...
			has_header = user_klass.is_header(first_line, dialect)
			if has_header:
				MODULE.process('Seems to be a header...')

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
			self.file_map[file_id] = FileInfo(filename, school, user_klass, dialect, has_header, delete_not_mentioned)
			result['success'] = True
			result['filename'] = filename
			result['file_id'] = file_id
			result['available_columns'] = user_klass.get_columns_for_assign()
			result['given_columns'] = columns
			result['first_lines'] = first_lines
			self.finished(request.id, [result])

	def _guess_date_format(self, date_pattern, python_date_format, value):
		if value and python_date_format is None:
			if re.match(r'^\d{2}.\d{2}.\d{2}$', value):
				python_date_format = '%d.%m.%y'
				date_pattern = 'dd.MM.yy'
			elif re.match(r'^\d{2}.\d{2}.\d{4}$', value):
				python_date_format = '%d.%m.%Y'
				date_pattern = 'dd.MM.yyyy'
			elif re.match(r'^\d{2}-\d{2}-\d{2}$', value):
				python_date_format = '%y.%m.%d'
				date_pattern = 'yy-MM-dd'
			elif re.match(r'^\d{4}-\d{2}-\d{2}$', value):
				python_date_format = '%Y.%m.%d'
				date_pattern = 'yyyy-MM-dd'
		return date_pattern, python_date_format

	@simple_response(with_progress=True)
	def show(self, progress, file_id, columns):
		result = {}
		progress.title = _('Checking users from CSV file')
		file_info = self.file_map[file_id]
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		search_base = SchoolSearchBase([], file_info.school)
		with open(file_info.filename, 'rb') as f:
			lines = f.readlines()
			if file_info.has_header:
				lines = lines[1:]
		reader = csv.DictReader(lines, columns, dialect=file_info.dialect)
		users = []
		date_pattern = 'yyyy.MMM.dd'
		if locale.getlocale()[0] == 'de':
			date_pattern = 'dd.MMM.yyyy'
		python_date_format = None
		line_no = 1
		if file_info.has_header:
			line_no = 2
		for line in reader:
			attrs = {'line' : line_no}
			attrs.update(line)
			if 'birthday' in columns:
				date_pattern, python_date_format = self._guess_date_format(date_pattern, python_date_format, line['birthday'])
			user = file_info.user_klass(lo, file_info.school, python_date_format, attrs)
			user.validate(lo)
			users.append(user.to_dict())
			line_no += 1
			progress.progress(message=user.username)
		if 'username' not in columns:
			# add username here:
			# 1. it has to be presented and will be populated by a guess
			# 2. do it before adding the to_be_deleted, as they need it
			# in the columns, otherwise their real username gets overwritten
			columns.insert(0, 'username')
		if file_info.delete_not_mentioned:
			mentioned_usernames = map(lambda u: u['username'], users)
			progress.title = _('Checking users from database')
			existing_udm_users = udm_modules.lookup('users/user', None, lo, scope='sub', base=file_info.user_klass.get_user_base_from_search_base(search_base))
			for user in existing_udm_users:
				if user['username'] not in mentioned_usernames:
					if 'birthday' in columns:
						date_pattern, python_date_format = self._guess_date_format(date_pattern, python_date_format, user['birthday'])
					user = file_info.user_klass.from_udm_obj(user, lo, file_info.school, python_date_format, columns, action='delete')
					users.append(user.to_dict())
					progress.progress(message=user.username)
		result['users'] = users
		file_info.date_format = python_date_format
		file_info.columns = columns
		result['date_pattern'] = date_pattern
		result['columns'] = file_info.user_klass.get_columns_for_spreadsheet(columns)
		result['required_columns'] = file_info.user_klass.get_required_columns()
		return result

	@simple_response
	def recheck_users(self, file_id, user_attrs):
		file_info = self.file_map[file_id]
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		users = []
		for attrs in user_attrs:
			user = file_info.user_klass(lo, file_info.school, file_info.date_format, attrs)
			user.validate(lo)
			users.append(user.to_dict())
		return users

	@multi_response(progress=[_('Processing %d user(s)'), _('%(username)s %(action)s')])
	def import_users(self, iterator, file_id, attrs):
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		file_info = None
		group_changes = {}
		group_cache = {}
		without_school_classes = True
		all_found_classes = []
		for file_id, attrs in iterator:
			if file_info is None:
				file_info = self.file_map[file_id]
				without_school_classes = 'school_class' not in file_info.columns and file_info.user_klass.supports_school_classes
				if not without_school_classes:
					group_base = SchoolSearchBase([], file_info.school).groups
					school_class_base = 'cn=klassen,cn=schueler,%s' % group_base
					all_found_classes = udm_modules.lookup('groups/group', None, lo, scope='sub', base=school_class_base, filter='*')
			user = file_info.user_klass(lo, file_info.school, file_info.date_format, attrs)
			MODULE.process('Going to %s %s %s' % (user.action, file_info.user_klass.__name__, user.username))
			action = user.action
			if action == 'create':
				action = _('created')
			elif action == 'modify':
				action = _('modified')
			if action == 'delete':
				action = _('deleted')
			if user.commit(lo, group_cache):
				yield {'username' : user.username, 'action' : action, 'success' : True}
			else:
				yield {'username' : user.username, 'action' : action, 'success' : False, 'msg' : user.get_error_msg()}
			user.merge_additional_group_changes(lo, group_changes, group_cache, all_found_classes, without_school_classes=without_school_classes)
		file_info.user_klass.bulk_group_change(lo, group_changes, group_cache)
		os.unlink(file_info.filename)
		del self.file_map[file_id]

	@simple_response
	def ping(self):
		return True

	def destroy(self):
		for file_info in self.file_map.itervalues():
			filename = file_info.filename
			if os.path.exists(filename):
				os.unlink(filename)
		return super(Instance, self).destroy()

