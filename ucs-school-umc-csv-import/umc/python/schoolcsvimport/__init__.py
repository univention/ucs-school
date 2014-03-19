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

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import file_upload

from ucsschool.lib.schoolldap import SchoolBaseModule

_ = Translation('ucs-school-umc-csv-import').translate

class Instance(SchoolBaseModule):
	def init(self):
		super(Instance, self).init()
		self.file_map = {}

	@file_upload
	def save_csv(self, request):
		result = {}
		csv_id = str(uuid.uuid4())
		school = request.body['school']
		user_type = request.body['type']
		filename = request.options[0]['tmpfile']
		MODULE.process('Processing %s' % filename)
		sniffer = csv.Sniffer()
		available_columns = [
			{_('Unused') : 'unused'},
			{_('Username') : 'username'},
			{_('First name') : 'firstname'},
			{_('Last name') : 'lastname'},
			{_('Birthday') : 'birthday'},
			{_('Class') : 'class'},
			{_('Email') : 'email'},
		]
		untranslated_columns = {
			'Username' : 'username',
			'First name' : 'firstname',
			'Last name' : 'lastname',
			'Birthday' : 'birthday',
			'Class' : 'class',
			'Email' : 'email',
		}
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
			def _find_column(column, i):
				for column_definition in available_columns:
					if column in column_definition:
						return column_definition[column]
				return untranslated_columns.get(column, 'unused%d' % i)
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
			columns = [_find_column(column, i) for i, column in enumerate(columns)]
			MODULE.process('First line translates to columns: %r' % columns)
		except csv.Error as exc:
			MODULE.warn('Malformatted CSV file? %s' % exc)
			result['success'] = False
			# result['message'] = ''
			self.finished(request.id, [result])
		else:
			self.file_map[csv_id] = filename, school, user_type
			result['success'] = True
			result['filename'] = filename
			result['file_id'] = csv_id
			result['available_columns'] = available_columns
			result['given_columns'] = columns
			result['first_lines'] = first_lines
			self.finished(request.id, [result])

	def destroy(self):
		for filename, school, user_type in self.file_map.itervalues():
			if os.path.exists(filename):
				os.unlink(filename)
		return super(Instance, self).destroy()

