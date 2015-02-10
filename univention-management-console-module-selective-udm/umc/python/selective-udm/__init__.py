#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: selective-udm
#
# Copyright 2012-2015 Univention GmbH
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

import threading
import traceback
import time
import notifier
import notifier.threads
import re
import string
import csv
import univention.info_tools as uit
from univention.lib.i18n import Translation
import univention.management.console.modules as umcm
import os
import copy
import locale
import ldap
import base64
import univention.config_registry
import univention.admin.config
import univention.admin.modules
import univention.admin.objects
import univention.admin.uldap
import univention.admin.handlers.users.user
import univention.admin.handlers.computers.windows

univention.admin.modules.update()

# update choices-lists which are defined in LDAP
univention.admin.syntax.update_choices()

from univention.management.console.log import MODULE
from univention.management.console.protocol.definitions import *
from univention.management.console.modules import UMC_CommandError
from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, SchoolSearchBase, SchoolBaseModule, ADMIN_WRITE, USER_READ

from univention.management.console.config import ucr

_ = Translation( 'univention-management-console-selective-udm' ).translate

class CreationDenied(Exception):
	pass

class Instance( SchoolBaseModule ):
	def __init__( self ):
		SchoolBaseModule.__init__(self)

	def init(self):
		SchoolBaseModule.init(self)

	def _check_usersid_join_permissions(self, lo, usersid):

		allowed_groups = ucr.get('ucsschool/windows/join/groups', 'Domain Admins').split(',')

		result  = lo.search('sambaSID=%s' %usersid, attr=['dn'])
		if not result:
			raise CreationDenied('SID %s was not found' % usersid)

		user_dn = result[0][0]
		MODULE.info("Found user with DN %s" % user_dn)

		result = lo.search('uniqueMember=%s' % user_dn, attr=['cn'])
		if not result:
			raise CreationDenied('No group memberships for SID %s found' % usersid)

		for dn,attr in result:
			if attr.get('cn', [])[0] in allowed_groups:
				return

		raise CreationDenied('SID %s is not member of one of the following groups: %s. The allowed groups can be modified by setting the UCR variable ucsschool/windows/join/groups.' % (usersid, allowed_groups))

	@LDAP_Connection(USER_READ, ADMIN_WRITE)
	def create_windows_computer(self, request, ldap_user_read = None, ldap_admin_write = None, ldap_position = None, search_base = None):

		self.required_options(request, 'name')

		if not search_base.school:
			raise UMC_CommandError( _('Could not determine schoolOU') )

		try:
			# Set new position
			ldap_position.setDn(search_base.computers)

			usersid = request.options.get('usersid')
			self._check_usersid_join_permissions(ldap_user_read, usersid)

			# Create the computer account
			computer = univention.admin.handlers.computers.windows.object(None, ldap_admin_write, position=ldap_position, superordinate=None)
			computer.open()
			name = request.options.get('name')
			if name[-1] == '$':
				# Samba 3 calls the name in this way
				name = name[:-1]

			# In Samba 3 the samba attributes must be set by Samba itself
			samba3_mode = request.options.get('samba3_mode')
			if samba3_mode and samba3_mode.lower() in ['true', 'yes']:
				computer.options=['posix']

			computer['name'] = name

			password = request.options.get('password')
			if password:
				decode_password = request.options.get('decode_password')
				if decode_password and decode_password.lower() in ['true', 'yes']:
					# the password is base64 encoded
					password = base64.decodestring(password)
					# decode from utf-16le
					password = password.decode('utf-16le')
					# and remove the quotes
					password = password.strip('"')
				computer['password'] = password

			computer['description'] = request.options.get('description')
			computer_dn = computer.create()

		except Exception, err:
			message = 'Failed to create windows computer\n%s' % traceback.format_exc()
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
		else:
			self.finished(request.id, {}, success=True)


