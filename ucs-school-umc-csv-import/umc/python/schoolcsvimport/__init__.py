#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  UCS@school CSV Upload
#
# Copyright 2014-2015 Univention GmbH
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
import csv
import re
import locale

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import file_upload, simple_response, multi_response
from univention.management.console.modules.mixins import ProgressMixin
from univention.config_registry import ConfigRegistry

from ucsschool.lib.schoolldap import SchoolBaseModule, open_ldap_connection
from ucsschool.lib.models.utils import create_passwd, add_module_logger_to_schoollib, stopped_notifier

from univention.management.console.modules.schoolcsvimport.util import CSVUser, CSVStudent, CSVTeacher, CSVStaff, CSVTeachersAndStaff, UCS_License_detection, LicenseInsufficient

_ = Translation('ucs-school-umc-csv-import').translate

ucr = ConfigRegistry()
ucr.load()

def generate_random():
	return create_passwd(length=30)

def license_check(users):
	change = 0
	for user in users:
		if user.action == 'delete':
			change -= 1
		if user.action == 'create':
			change += 1
	user_info = {'users' : change}
	ucs_license = UCS_License_detection(ucr)
	try:
		ucs_license.check_license(user_info)
	except LicenseInsufficient as e:
		return str(e) + ' ' + _('You may proceed with the import, but the domain management may be limited afterwards until a new UCS license is imported. Please note that this warning is based on the assumption that all users will be imported. You may ignore certain lines in the following.')

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

