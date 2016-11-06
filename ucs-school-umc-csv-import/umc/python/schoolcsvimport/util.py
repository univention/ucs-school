#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  UCS@school CSV Upload (helper)
#
# Copyright 2014-2016 Univention GmbH
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

import re
import csv
from datetime import datetime, date
from ldap.filter import escape_filter_chars
import traceback

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.admin.filter import conjunction, expression

from ucsschool.lib.models import User, Student, Teacher, Staff, TeachersAndStaff, Attribute

_ = Translation('ucs-school-umc-csv-import').translate

def unformat_date(value, date_format):
	try:
		date_obj = datetime.strptime(value, date_format)
		if '%y' in date_format:
			# date format has only 2 year digits
			# so 01.01.40 -> 2040-01-01 which is not wanted
			if date_obj > datetime.now():
				date_obj = date(date_obj.year - 100, date_obj.month, date_obj.day)
		return date_obj.strftime('%Y-%m-%d')
	except (TypeError, ValueError):
		return value

def format_date(value, date_format):
	try:
		return datetime.strptime(value, '%Y-%m-%d').strftime(date_format)
	except (TypeError, ValueError):
		return value

class Birthday(Attribute):
	udm_name = 'birthday'
	# no syntax = iso8601Date, error message is misleading (some iso standard, not our python_format)

