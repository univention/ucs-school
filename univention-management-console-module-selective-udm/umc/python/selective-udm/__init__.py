#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: selective-udm
#
# Copyright 2012-2013 Univention GmbH
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
			message = 'Failed to create windows computer\nDid not find the ou in the Server DN'
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


	def clone_user_account(self, request):
		lo, con_position = univention.admin.uldap.getAdminConnection()
		co = univention.admin.config.config()

		# Convert the username into a DN. We need the position of the server DN
		# to get the OU
		server_dn = lo.searchDn('(&(uid=%s)(objectClass=posixAccount))' % self._username )
		if len(server_dn) != 1:
			message = 'Command failed\nDid not find the Server DN'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return
		server_dn = server_dn[0]
			
		## Search for the OU container
		server_dn_list = ldap.explode_dn(server_dn)
		idx=None
		for i in range(1,len(server_dn_list)):
			if server_dn_list[i].lower().startswith('ou='):
				idx=i
				break
		if not idx:
			message = 'Command failed\nDid not find the ou in the Server DN'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		#### Validate the client specified parameters
		### Target container
		clone_user_container = request.options.get('container')
		if not clone_user_container:
			clone_user_container = 'cn=users,cn=temp,%s' % string.join(server_dn_list[idx:], ',')
		try:
			lo.searchDn(base=clone_user_container, scope='base')
		except Exception, err:
			message = 'Command failed\nTarget container does not exists: %s' % clone_user_container
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return
		
		### Origin uid
		username = request.options.get('username')
		if not username:
			message = 'Command failed\nNo username specified'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		## Convert the username into the object DN.
		user_orig_dn = lo.searchDn('(&(uid=%s)(objectClass=posixAccount))' % username )
		if len(user_orig_dn) != 1:
			message = 'Command failed\nUser %s not found' % username
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		### Target uid
		user_clone_uid = request.options.get('clonename')
		if not user_clone_uid:
			message = 'Command failed\nNo clonename specified'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		prohibited_objects=univention.admin.handlers.settings.prohibited_username.lookup(co, lo, '')
		if prohibited_objects and len(prohibited_objects) > 0:
			for i in range(0,len(prohibited_objects)):
				if user_clone_uid in prohibited_objects[i]['usernames']:
					message = 'Command failed\nRequested clonename is not allowed according to settings/prohibited_username object %s' % prohibited_objects[i]['name']
					MODULE.warn(message)
					self.finished(request.id, {}, message, success=False)
					return

		### Get user_orig attributes
		module_users_user = univention.admin.modules.get('users/user')
		univention.admin.modules.init(lo, con_position, module_users_user)
		user_orig = univention.admin.objects.get(module_users_user, co, lo, position=con_position, dn=user_orig_dn[0])

		### Determine new DN
		user_clone_position = univention.admin.uldap.position(user_orig.lo.base)
		user_clone_position.setDn(clone_user_container)
		user_clone_dn = "uid=%s,%s" % (user_clone_uid, user_clone_position.getDn())

		### Allocate new uid
		alloc = []
		try:
			uid=univention.admin.allocators.request(lo, con_position, 'uid', value=user_clone_uid)
			alloc.append(('uid', uid))
		except univention.admin.uexceptions.noLock, e:
			univention.admin.allocators.release(lo, con_position, 'uid', user_clone_uid)
			raise univention.admin.uexceptions.uidAlreadyUsed, ': %s' % user_clone_uid

		### Ok, we have a valid target uid, so start cloning the user
		## deepcopy(user_orig) soes not help much, as we cannot use users.user.object.create()
		## because it currently cannot be convinced to preserve the password. So we do it manually:
		try: 
			## Allocate new uidNumber
			if 'posix' in user_orig.options:
				uidNum = univention.admin.allocators.request(lo, con_position, 'uidNumber')
				alloc.append(('uidNumber', uidNum))

			## Allocate new sambaSID
			if 'samba' in user_orig.options:
				## code copied from users.user.object.__generate_user_sid:
				if user_orig.s4connector_present:
					# In this case Samba 4 must create the SID, the s4 connector will sync the
					# new sambaSID back from Samba 4.
					userSid='S-1-4-%s' % uidNum
				else:
					try:
						userSid=univention.admin.allocators.requestUserSid(lo, con_position, uidNum)
					except:
						pass
				if not userSid or userSid == 'None':
					num=uidNum
					while not userSid or userSid == 'None':
						num = str(int(num)+1)
						try:
							userSid=univention.admin.allocators.requestUserSid(lo, con_position, num)
						except univention.admin.uexceptions.noLock, e:
							num = str(int(num)+1)
					alloc.append(('sid', userSid))


			## Now create the addlist, fixing up attributes as we go
			new_description = "Exam user for %s" % user_orig.oldattr['uid']
			al=[]
			for (key, value) in user_orig.oldattr.items():
				if key == 'uid':
					value = [user_clone_uid]
				elif key == 'homeDirectory':
					value = ["/home/%s" % user_clone_uid]
				elif key == 'krb5PrincipalName':
					user_orig_krb5PrincipalName = value[0]
					value = ["%s%s" % (user_clone_uid, user_orig_krb5PrincipalName[user_orig_krb5PrincipalName.find("@"):])]
				elif key == 'uidNumber':
					value = [uidNum]
				elif key == 'sambaSID':
					value = [userSid]
				elif key == 'description':
					value = [new_description]
					new_description = None	## that's done
				al.append((key, value))

			if new_description:
				al.append(('description', [new_description]))

			## And create the clone
			lo.add(user_clone_dn, al)

		except Exception, err:
			for i, j in alloc:
				univention.admin.allocators.release(lo, con_position, i, j)

			message = 'ERROR: Command failed\n%s' % traceback.format_exc()
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		## Add user_clone to groups
		if 'posix' in user_orig.options:
			## Now simply open the original user object to load the groups
			user_orig.open()
			module_groups_group = univention.admin.modules.get('groups/group')
			grpobj = module_groups_group.object(None, lo, con_position, user_orig['primaryGroup'])
			grpobj.fast_member_add( [ user_clone_dn ], [ user_clone_uid ] )

			for group in user_orig.info.get('groups', []):
				grpobj = module_groups_group.object(None, lo, con_position, group)
				grpobj.fast_member_add( [ user_clone_dn ], [ user_clone_uid ] )

		## finally confirm allocated IDs
		univention.admin.allocators.confirm(lo, con_position, 'uid', user_clone_uid)
		if 'samba' in user_orig.options:
			univention.admin.allocators.confirm(lo, con_position, 'sid', userSid)
		if 'posix' in user_orig.options:
			univention.admin.allocators.confirm(lo, con_position, 'uidNumber', uidNum)

		self.finished(request.id, {}, success=True)
		return
