#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
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

from datetime import datetime, date
import traceback
import ldap.filter
import csv
import random
import string
import ldap

import univention.admin.uldap as udm_uldap
from univention.admin.filter import conjunction, expression
from univention.admin.uexceptions import noObject
from univention.config_registry import ConfigRegistry
import univention.admin.modules as udm_modules

from univention.management.console.log import MODULE
from univention.lib.i18n import Translation

from ucsschool.lib.schoolldap import SchoolSearchBase

_ = Translation('python-ucs-school').translate

udm_modules.update()

ucr = ConfigRegistry()
ucr.load()

def generate_random(length=30):
	chars = string.ascii_letters + string.digits
	return ''.join(random.choice(chars) for x in range(length))

class User(object):
	_search_base_cache = {}

	columns = ['action', 'username', 'firstname', 'lastname', 'birthday', 'email', 'password', 'line']
	column_labels = {
		'username' : (_('Username'), 'Username'),
		'firstname' : (_('First name'), 'First name'),
		'lastname' : (_('Last name'), 'Last name'),
		'birthday' : (_('Birthday'), 'Birthday'),
		'email' : (_('Email'), 'Email'),
		# no password!
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
			date_obj = datetime.strptime(value, self.date_format)
			if '%y' in self.date_format:
				# date format has only 2 year digits
				# so 01.01.40 -> 2040-01-01 which is not wanted
				if date_obj > datetime.now():
					date_obj = date(date_obj.year - 100, date_obj.month, date_obj.day)
			return date_obj.strftime('%Y-%m-%d')
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

	def merge_additional_group_changes(self, lo, changes, all_found_classes, without_school_classes=False):
		if self.action not in ['create', 'modify']:
			return
		udm_obj = self.get_udm_object(lo)
		if not udm_obj:
			MODULE.error('%s does not have an associated UDM object. This should not happen. Unable to set group memberships here!' % self.username)
			return
		udm_obj.open()
		dn = udm_obj.dn
		all_groups = self.groups_for_ucs_school(lo, all_found_classes, without_school_classes=without_school_classes)
		my_groups = self.groups_used(lo)
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
	def bulk_group_change(cls, lo, school, group_changes):
		for group_dn, group_changes in group_changes.iteritems():
			MODULE.process('Changing group memberships for %s' % group_dn)
			MODULE.info('Changes: %r' % group_changes)

			# do not use the group cache. get a fresh instance from database
			group_obj = cls.get_or_create_group_udm_object(group_dn, lo, school, fresh=True)
			group_obj.open()
			group_users = group_obj['users'][:]
			MODULE.info('Members already present: %s' % ', '.join(group_users))

			for remove in group_changes['remove']:
				if remove in group_users:
					MODULE.info('Removing %s from %s' % (remove, group_dn))
					group_users.remove(remove)
			for add in group_changes['add']:
				if add not in group_users:
					MODULE.info('Adding %s to %s' % (add, group_dn))
					group_users.append(add)
			group_obj['users'] = group_users
			group_obj.modify()

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
	def get_search_base(cls, school):
		if school not in cls._search_base_cache:
			cls._search_base_cache[school] = SchoolSearchBase([], school)
		return cls._search_base_cache[school]

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
		if self.email:
			try:
				udm_modules.lookup('users/user', None, lo, scope='sub', base=ucr.get('ldap/base'), filter='&(!(uid=%s))(mailPrimaryAddress=%s)' % (self.username, self.email))[0]
			except IndexError:
				pass
			else:
				self.add_error('email', _('The email address is already taken by another user. Please change the email address.'))
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
					if new_value and old_value:
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

	def commit(self, lo):
		self.validate(lo)
		self._error_msg = None
		if self.errors:
			for field, errors in self.errors.iteritems():
				self._error_msg = errors[0]
			return False
		try:
			if self.action == 'create':
				self.commit_create(lo)
			elif self.action == 'modify':
				self.commit_modify(lo)
			elif self.action == 'delete':
				self.commit_delete(lo)
		except Exception as exc:
			MODULE.warn('Something went wrong. %s' % traceback.format_exc())
			self._error_msg = str(exc)
			return False
		else:
			self._udm_obj_searched = False
			self._udm_obj = None
			return True

	def get_own_container(self):
		return self.get_container(self.school)

	@classmethod
	def get_container(cls, school):
		raise NotImplementedError()

	def get_group_dn(self, group_name):
		return Group.get(group_name, self.school).dn

	def get_class_dn(self, class_name):
		return SchoolClass.get('%s-%s' % (self.school, class_name), self.school).dn

	def primary_group_dn(self, lo):
		dn = self.get_group_dn('Domain Users %s' % self.school)
		return self.get_or_create_group_udm_object(dn, lo, self.school).dn

	def commit_create(self, lo):
		pos = udm_uldap.position(ucr.get('ldap/base'))
		pos.setDn(self.get_own_container())
		udm_obj = udm_modules.get('users/user').object(None, lo, pos)
		udm_obj.open()
		udm_obj['username'] = self.username
		udm_obj['password'] = self.password or generate_random()
		udm_obj['primaryGroup'] = self.primary_group_dn(lo)
		self._alter_udm_obj(udm_obj, lo)
		udm_obj.create()
		return udm_obj

	def commit_modify(self, lo):
		udm_obj = self.get_udm_object(lo)
		udm_obj.open()
		self._alter_udm_obj(udm_obj, lo)
		udm_obj.modify()
		rdn = lo.explodeDn(udm_obj.dn)[0]
		dest = '%s,%s' % (rdn, self.get_own_container())
		if dest != udm_obj.dn:
			udm_obj.move(dest)
		return udm_obj

	def _alter_udm_obj(self, udm_obj, lo):
		udm_obj['firstname'] = self.firstname
		udm_obj['lastname'] = self.lastname
		birthday = self.birthday
		if birthday:
			birthday = self.unformat_date(birthday)
			udm_obj['birthday'] = birthday
		if self.email:
			domain_name = self.email.split('@')[-1]
			mail_domain = MailDomain.get(domain_name, self.school)
			mail_domain.create(lo)
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
				self._udm_obj = None
			self._udm_obj_searched = True
		return self._udm_obj

	def to_dict(self):
		attrs = dict([column, getattr(self, column) or ''] for column in self.get_columns())
		attrs['errors'] = self.errors
		attrs['warnings'] = self.warnings
		return attrs

	def groups_for_ucs_school(self, lo, all_found_classes, without_school_classes=False):
		group_dns = []
		group_dns.append(self.get_group_dn('Domain Users %s' % self.school))
		group_dns.append(self.get_group_dn('schueler-%s' % self.school))
		group_dns.append(self.get_group_dn('lehrer-%s' % self.school))
		group_dns.append(self.get_group_dn('mitarbeiter-%s' % self.school))

		if not without_school_classes:
			for school_class_group in all_found_classes:
				group_dns.append(school_class_group.dn)

		for group_dn in group_dns:
			self.get_or_create_group_udm_object(group_dn, lo, self.school)

		return group_dns

	def groups_used(self, lo):
		group_dns = []
		group_dns.append(self.get_group_dn('Domain Users %s' % self.school))
		group_dns.extend(self.get_specific_groups())

		for group_dn in group_dns:
			self.get_or_create_group_udm_object(group_dn, lo, self.school)

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
	def get_or_create_group_udm_object(cls, group_dn, lo, school, fresh=False):
		name = lo.explodeDn(group_dn, 1)[0]
		if Group.is_school_class(school, group_dn):
			group = SchoolClass.get(name, school)
		else:
			group = Group.get(name, school)
		if fresh:
			group._udm_obj_searched = False
		return group.create(lo)

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
				if Group.is_school_class(school, group):
					school_class_name = lo.explodeDn(group, 1)[0]
					school_class = school_class_name.split('-')[-1]
					break
			kwargs['school_class'] = school_class
		return super(Student, cls).from_udm_obj(user_obj, lo, school, date_format, columns, **kwargs)

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).students

	def get_specific_groups(self):
		groups = []
		groups.append(self.get_group_dn('schueler-%s' % self.school))
		if self.school_class:
			groups.append(self.get_class_dn(self.school_class))
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
			for group_dn in user_obj['groups']:
				if Group.is_school_class(school, group_dn):
					school_class_name = lo.explodeDn(group_dn, 1)[0]
					school_class = school_class_name.split('-')[-1]
					school_classes.append(school_class)
			kwargs['school_class'] = ','.join(school_classes)
		return super(Teacher, cls).from_udm_obj(user_obj, lo, school, date_format, columns, **kwargs)

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).teachers

	def get_specific_groups(self):
		groups = []
		groups.append(self.get_group_dn('lehrer-%s' % self.school))
		if self.school_class:
			for school_class in self.school_class.split(','):
				groups.append(self.get_class_dn(school_class))
		return groups