class Instance(SchoolBaseModule, ProgressMixin):
	def init(self):
		super(Instance, self).init()
		add_module_logger_to_schoollib()
		self.file_map = {}

	@file_upload
	def save_csv(self, request):
		result = {}
		file_id = generate_random()
		school = request.body['school']
		user_type = request.body['type']
		delete_not_mentioned = bool(request.body.get('delete_not_mentioned'))
		user_klass = None
		if user_type == 'student':
			user_klass = CSVStudent
		elif user_type == 'teacher':
			user_klass = CSVTeacher
		elif user_type == 'staff':
			user_klass = CSVStaff
		elif user_type == 'teachersAndStaff':
			user_klass = CSVTeachersAndStaff
		filename = request.options[0]['tmpfile']
		MODULE.process('Processing %s' % filename)
		sniffer = csv.Sniffer()
		with open(filename, 'rb') as f:
			content = f.read()
			# try utf-8 and latin-1
			# if this still fails -> traceback...
			try:
				content = content.decode('utf-8')
			except UnicodeDecodeError:
				content = content.decode('latin-1')
			lines = content.splitlines()
		try:
			first_line = ''
			if lines:
				first_line = lines[0].strip()
				try:
					MODULE.process('First line is:\n%s' % first_line)
				except TypeError:
					MODULE.error('First line is not printable! Wrong CSV format!')
			try:
				# be strict regarding delimiters. I have seen the
				# sniffer returning 'b' as the delimiter in some cases
				dialect = sniffer.sniff(str(content), delimiters=' ,;\t')
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

			num_lines = 0
			with open(filename, 'wb') as f:
				reader = csv.reader(lines, dialect)
				writer = csv.writer(f, dialect)
				csv_columns = [] # Benutzername,Vorname,Irgendwas
				columns = [] # name,firstname,unused2
				first_lines = []
				for line in reader:
					if not any(cell.strip() for cell in line):
						# empty line
						continue
					writer.writerow(line)
					if not csv_columns:
						if has_header:
							csv_columns = line
							continue
						else:
							csv_columns = ['unused%d' % x for x in range(len(line))]
					if len(first_lines) < 10:
						first_lines.append(line)
					num_lines += 1
				if num_lines == 0:
					raise csv.Error('Empty!')
				for i, column in enumerate(csv_columns):
					column_name = user_klass.find_field_name_from_label(column, i)
					if column_name in columns:
						column_name = 'unused%d' % i
					columns.append(column_name)
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
			result['num_more_lines'] = num_lines - len(first_lines)
			self.finished(request.id, [result])

	def _guess_date_format(self, date_pattern, python_date_format, value):
		if value and python_date_format is None:
			if re.match(r'^\d{2}\.\d{2}\.\d{2}$', value):
				python_date_format = '%d.%m.%y'
				date_pattern = 'dd.MM.yy'
			elif re.match(r'^\d{2}\.\d{2}\.\d{4}$', value):
				python_date_format = '%d.%m.%Y'
				date_pattern = 'dd.MM.yyyy'
			elif re.match(r'^\d{2}-\d{2}-\d{2}$', value):
				python_date_format = '%y-%m-%d'
				date_pattern = 'yy-MM-dd'
			elif re.match(r'^\d{4}-\d{2}-\d{2}$', value):
				python_date_format = '%Y-%m-%d'
				date_pattern = 'yyyy-MM-dd'
			elif re.match(r'^\d{2}/\d{2}/\d{2}$', value):
				python_date_format = '%m/%d/%y'
				date_pattern = 'MM/dd/yy'
			elif re.match(r'^\d{2}/\d{2}/\d{4}$', value):
				python_date_format = '%m/%d/%Y'
				date_pattern = 'MM/dd/yyyy'
		return date_pattern, python_date_format

	@simple_response(with_progress=True)
	def show(self, progress, file_id, columns):
		result = {}
		progress.title = _('Checking users from CSV file')
		file_info = self.file_map[file_id]
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		with open(file_info.filename, 'rb') as f:
			lines = f.readlines()
			if file_info.has_header:
				lines = lines[1:]
		reader = csv.DictReader(lines, columns, dialect=file_info.dialect)
		users = []
		date_pattern = 'yyyy-MMM-dd'
		if locale.getlocale()[0] == 'de':
			date_pattern = 'dd.MMM.yyyy'
		python_date_format = None
		line_no = 1
		if file_info.has_header:
			line_no = 2
		for line in reader:
			if 'birthday' in columns:
				date_pattern, python_date_format = self._guess_date_format(date_pattern, python_date_format, line['birthday'])
			user = file_info.user_klass.from_csv_line(line, file_info.school, python_date_format, line_no, lo)
			user.validate(lo)
			users.append(user)
			line_no += 1
			progress.progress(message=user.name)
		if 'name' not in columns:
			# add username here:
			# 1. it has to be presented and will be populated by a guess
			# 2. do it before adding the to_be_deleted, as they need it
			# in the columns, otherwise their real username gets overwritten
			columns.insert(0, 'name')
		if file_info.delete_not_mentioned:
			mentioned_usernames = map(lambda u: u.name, users)
			progress.title = _('Checking users from database')
			progress.message = ''
			existing_users = file_info.user_klass.get_all(lo, file_info.school)
			for user in existing_users:
				if user.name not in mentioned_usernames:
					if 'birthday' in columns:
						date_pattern, python_date_format = self._guess_date_format(date_pattern, python_date_format, user.birthday)
					user.action = 'delete'
					user.line = ''
					users.append(user)
					progress.progress(message=user.name)
		file_info.date_format = python_date_format
		file_info.columns = columns
		result['date_pattern'] = date_pattern
		result['columns'] = file_info.user_klass.get_columns_for_spreadsheet(columns)
		result['required_columns'] = file_info.user_klass.get_required_columns()
		result['users'] = [user.to_dict(file_info.date_format) for user in users]
		result['license_error'] = license_check(users)
		return result

	@simple_response
	def recheck_users(self, file_id, user_attrs):
		file_info = self.file_map[file_id]
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		users = []
		for attrs in user_attrs:
			user = file_info.user_klass.from_frontend_attrs(attrs, file_info.school, file_info.date_format)
			user.validate(lo)
			users.append(user.to_dict(file_info.date_format))
		return users

	@multi_response(progress=[_('Processing %d user(s)'), _('%(username)s %(action)s')])
	def import_users(self, iterator, file_id, attrs):
		lo = open_ldap_connection(self._user_dn, self._password, ucr.get('ldap/server/name'))
		file_info = None
		with stopped_notifier():
			CSVUser.invalidate_all_caches()
			for file_id, attrs in iterator:
				if file_info is None:
					file_info = self.file_map[file_id]
				user = file_info.user_klass.from_frontend_attrs(attrs, file_info.school, file_info.date_format)
				MODULE.process('Going to %s %s %s' % (user.action, file_info.user_klass.__name__, user.name))
				action = user.action
				if action == 'create':
					action = _('created')
				elif action == 'modify':
					action = _('modified')
				if action == 'delete':
					action = _('deleted')
				if user.commit(lo):
					yield {'username' : user.name, 'action' : action, 'success' : True}
				else:
					yield {'username' : user.name, 'action' : action, 'success' : False, 'msg' : user.get_error_msg()}
		if file_info:
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