class CSVUser(User):

	RE_UID_INVALID = re.compile(r'[^\w \-\.]', re.UNICODE)

	def __init__(self, **kwargs):
		self._error_msg = None
		self.action = None
		super(CSVUser, self).__init__(**kwargs)

	def guess_username(self, lo, date_format):
		# already provided. use this one
		if self.name:
			return self.name

		# search database
		hints = []
		if self.lastname:
			hints.append(expression('lastname', escape_filter_chars(self.lastname)))
			if self.firstname:
				hints.append(expression('firstname', escape_filter_chars(self.firstname)))
			if self.birthday:
				hints.append(expression('birthday', escape_filter_chars(unformat_date(self.birthday, date_format))))
		if hints:
			ldap_filter = conjunction('&', hints)
			udm_obj = self.get_first_udm_obj(lo, str(ldap_filter))
			if udm_obj:
				return udm_obj['username']

		# generate a reasonable one
		firstname = u''
		if self.firstname:
			firstname = u'%s' % (self.firstname.split()[0].lower(),)
		lastname = u''
		if self.lastname:
			lastname = u'%s' % (self.lastname.split()[-1].lower())

		firstname = self.RE_UID_INVALID.sub('', firstname)
		lastname = self.RE_UID_INVALID.sub('', lastname)

		replace_invalid_chars = lambda u: re.sub(r'^(?:[^\w]+)?(.*?)(?:[^\w]+)?$', r'\1', u, re.UNICODE)

		if ucr.is_true('ucsschool/csvimport/username/generation/firstname_lastname', False):
			username = firstname + (u'.' if firstname else u'') + lastname
			return replace_invalid_chars(username)

		if firstname:
			firstname = firstname[:5] + '.'

		username = firstname + lastname[:5]
		maxlength = 20 - len(ucr.get('ucsschool/ldap/default/userprefix/exam', 'exam-'))
		return replace_invalid_chars(username[:maxlength])

	@classmethod
	def from_csv_line(cls, attrs, school, date_format, line_no, lo):
		attrs = dict((key, value) for key, value in attrs.iteritems() if isinstance(key, basestring))
		school_classes = attrs.pop('school_classes', None)
		user = cls(**attrs)
		user.name = user.guess_username(lo, date_format)
		user.school = school
		if not user.schools:
			user.schools = [school]
		if user.birthday:
			try:
				user.birthday = unformat_date(user.birthday, date_format)
			except (TypeError, ValueError):
				pass
		cls.set_school_classes(user, school_classes)

		user.action = 'modify' if user.exists(lo) else 'create'
		user.line = line_no
		return user

	@classmethod
	def set_school_classes(cls, user, school_classes):
		if school_classes:
			user.school_classes = {user.school: school_classes.split(',')}

	@classmethod
	def from_frontend_attrs(cls, attrs, school, date_format):
		attrs['school'] = school
		if 'birthday' in attrs:
			attrs['birthday'] = unformat_date(attrs['birthday'], date_format)
		user = cls(**attrs)
		user.action = attrs['action']
		user.line = attrs.get('line')
		return user

	@classmethod
	def is_header(cls, line, dialect):
		real_column = 0
		if line:
			reader = csv.reader([line], dialect)
			columns = reader.next()
			for column in columns:
				found_column = cls.find_field_name_from_label(column, 0)
				if not found_column.startswith('unused'):
					real_column += 1
		# at least 2: Prevent false positives because of someone
		# called Mr. Surname
		return real_column > 1

	@classmethod
	def find_all_fields(cls):
		return ['name', 'firstname', 'lastname', 'birthday', 'email', 'school_classes', 'password']

	@classmethod
	def find_field_name_from_label(cls, label, i):
		for name in cls.find_all_fields():
			attr = cls._attributes[name]
			if attr.label == label or label in attr.aka:
				return name
		return 'unused%d' % i

	@classmethod
	def get_required_columns(cls):
		return [key for key, attr in cls._attributes.iteritems() if attr.required]

	@classmethod
	def get_columns_for_assign(cls):
		columns = [{'name': 'unused', 'label': _('Unused')}]
		columns.extend(cls.get_columns_for_frontend(cls.find_all_fields()))
		return columns

	@classmethod
	def get_columns_for_spreadsheet(cls, column_names):
		columns = [{'name': 'action', 'label': _('Action')}]
		columns.extend(cls.get_columns_for_frontend(column_names))
		columns.append({'name': 'line', 'label': _('Line')})
		return columns

	@classmethod
	def get_columns_for_frontend(cls, column_names):
		columns = []
		for field in column_names:
			label = cls.find_field_label_from_name(field)
			if label:
				columns.append({'name': field, 'label': label})
		return columns

	def to_dict(self, format_birthday):
		attrs = super(CSVUser, self).to_dict()
		if format_birthday:
			# force format of date as requested, not as seen in LDAP
			try:
				if attrs['birthday']:
					attrs['birthday'] = attrs['birthday'].replace(' ', '')
				attrs['birthday'] = format_date(attrs['birthday'], format_birthday)
			except (TypeError, ValueError):
				pass
		attrs['errors'] = self.errors
		attrs['warnings'] = self.warnings
		attrs['line'] = self.line
		attrs['action'] = self.action
		return attrs

	def commit(self, lo):
		if self.action != 'delete':
			self.validate(lo)
		self._error_msg = None
		if self.errors:
			for field, errors in self.errors.iteritems():
				self._error_msg = errors[0]
			return False
		try:
			if self.action == 'create':
				self.create(lo, validate=False)
			elif self.action == 'modify':
				self.modify(lo, validate=False, move_if_necessary=False)
			elif self.action == 'delete':
				self.remove(lo)
		except Exception as exc:
			MODULE.warn('Something went wrong. %s' % traceback.format_exc())
			self._error_msg = str(exc)
			return False
		else:
			return True

	def validate(self, lo, validate_unlikely_changes=True):
		super(CSVUser, self).validate(lo, validate_unlikely_changes)
		if self.exists(lo):
			if self.action == 'create':
				self.add_error('action', _('The user already exists and cannot be created. Please change the username to one that does not yet exist or change the action to be taken.'))
		else:
			if self.action == 'modify':
				self.add_error('action', _('The user does not yet exist and cannot be modified. Please change the username to one that exists or change the action to be taken.'))
			elif self.action == 'delete':
				self.add_error('action', _('The user does not yet exist and cannot be deleted. Please change the username to one that exists or change the action to be taken.'))

	def get_error_msg(self):
		if self._error_msg is None:
			return None
		markup_username = '<strong>%s</strong>' % self.name
		if self.action == 'create':
			first_sentence = _('%s could not be created.') % markup_username
		elif self.action == 'delete':
			first_sentence = _('%s could not be deleted.') % markup_username
		else:
			first_sentence = _('%s could not be changed.') % markup_username
		return first_sentence + ' ' + self._error_msg

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		model = super(CSVUser, cls).get_class_for_udm_obj(udm_obj, school)
		if model is Student:
			return CSVStudent
		if model is Teacher:
			return CSVTeacher
		if model is TeachersAndStaff:
			return CSVTeachersAndStaff
		if model is Staff:
			return CSVStaff
		MODULE.warn('No mapping for %r, using %r' % (model.__name__, cls.__name__))
		return cls

# same as normal but without syntax validation (done by our validate function)
# has to be specified in each class, otherwise the base class Student would overwrite
# it from base class CSVUser
birthday_attr = Birthday(_('Birthday'), aka=['Birthday', 'Geburtstag'], unlikely_to_change=True)

