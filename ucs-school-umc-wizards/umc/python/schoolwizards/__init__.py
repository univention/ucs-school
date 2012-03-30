#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  Wizards
#
# Copyright 2012 Univention GmbH
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

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_OptionMissing, UMC_CommandError, UMC_OptionTypeError
from univention.management.console.protocol.definitions import *
import univention.admin.modules as udm_modules

from ucsschool.lib.schoolldap import SchoolBaseModule, LDAP_Connection, LDAP_Filter

from SchoolImport import *

_ = Translation('ucs-school-umc-wizards').translate

class Instance(SchoolBaseModule, SchoolImport):
	"""Base class for the schoolwizards UMC module.
	"""
	def required_values(self, request, *keys):
		missing = filter(lambda key: '' == request.options[key], keys)
		if missing:
			raise ValueError(_('Missing value for the following properties: %s')
			                 % ','.join(missing))

	@LDAP_Connection()
	def _username_used(self, username, search_base=None,
	                   ldap_user_read=None, ldap_position=None):
		ldap_filter = LDAP_Filter.forAll(username, ['username'])
		user_exists = udm_modules.lookup('users/user', None, ldap_user_read,
		                                 scope = 'sub', filter = ldap_filter)
		return bool(user_exists)

	@LDAP_Connection()
	def _mail_address_used(self, address, search_base=None,
	                       ldap_user_read=None, ldap_position=None):
		ldap_filter = LDAP_Filter.forAll(address, ['mailPrimaryAddress'])
		address_exists = udm_modules.lookup('users/user', None, ldap_user_read,
		                                    scope = 'sub', filter = ldap_filter)
		return bool(address_exists)

	@LDAP_Connection()
	def _school_name_used(self, name, search_base=None,
	                      ldap_user_read=None, ldap_position=None):
		return bool(name in search_base.availableSchools)

	@LDAP_Connection()
	def _class_name_used(self, school, name, search_base=None,
	                     ldap_user_read=None, ldap_position=None):
		ldap_filter = LDAP_Filter.forAll(name, ['name'], prefixes = { 'name' : '%s-' % school })
		class_exists = udm_modules.lookup('groups/group', None, ldap_user_read, scope = 'one',
		                                  filter = ldap_filter, base = search_base.classes)
		return bool(class_exists)

	def create_user(self, request):
		"""Create a new user.
		"""
		try:
			# Validate request options
			keys = ['username', 'lastname', 'firstname', 'school', 'class', 'type']
			self.required_options(request, *keys)
			self.required_values(request, *keys)

			if self._username_used(request.options['username']):
				raise ValueError(_('Username is already in use'))
			if request.options.get('mailPrimaryAddress', ''):
				if self._mail_address_used(request.options['mailPrimaryAddress']):
					raise ValueError(_('Mail address is already in use'))

			isTeacher = False
			isStaff = False
			if request.options['type'] not in ['student', 'teacher', 'staff', 'teachersAndStaff']:
				raise ValueError(_('Invalid value for  \'type\' property'))
			if request.options['type'] == 'teacher':
				isTeacher = True
			elif request.options['type'] == 'staff':
				isStaff = True
			elif request.options['type'] == 'teachersAndStaff':
				isStaff = True
				isTeacher = True

			# Create the user
			self.import_user(request.options['username'],
			                 request.options['lastname'],
			                 request.options['firstname'],
			                 request.options['school'],
			                 request.options['class'],
			                 request.options.get('mailPrimaryAddress', ''),
			                 isTeacher,
			                 isStaff)
		except (ValueError, IOError, OSError), err:
			MODULE.info(str(err))
			result = {'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('User successfully created'))

	def create_school(self, request):
		"""Create a new school.
		"""
		try:
			# Validate request options
			self.required_options(request, 'name')
			self.required_values(request, 'name')

			if self._school_name_used(request.options['name']):
				raise ValueError(_('School name is already in use'))

			# Create the school
			self.create_ou(request.options['name'])
		except (ValueError, IOError, OSError), err:
			MODULE.info(str(err))
			result = {'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('School successfully created'))

	def create_class(self, request):
		"""Create a new class.
		"""
		try:
			# Validate request options
			self.required_options(request, 'school', 'name')
			self.required_values(request, 'school', 'name')

			if not self._school_name_used(request.options['school']):
				raise ValueError(_('Unknown school'))

			if self._class_name_used(request.options['school'], request.options['name']):
				raise ValueError(_('Class name is already in use'))

			# Create the school
			self.import_class(request.options['school'],
			                  request.options['name'],
			                  request.options.get('description', ''))
		except (ValueError, IOError, OSError), err:
			MODULE.info(str(err))
			result = {'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('Class successfully created'))