class Staff(User):
	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).staff

	def get_specific_groups(self):
		groups = []
		groups.append(self.get_group_dn('mitarbeiter-%s' % self.school))
		return groups

class TeacherAndStaff(Teacher):
	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).teachersAndStaff

	def get_specific_groups(self):
		groups = super(TeacherAndStaff, self).get_specific_groups()
		groups.append(self.get_group_dn('mitarbeiter-%s' % self.school))
		return groups

class UCSSchoolHelperAbstractClass(object):
	udm_module = None
	udm_filter = ''
	cache = {}

	_search_base_cache = {}
	_initialized_udm_modules = []

	@classmethod
	def get(cls, name, school):
		key = cls.__name__, name, school
		if key not in cls.cache:
			MODULE.info('Initializing %r' % (key,))
			obj = cls(name, school)
			cls.cache[key] = obj
		return cls.cache[key]

	def __init__(self, name, school):
		self._udm_obj_searched = False
		self._udm_obj = None
		self.name = name
		self.school = school
		self.dn = self.get_dn()

	def create(self, lo):
		MODULE.process('Creating %s' % self.dn)
		udm_obj = self.get_udm_object(lo)
		if udm_obj:
			MODULE.process('%s already exists!' % self.dn)
			return udm_obj

		pos = udm_uldap.position(ucr.get('ldap/base'))
		pos.setDn(self.get_own_container())
		udm_obj = udm_modules.get(self.udm_module).object(None, lo, pos)
		udm_obj.open()

		# here is the real logic
		self.do_create(udm_obj, lo)

		# get it fresh from the database (needed for udm_obj._exists ...)
		self._udm_obj_searched = False
		udm_obj = self.get_udm_object(lo)
		return udm_obj

	def do_create(self, udm_obj, lo):
		raise NotImplementedError()

	def get_udm_object(self, lo):
		if self._udm_obj_searched is False:
			try:
				self._udm_obj = udm_modules.lookup(self.udm_module, None, lo, scope='base', base=self.dn)[0]
			except noObject:
				self._udm_obj = None
			self._udm_obj_searched = True
		return self._udm_obj

	def get_dn(self):
		return 'cn=%s,%s' % (self.name, self.get_own_container())

	def get_own_container(self):
		return self.get_container(self.school)

	@classmethod
	def get_container(cls, school):
		raise NotImplementedError()

	@classmethod
	def get_search_base(cls, school):
		if school not in cls._search_base_cache:
			cls._search_base_cache[school] = SchoolSearchBase([], school)
		return cls._search_base_cache[school]

	@classmethod
	def init_udm_module(cls, lo):
		if cls.udm_module in cls._initialized_udm_modules:
			return
		pos = udm_uldap.position(lo.base)
		udm_modules.init(lo, pos, udm_modules.get(cls.udm_module))
		cls._initialized_udm_modules.append(cls.udm_module)

	@classmethod
	def get_all(cls, school, lo):
		cls.init_udm_module(lo)
		ret = []
		udm_objs = udm_modules.lookup(cls.udm_module, None, lo, filter=cls.udm_filter, base=cls.get_container(school))
		for udm_obj in udm_objs:
			udm_obj.open()
			ret.append(cls.from_udm_obj(udm_obj, school))
		return ret

	@classmethod
	def from_udm_obj(cls, udm_obj, school):
		raise NotImplementedError()

	def __repr__(self):
		return '%s(name=%r, school=%r)' % (self.__class__.__name__, self.name, self.school)

	def __lt__(self, other):
		return self.name < other.name

	@classmethod
	def from_dn(cls, dn, school, lo):
		cls.init_udm_module(lo)
		udm_obj = udm_modules.lookup(cls.udm_module, None, lo, filter=cls.udm_filter, base=dn, scope='base')[0]
		udm_obj.open()
		return cls.from_udm_obj(udm_obj, school)

