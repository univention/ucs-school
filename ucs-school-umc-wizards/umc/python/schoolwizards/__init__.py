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

			if self._username_used(request.options['username'], ldap_user_read):
				raise ValueError(_('Username is already in use'))
			if request.options.get('mailPrimaryAddress', ''):
				if self._mail_address_used(request.options['mailPrimaryAddress'], ldap_user_read):
					raise ValueError(_('Mail address is already in use'))

			isTeacher = False
			isStaff = False
			if request.options['type'] in ['student', 'teacher', 'staff', 'teachersAndStaff']:
				# The class name is only required if the user is a student
				if request.options['type'] == 'student':
					self.required_options(request, 'class')
					self.required_values(request, 'class')
			else:
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
			                 request.options.get('class', ''),
			                 request.options.get('mailPrimaryAddress', ''),
			                 isTeacher,
			                 isStaff,
			                 request.options.get('password', ''))
		except (ValueError, IOError, OSError), err:
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
			self.required_options(request, 'name')
			self.required_values(request, 'name')

			if self._school_name_used(request.options['name'], ldap_user_read, search_base):
				raise ValueError(_('School name is already in use'))

			# Create the school
			self.create_ou(request.options['name'], request.options.get('schooldc', ''))
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

			if not self._school_name_used(request.options['school'], ldap_user_read, search_base):
				raise ValueError(_('Unknown school'))

			if self._class_name_used(request.options['school'], request.options['name'],
			                         ldap_user_read, search_base):
				raise ValueError(_('Class name is already in use'))

			# Create the school
			self.import_group(request.options['school'],
			                  request.options['name'],
			                  request.options.get('description', ''))
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

			if not self._school_name_used(request.options['school'], ldap_user_read, search_base):
				raise ValueError(_('Unknown school'))

			name = udm_syntax.hostName.parse(request.options['name'])
			if self._computer_name_used(name, ldap_user_read):
				raise ValueError(_('Computer name is already in use'))

			mac = udm_syntax.MAC_Address.parse(request.options['mac'])
			if self._mac_address_used(mac, ldap_user_read):
				raise ValueError(_('MAC address is already in use'))
			ip_address = udm_syntax.ipv4Address.parse(request.options['ipAddress'])
			subnet_mask = request.options.get('subnetMask', '')
			if subnet_mask:
				subnet_mask = udm_syntax.netmask.parse(request.options.get('subnetMask', ''))

			if request.options['type'] not in ['ipmanagedclient', 'windows']:
				raise ValueError(_('Invalid value for  \'type\' property'))

			# Create the computer
			self.import_computer(request.options['type'],
			                     name,
			                     mac,
			                     request.options['school'],
			                     ip_address,
			                     subnet_mask,
			                     request.options.get('inventoryNumber', ''))
		except (ValueError, IOError, OSError, valueError), err:
			MODULE.info(str(err))
			result = {'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('Computer successfully created'))
