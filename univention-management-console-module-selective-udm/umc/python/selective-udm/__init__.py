#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: selective-udm
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

class Instance(umcm.Base):

	def create_windows_computer(self, request):
		lo, con_position = univention.admin.uldap.getAdminConnection()
		co = univention.admin.config.config()

		# Convert the username into a DN. We need the position of the server DN
		# to get the OU
		server_dn = lo.searchDn('(&(uid=%s)(objectClass=posixAccount))' % self._username )
		if len(server_dn) != 1:
			message = 'Failed to create windows computer\nDid not find the Server DN'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return
		server_dn = server_dn[0]
			
		# Search for the default computer container in this OU
		server_dn_list = ldap.explode_dn(server_dn)
		idx=None
		for i in range(1,len(server_dn_list)):
			if server_dn_list[i].lower().startswith('ou='):
				idx=i
				break
		if not idx:
			messages = 'Failed to create windows computer\nDid not find the ou in the Server DN'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return
		position = 'cn=computers,%s' % string.join(server_dn_list[idx:], ',')

		try:
			# Set new positinion
			con_position.setDn(position)
		
			# Create the computer account
			computer = univention.admin.handlers.computers.windows.object(co, lo, position=con_position, superordinate=None)
			computer.open()
			name = request.options.get('name')
			if name[-1] == '$':
				# Samba 3 calls the name in this way
				name = name[:-1]
				computer.options=['posix']
			computer['name'] = name
			# Get password hashes
			unicodePwd = request.options.get('unicodePwd')
			if unicodePwd:
				# the password is base64 encoded
				unicodePwd = base64.decodestring(unicodePwd)
				unicodePwd = unicodePwd.decode('utf-16le')
				computer['password'] = unicodePwd
			computer['description'] = request.options.get('description')
			computer_dn = computer.create()

		except Exception, err:
			message = 'Failed to create windows computer\n%s' % traceback.format_exc()
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
		else:
			self.finished(request.id, {}, success=True)


