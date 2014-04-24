#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  UCS@school CSV Upload (helper)
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

import csv
from datetime import datetime, date
from ldap.filter import escape_filter_chars
import traceback

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.admin.filter import conjunction, expression

from ucsschool.lib.models import User, Student, Teacher, Staff, TeachersAndStaff

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

class CSVUser(User):
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
			udm_obj = self.get_first(lo, str(ldap_filter))
			if udm_obj:
				return udm_obj['username']

		# generate a reasonable one
		firstname = ''
		if self.firstname:
			firstname = self.firstname.split()[0].lower() + '.'
		lastname = ''
		if self.lastname:
			lastname = self.lastname.split()[-1].lower()
		return firstname + lastname

	@classmethod
	def from_csv_line(cls, attrs, school, date_format, line_no, lo):
		user = cls(**attrs)
		user.name = user.guess_username(lo, date_format)
		user.school = school
		if user.birthday:
			try:
				user.birthday = unformat_date(user.birthday, date_format)
			except (TypeError, ValueError):
				pass

		if user.exists(lo):
			user.action = 'modify'
		else:
			user.action = 'create'
		user.line = line_no
		return user

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
		# called Mr. Line
		return real_column > 1

	@classmethod
	def find_all_fields(cls):
		return cls._attributes.keys()

	@classmethod
	def find_field_label_from_name(cls, field):
		for name, attr in cls._attributes.items():
			if name == field:
				return attr.label

	@classmethod
	def find_field_name_from_label(cls, label, i):
		for name, attr in cls._attributes.items():
			if attr.label == label or label in attr.aka:
				return name
		return 'unused%d' % i

	@classmethod
	def get_required_columns(cls):
		return [key for key, attr in cls._attributes.iteritems() if attr.required]

	@classmethod
	def get_columns_for_assign(cls):
		columns = [{'name' : 'unused', 'label' : _('Unused')}]
		columns.extend(cls.get_columns_for_frontend(cls.find_all_fields()))
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
		for field in column_names:
			label = cls.find_field_label_from_name(field)
			if label:
				columns.append({'name' : field, 'label' : label})
		return columns

	@classmethod
	def bulk_group_change(cls, lo, school, group_changes):
		for group_dn, group_changes in group_changes.iteritems():
			MODULE.process('Changing group memberships for %s' % group_dn)
			MODULE.info('Changes: %r' % group_changes)

			# do not use the group cache. get a fresh instance from database
			group = cls.get_or_create_group_udm_object(group_dn, lo, school, fresh=True)
			group_obj = group.get_udm_object(lo)
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

	def merge_additional_group_changes(self, lo, changes, all_found_classes, without_school_classes=False):
		if self.action not in ['create', 'modify']:
			return
		udm_obj = self.get_udm_object(lo)
		if not udm_obj:
			MODULE.error('%s does not have an associated UDM object. This should not happen. Unable to set group memberships here!' % self.name)
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

	def to_dict(self, format_birthday):
		attrs = super(CSVUser, self).to_dict()
		if format_birthday:
			# force format of date as requested, not as seen in LDAP
			try:
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
				self.modify(lo, validate=False)
			elif self.action == 'delete':
				self.delete(lo)
		except Exception as exc:
			MODULE.warn('Something went wrong. %s' % traceback.format_exc())
			self._error_msg = str(exc)
			return False
		else:
			return True

	def validate(self, lo):
		super(CSVUser, self).validate(lo, validate_unlikely_changes=True)
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
		if cls.is_student(school, udm_obj.dn):
			return CSVStudent
		if cls.is_teacher(school, udm_obj.dn):
			if cls.is_staff(school, udm_obj.dn):
				return CSVTeachersAndStaff
			return CSVTeacher
		if cls.is_staff(school, udm_obj.dn):
			return CSVStaff
		return cls

class CSVStudent(CSVUser, Student):
	pass

class CSVTeacher(CSVUser, Teacher):
	pass

class CSVStaff(CSVUser, Staff):
	pass

class CSVTeachersAndStaff(CSVUser, TeachersAndStaff):
	pass