class Group(UCSSchoolHelperAbstractClass):
	udm_module = 'groups/group'

	def __init__(self, name, school, description=None):
		super(Group, self).__init__(name, school)
		self.description = description

	def do_create(self, udm_obj, lo):
		udm_obj['name'] = self.name
		if self.description:
			udm_obj['description'] = self.description
		udm_obj.create()

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).groups

	@classmethod
	def is_school_class(cls, school, group_dn):
		return cls.get_search_base(school).isClass(group_dn)

	@classmethod
	def from_udm_obj(cls, udm_obj, school):
		return cls(udm_obj['name'], school, udm_obj['description'])

class SchoolClass(Group):
	def create(self, lo):
		udm_obj = super(SchoolClass, self).create(lo)

		# alright everything in place.
		# but school classes all have their corresponding share!
		self.create_share(lo)
		return udm_obj

	def create_share(self, lo):
		share = ClassShare.from_school_class(self)
		share.create(lo)
		return share

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).classes

class ClassShare(UCSSchoolHelperAbstractClass):
	udm_module = 'shares/share'

	def __init__(self, name, school, school_class=None):
		super(ClassShare, self).__init__(name, school)
		self.school_class = school_class

	@classmethod
	def from_school_class(cls, school_class):
		obj = cls.get(school_class.name, school_class.school)
		obj.school_class = school_class

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).classShares

	def do_create(self, udm_obj, lo):
		gid = self.school_class.get_udm_object(lo)['gidNumber']
		udm_obj['name'] = self.name
		udm_obj['host'] = self.get_server_fqdn(lo)
		udm_obj['path'] = '/home/groups/klassen/%s' % self.name
		udm_obj['writeable'] = '1'
		udm_obj['sambaWriteable'] = '1'
		udm_obj['sambaBrowseable'] = '1'
		udm_obj['sambaForceGroup'] = '+%s' % self.name
		udm_obj['sambaCreateMode'] = '0770'
		udm_obj['sambaDirectoryMode'] = '0770'
		udm_obj['owner'] = '0'
		udm_obj['group'] = gid
		udm_obj['directorymode'] = '0770'
		udm_obj.create()
		MODULE.process('Share created on "%s"' % udm_obj['host'])

	def get_server_fqdn(self, lo):
		domainname = ucr.get('domainname')
		school_dn = School.get(self.school).dn

		# fetch serverfqdn from OU
		result = lo.get(school_dn, ['ucsschoolClassShareFileServer'])
		if result:
			server_domain_name = lo.get(result['ucsschoolClassShareFileServer'][0], ['associatedDomain'])
			if server_domain_name:
				server_domain_name = server_domain_name['associatedDomain'][0]
			else:
				server_domain_name = domainname
			result = lo.get(result['ucsschoolClassShareFileServer'][0], ['cn'])
			if result:
				return '%s.%s' % (result['cn'][0], server_domain_name)

		# get alternative server (defined at ou object if a dc slave is responsible for more than one ou)
		ou_attr_ldap_access_write = lo.get(school_dn, ['univentionLDAPAccessWrite'])
		alternative_server_dn = None
		if len(ou_attr_ldap_access_write) > 0:
			alternative_server_dn = ou_attr_ldap_access_write['univentionLDAPAccessWrite'][0]
			if len(ou_attr_ldap_access_write) > 1: # TODO FIXME This doesn't look correct to me - ou_attr_ldap_access_write is a dict and not a list!
				MODULE.warn('more than one corresponding univentionLDAPAccessWrite found at ou=%s' % self.school)

		# build fqdn of alternative server and set serverfqdn
		if alternative_server_dn:
			alternative_server_attr = lo.get(alternative_server_dn,['uid'])
			if len(alternative_server_attr) > 0:
				alternative_server_uid = alternative_server_attr['uid'][0]
				alternative_server_uid = alternative_server_uid.replace('$','')
				if len(alternative_server_uid) > 0:
					return '%s.%s' % (alternative_server_uid, domainname)

		# fallback
		return 'dc%s-01.%s' % (self.school.lower(), domainname)

