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

import apt
import re

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_OptionMissing, UMC_CommandError, UMC_OptionTypeError
from univention.management.console.protocol.definitions import *
from univention.admin.uexceptions import valueError
import univention.admin.modules as udm_modules
import univention.admin.syntax as udm_syntax

from ucsschool.lib.schoolldap import SchoolBaseModule, LDAP_Connection, LDAP_Filter, _init_search_base

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

	def _username_used(self, username, ldap_user_read):
		ldap_filter = LDAP_Filter.forAll(username, ['username'])
		user_exists = udm_modules.lookup('users/user', None, ldap_user_read,
		                                 scope = 'sub', filter = ldap_filter)
		return bool(user_exists)

	def _mail_address_used(self, address, ldap_user_read):
		ldap_filter = LDAP_Filter.forAll(address, ['mailPrimaryAddress'])
		address_exists = udm_modules.lookup('users/user', None, ldap_user_read,
		                                    scope = 'sub', filter = ldap_filter)
		return bool(address_exists)

	def _school_name_used(self, name, ldap_user_read, search_base):
		return bool(name in search_base.availableSchools)

	def _class_name_used(self, school, name, ldap_user_read, search_base):
		ldap_filter = LDAP_Filter.forAll(name, ['name'], prefixes = { 'name' : '%s-' % school })
		class_exists = udm_modules.lookup('groups/group', None, ldap_user_read, scope = 'one',
		                                  filter = ldap_filter, base = search_base.classes)
		return bool(class_exists)

	def _computer_name_used(self, name, ldap_user_read):
		ldap_filter = LDAP_Filter.forAll(name, ['name'])
		computer_exists = udm_modules.lookup('computers/computer', None, ldap_user_read,
		                                     scope = 'sub', filter = ldap_filter)
		return bool(computer_exists)

	def _mac_address_used(self, address, ldap_user_read):
		ldap_filter = LDAP_Filter.forAll(address, ['mac'])
		address_exists = udm_modules.lookup('computers/computer', None, ldap_user_read,
		                                    scope = 'sub', filter = ldap_filter)
		return bool(address_exists)

	@LDAP_Connection()
	def create_user(self, request, search_base=None,
	                ldap_user_read=None, ldap_position=None):
		"""Create a new user.
		"""
		try:
			# Validate request options
			keys = ['username', 'lastname', 'firstname', 'school', 'type']
			self.required_options(request, *keys)
			self.required_values(request, *keys)

			request = remove_whitespaces(request)

			username = udm_syntax.UserName.parse(request.options['username'])
			lastname = request.options['lastname']
			firstname = request.options['firstname']
			school = udm_syntax.GroupName.parse(request.options['school'])
			mail_primary_address = request.options.get('mailPrimaryAddress', '')
			class_ = request.options.get('class', '')
			password = request.options.get('password', '')
			type_ = request.options['type']

			if self._username_used(username, ldap_user_read):
				raise ValueError(_('Username is already in use'))
			if mail_primary_address:
				if self._mail_address_used(udm_syntax.emailAddressTemplate.parse(mail_primary_address),
				                           ldap_user_read):
					raise ValueError(_('Mail address is already in use'))

			is_teacher = False
			is_staff = False
			if type_ in ['student', 'teacher', 'staff', 'teachersAndStaff']:
				# The class name is only required if the user is a student
				if type_ == 'student':
					self.required_options(request, 'class')
					self.required_values(request, 'class')
			else:
				raise ValueError(_('Invalid value for  \'type\' property'))
			if type_ == 'teacher':
				is_teacher = True
			elif type_ == 'staff':
				is_staff = True
			elif type_ == 'teachersAndStaff':
				is_staff = True
				is_teacher = True

			# Create the user
			self.import_user(username, lastname, firstname, school, class_,
			                 mail_primary_address, is_teacher, is_staff, password)

			if not self._username_used(username, ldap_user_read):
				raise OSError(_('The user could not be created'))
		except (ValueError, IOError, OSError, valueError), err:
			MODULE.info(str(err))
			result = {'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('User successfully created'))

	@LDAP_Connection()
	def create_school(self, request, search_base=None,
	                  ldap_user_read=None, ldap_position=None):
		"""Create a new school.
		"""
		try:
			# Validate request options
			options = ['name']
			if not self._is_singlemaster():
				options.append('schooldc')
			self.required_options(request, *options)
			self.required_values(request, *options)

			request = remove_whitespaces(request)

			name = udm_syntax.GroupName.parse(request.options['name'])
			schooldc = request.options.get('schooldc', '')

			if not self._is_singlemaster():
				regex = re.compile('^\w+$')
				if not regex.match(schooldc):
					raise ValueError(_('Invalid school server name'))
			if self._school_name_used(name, ldap_user_read, search_base):
				raise ValueError(_('School name is already in use'))

			# Create the school
			self.create_ou(name, schooldc)
			_init_search_base(ldap_user_read, force = True)
		except (ValueError, IOError, OSError), err:
			MODULE.info(str(err))
			result = {'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('School successfully created'))

	@LDAP_Connection()
	def create_class(self, request, search_base=None,
	                 ldap_user_read=None, ldap_position=None):
		"""Create a new class.
		"""
		try:
			# Validate request options
			self.required_options(request, 'school', 'name')
			self.required_values(request, 'school', 'name')

			request = remove_whitespaces(request)

			school = udm_syntax.GroupName.parse(request.options['school'])
			name = udm_syntax.GroupName.parse(request.options['name'])
			description = request.options.get('description', '')

			if not self._school_name_used(school, ldap_user_read, search_base):
				raise ValueError(_('Unknown school'))
			if self._class_name_used(school, name, ldap_user_read, search_base):
				raise ValueError(_('Class name is already in use'))

			# Create the school
			self.import_group(school, name, description)

			if not self._class_name_used(school, name, ldap_user_read, search_base):
				raise OSError(_('The class could not be created'))
		except (ValueError, IOError, OSError), err:
			MODULE.info(str(err))
			result = {'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('Class successfully created'))

	@LDAP_Connection()
	def create_computer(self, request, search_base=None,
	                    ldap_user_read=None, ldap_position=None):
		"""Create a new computer.
		"""
		try:
			# Validate request options
			self.required_options(request, 'type', 'name', 'mac', 'school', 'ipAddress')
			self.required_values(request, 'type', 'name', 'mac', 'school', 'ipAddress')

			request = remove_whitespaces(request)

			type_ = request.options['type']
			name = udm_syntax.hostName.parse(request.options['name'])
			mac = udm_syntax.MAC_Address.parse(request.options['mac'])
			school = request.options['school']
			ip_address = udm_syntax.ipv4Address.parse(request.options['ipAddress'])
			subnet_mask = request.options.get('subnetMask', '')
			inventory_number = request.options.get('inventoryNumber', '')

			if not self._school_name_used(school, ldap_user_read, search_base):
				raise ValueError(_('Unknown school'))
			if self._computer_name_used(name, ldap_user_read):
				raise ValueError(_('Computer name is already in use'))
			if self._mac_address_used(mac, ldap_user_read):
				raise ValueError(_('MAC address is already in use'))
			if subnet_mask:
				subnet_mask = udm_syntax.netmask.parse(subnet_mask)
			if type_ not in ['ipmanagedclient', 'windows']:
				raise ValueError(_('Invalid value for  \'type\' property'))

			# Create the computer
			self.import_computer(type_, name, mac, school, ip_address,
			                     subnet_mask, inventory_number)

			if not self._computer_name_used(name, ldap_user_read):
				raise OSError(_('The computer could not be created'))
		except (ValueError, IOError, OSError, valueError), err:
			MODULE.info(str(err))
			result = {'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('Computer successfully created'))

	def _is_singlemaster(self):
		PKG_NAME = 'ucs-school-singlemaster'
		cache = apt.Cache()

		is_installed = False
		if PKG_NAME in cache:
			pkg = cache[PKG_NAME]
			is_installed = pkg.is_installed

		return is_installed

	def is_singlemaster(self, request):
		self.finished(request.id, self._is_singlemaster())


def remove_whitespaces(request):
	for key, value in request.options.iteritems():
		if isinstance(value, basestring):
			request.options[key] = value.strip()
	return request