class CSVStudent(CSVUser, Student):
	birthday = birthday_attr

class CSVTeacher(CSVUser, Teacher):
	birthday = birthday_attr

class CSVStaff(CSVUser, Staff):
	birthday = birthday_attr

	@classmethod
	def set_school_classes(cls, user, school_classes):
		return

	@classmethod
	def find_all_fields(cls):
		fields = super(CSVStaff, cls).find_all_fields()
		fields.remove('school_classes')
		return fields

class CSVTeachersAndStaff(CSVUser, TeachersAndStaff):
	birthday = birthday_attr

########################################################################
#### LICENSE CHECK - copied from ad-takeover ###########################

import univention.admin.uexceptions as uexceptions
from univention.admincli import license_check
import univention.admin.uldap

class LicenseInsufficient(Exception):
	pass

class UCS_License_detection(object):

	def __init__(self, ucr):
		self.ucr = ucr

		self.GPLversion = False
		try:
			import univention.admin.license
			self.License = univention.admin.license.License
			self._license = univention.admin.license._license
			self.ignored_users_list = self._license.sysAccountNames
		except ImportError:  # GPLversion
			self.GPLversion = True
			self.ignored_users_list = []

	def determine_license(self, lo, dn):
		def mylen(xs):
			if xs is None:
				return 0
			return len(xs)
		v = self._license.version
		types = self._license.licenses[v]
		if dn is None:
			max = [self._license.licenses[v][type]
				for type in types]
		else:
			max = [lo.get(dn)[self._license.keys[v][type]][0]
				for type in types]

		objs = [lo.searchDn(filter=self._license.filters[v][type])
			for type in types]
		num = [mylen(obj)
			for obj in objs]
		self._license.checkObjectCounts(max, num)
		result = []
		for i in types.keys():
			m = max[i]
			n = num[i]
			if i == self.License.USERS or i == self.License.ACCOUNT:
				n -= self._license.sysAccountsFound
				if n < 0: n = 0
			l = self._license.names[v][i]
			if m:
				if i == self.License.USERS or i == self.License.ACCOUNT:
					MODULE.info('determine_license for current UCS %s: %s of %s' % (l, n, m))
					MODULE.info('  %s Systemaccounts are ignored.' % self._license.sysAccountsFound)
					result.append((l, n, m))
		return result

	def check_license(self, domain_info):

		if self.GPLversion:
			return True

		binddn = self.ucr['ldap/hostdn']
		with open('/etc/machine.secret', 'r') as pwfile:
			bindpw = pwfile.readline().strip()

		try:
			lo = univention.admin.uldap.access(host=self.ucr['ldap/master'],
							port=int(self.ucr.get('ldap/master/port', '7389')),
							base=self.ucr['ldap/base'],
							binddn=binddn,
							bindpw=bindpw)
		except uexceptions.authFail:
			raise LicenseInsufficient(_('Internal Error: License check failed.'))

		try:
			self._license.init_select(lo, 'admin')
			check_array = self.determine_license(lo, None)
		except uexceptions.base:
			dns = license_check.find_licenses(lo, self.ucr['ldap/base'], 'admin')
			dn, expired = license_check.choose_license(lo, dns)
			check_array = self.determine_license(lo, dn)

		## some name translation
		object_displayname_for_licensetype = {'Accounts': _('users'), 'Users': _('users')}
		import_object_count_for_licensetype = {'Accounts': domain_info['users'], 'Users': domain_info['users']}

		license_sufficient = True
		error_msg = None
		for object_type, num, max_objs in check_array:
			object_displayname = object_displayname_for_licensetype.get(object_type, object_type)
			MODULE.info('Found %s %s objects on the remote server.' % (import_object_count_for_licensetype[object_type], object_displayname))
			sum_objs = num + import_object_count_for_licensetype[object_type]
			domain_info['licensed_%s' % (object_displayname,)] = max_objs
			domain_info['estimated_%s' % (object_displayname,)] = sum_objs
			if self._license.compare(sum_objs, max_objs) > 0:
				license_sufficient = False
				error_msg = _('Number of %(object_name)s after the import would be %(sum)s. This would exceed the number of licensed objects (%(max)s).') % {
							'object_name': object_displayname,
							'sum': sum_objs,
							'max': max_objs,
						}
				MODULE.warn(error_msg)

		if not license_sufficient:
			raise LicenseInsufficient(error_msg)