class MailDomain(UCSSchoolHelperAbstractClass):
	udm_module = 'mail/domain'

	@classmethod
	def get_container(cls, school):
		return 'cn=domain,cn=mail,%s' % ucr.get('ldap/base')

	def do_create(self, udm_obj, lo):
		udm_obj['name'] = self.name
		udm_obj.create()

class School(UCSSchoolHelperAbstractClass):
	udm_module = 'container/ou'
	udm_filter = 'objectClass=ucsschoolOrganizationalUnit'

	def __init__(self, name, school=None, display_name=None):
		super(School, self).__init__(name, None)
		self.display_name = display_name or name

	@classmethod
	def get_container(cls, school=None):
		return ucr.get('ldap/base')

	@classmethod
	def get(cls, name):
		return super(School, cls).get(name, None)

	def get_dn(self):
		return self.get_search_base(self.name).schoolDN

	def do_create(self, udm_obj, lo):
		udm_obj.options = ['ucsschoolOrganizationalUnit']
		udm_obj['name'] = self.name
		udm_obj['displayName'] = self.display_name
		udm_obj.create()

	@classmethod
	def from_udm_obj(cls, udm_obj, school):
		return cls(udm_obj['name'], school, udm_obj['displayName'])

	@classmethod
	def get_from_oulist(cls, lo, oulist):
		ous = [x.strip() for x in oulist.split(',')]
		schools = []
		for ou in ous:
			MODULE.info('All Schools: Getting OU %s' % ou)
			school = cls.from_dn(cls(ou).dn, None, lo)
			MODULE.info('All Schools: Found school: %r' % school)
			schools.append(school)
		return schools

	@classmethod
	def get_all(cls, lo, restrict_to_user=True):
		if restrict_to_user:
			if lo.binddn.find('ou=') > 0:
				# we got an OU in the user DN -> school teacher or assistent
				# restrict the visibility to current school
				# (note that there can be schools with a DN such as ou=25g18,ou=25,dc=...)
				school_dn = lo.binddn[lo.binddn.find('ou='):]
				MODULE.info('All Schools: Found an OU in the LDAP binddn. Restricting schools to only show %s' % school_dn)
				school = cls.from_dn(school_dn, None, lo)
				MODULE.info('All Schools: Found school: %r' % school)
				return [school]
			else:
				MODULE.warn('All Schools: Unable to identify OU of this account - showing all OUs!')
				oulist = ucr.get('ucsschool/local/oulist')
				if oulist:
					# OU list override via UCR variable (it can be necessary to adjust the list of
					# visible schools on specific systems manually)
					MODULE.info('All Schools: Schools overridden by UCR variable ucsschool/local/oulist')
					return cls.get_from_oulist(cls, lo, oulist)
		return super(School, cls).get_all(None, lo)

	@classmethod
	def get_all_hosted(cls, lo):
		oulist = ucr.get('ucsschool/local/oulist')
		if oulist:
			MODULE.info('All hosted schools: Schools overridden by UCR variable ucsschool/local/oulist')
			return cls.get_from_oulist(cls, lo, oulist)
		else:
			index_ou = lo.binddn.find('ou=')
			if index_ou > 0:
				# we got an OU in the bind DN
				# (note that there can be schools with a DN such as ou=25g18,ou=25,dc=...)
				# TODO: districtmode
				# TODO: school DCs hosting multiple OUs
				school_dn = lo.binddn[index_ou:]
				MODULE.info('All hosted schools: Found an OU in the LDAP binddn: %s' % school_dn)
				school = cls.from_dn(school_dn, None, lo)
				MODULE.info('All hosted schools: Found school: %r' % school)
				return [school]
			else:
				MODULE.warn('All hosted schools: Unable to identify OU of this account - showing all OUs!')
				return super(School, cls).get_all(None, lo)

	def __repr__(self):
		return '%s(name=%r, display_name=%r)' % (self.__class__.__name__, self.name, self.display_name)

