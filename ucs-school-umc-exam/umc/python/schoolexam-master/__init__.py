#!/usr/bin/python2.6
#
# UCS@School UMC module schoolexam-master
#  UMC module delivering backend services for ucs-school-umc-exam
#
# Copyright 2013 Univention GmbH
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

import notifier

from univention.management.console.modules import Base
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, sanitize

from univention.lib.i18n import Translation

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display
import ucsschool.lib.internetrules as internetrules

import univention.management.console.modules.distribution.util as distribution_util

import os
import tempfile
import shutil

_ = Translation( 'ucs-school-umc-exam-master' ).translate

class Instance( SchoolBaseModule ):
	def __init__( self ):
		SchoolBaseModule.__init__(self)

		self._containerExamUsers = ucr.get('ucsschool/ldap/default/container/exam', 'examusers')
		self._examUserPrefix = ucr.get('ucsschool/ldap/default/userprefix/exam', 'exam-')
		self._examGroupname = ucr.get('ucsschool/ldap/default/groupname/exam')	## default depends on search_base.school

		## cache objects
		self._udm_modules = []
		self._examGroup = None

	def init(self):
		SchoolBaseModule.init(self)

	@property
	def examGroup(self):
		if not self._examGroup:
			if not self._examGroupname:
				self._examGroupname = "%s-Klassenarbeit" % self._search_base.school
			## Determine examGroupDN
			examGroupDN = ldap_admin_write.searchDn('(&(cn=%s)(objectClass=univentionGroup))' % self._examGroupname, self._search_base.groups )
			if len(examGroupDN) != 1:
				message = 'Command failed\nGroup %s not found' % examGroupname
				MODULE.warn(message)
				self.finished(request.id, {}, message, success=False)
				return
			## Get the room object
			self._examGroup = module_groups_group.object(None, self._ldap_admin_write, self._ldap_position, examGroupDN)
		return self._examGroup

	@LDAP_Connection(ADMIN_WRITE)
	def create_exam_user(self, request, ldap_admin_write = None, ldap_position = None, search_base = None):
		## store the ldap related objects for calls to the examGroup property
		self._ldap_admin_write = ldap_admin_write
		self._ldap_position = ldap_position
		self._search_base = search_base

		### Origin uid
		username = request.options.get('username')
		if not username:
			message = 'Command failed\nNo username specified'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		## Convert the username into the object DN.
		udm_filter = '(username=%s)' % username
		objs = udm_modules.lookup( 'users/user', None, ldap_admin_write, filter = udm_filter, scope = 'sub', base = search_base.students, unique=1)
		if objs:
			user_orig = objs[0]
		else:
			message = 'Command failed\nUser %s not found' % username
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		### uid and DN of exam_user
		exam_user_uid = "".join( (self._examUserPrefix, username) )
		exam_user_container = "cn=%s,%s" % (self._containerExamUsers, search_base.schoolDN)
		exam_user_dn = "uid=%s,%s" % (exam_user_uid, exam_user_container)

		### Check if it's blacklisted
		prohibited_objects=univention.admin.handlers.settings.prohibited_username.lookup(None, ldap_admin_write, '')
		if prohibited_objects and len(prohibited_objects) > 0:
			for i in range(0,len(prohibited_objects)):
				if exam_user_uid in prohibited_objects[i]['usernames']:
					message = 'Command failed\nRequested exam user name %s is not allowed according to settings/prohibited_username object %s' % ( exam_user_uid, prohibited_objects[i]['name'])
					MODULE.warn(message)
					self.finished(request.id, {}, message, success=False)
					return

		### Allocate new uid
		alloc = []
		try:
			uid=univention.admin.allocators.request(ldap_admin_write, ldap_position, 'uid', value=exam_user_uid)
			alloc.append(('uid', uid))
		except univention.admin.uexceptions.noLock, e:
			univention.admin.allocators.release(ldap_admin_write, ldap_position, 'uid', exam_user_uid)
			raise univention.admin.uexceptions.uidAlreadyUsed, ': %s' % exam_user_uid

		### Ok, we have a valid target uid, so start cloning the user
		## deepcopy(user_orig) soes not help much, as we cannot use users.user.object.create()
		## because it currently cannot be convinced to preserve the password. So we do it manually:
		try: 
			## Allocate new uidNumber
			if 'posix' in user_orig.options:
				uidNum = univention.admin.allocators.request(ldap_admin_write, ldap_position, 'uidNumber')
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
						userSid=univention.admin.allocators.requestUserSid(ldap_admin_write, ldap_position, uidNum)
					except:
						pass
				if not userSid or userSid == 'None':
					num=uidNum
					while not userSid or userSid == 'None':
						num = str(int(num)+1)
						try:
							userSid=univention.admin.allocators.requestUserSid(ldap_admin_write, ldap_position, num)
						except univention.admin.uexceptions.noLock, e:
							num = str(int(num)+1)
					alloc.append(('sid', userSid))


			## Determine description attribute for exam_user
			exam_user_description = request.options.get('description')
			if not exam_user_description:
				exam_user_description = "Exam for user %s" % username

			## Now create the addlist, fixing up attributes as we go
			al=[]
			for (key, value) in user_orig.oldattr.items():
				if key == 'uid':
					value = [exam_user_uid]
				elif key == 'homeDirectory':
					value = ["/home/%s" % exam_user_uid]
				elif key == 'krb5PrincipalName':
					user_orig_krb5PrincipalName = value[0]
					value = ["%s%s" % (exam_user_uid, user_orig_krb5PrincipalName[user_orig_krb5PrincipalName.find("@"):])]
				elif key == 'uidNumber':
					value = [uidNum]
				elif key == 'sambaSID':
					value = [userSid]
				elif key == 'description':
					value = [exam_user_description]
					exam_user_description = None	## that's done
				al.append((key, value))

			if exam_user_description:
				al.append(('description', [exam_user_description]))

			## And create the exam_user
			ldap_admin_write.add(exam_user_dn, al)

		except Exception, err:
			for i, j in alloc:
				univention.admin.allocators.release(ldap_admin_write, ldap_position, i, j)

			message = 'ERROR: Command failed\n%s' % traceback.format_exc()
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		## Add exam_user to groups
		if 'groups/group' in self._udm_modules:
			module_groups_group = self._udm_modules['groups/group']
		else:
			module_groups_group = univention.admin.modules.get('groups/group')
			univention.admin.modules.init(ldap_admin_write, ldap_position, module_groups_group)
			self._udm_modules['groups/group'] = module_groups_group

		if 'posix' in user_orig.options:
			grpobj = module_groups_group.object(None, ldap_admin_write, ldap_position, user_orig['primaryGroup'])
			grpobj.fast_member_add( [ exam_user_dn ], [ exam_user_uid ] )

			for group in user_orig.info.get('groups', []):
				grpobj = module_groups_group.object(None, ldap_admin_write, ldap_position, group)
				grpobj.fast_member_add( [ exam_user_dn ], [ exam_user_uid ] )

		## Add exam_user to self._examGroupname
		self.examGroup.fast_member_add( [ exam_user_dn ], [ exam_user_uid ] )

		## finally confirm allocated IDs
		univention.admin.allocators.confirm(ldap_admin_write, ldap_position, 'uid', exam_user_uid)
		if 'samba' in user_orig.options:
			univention.admin.allocators.confirm(ldap_admin_write, ldap_position, 'sid', userSid)
		if 'posix' in user_orig.options:
			univention.admin.allocators.confirm(ldap_admin_write, ldap_position, 'uidNumber', uidNum)

		self.finished(request.id, {}, success=True)
		return

	@LDAP_Connection(ADMIN_WRITE)
	def remove_exam_user(self, request, ldap_admin_write = None, ldap_position = None, search_base = None):

		### get parameters
		username = request.options.get('username')
		if not username:
			message = 'Command failed\nNo username specified'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		### uid and DN of exam_user
		exam_user_uid = "".join( (self._examUserPrefix, username) )
		exam_user_container = "cn=%s,%s" % (self._containerExamUsers, search_base.schoolDN)
		exam_user_dn = "uid=%s,%s" % (exam_user_uid, exam_user_container)

		udm_filter = '(username=%s)' % username
		objs = udm_modules.lookup( 'users/user', None, ldap_admin_write, filter = udm_filter, scope = 'sub', base = search_base.students, unique=1)
		if objs:
			obj = objs[0]
			try:
				obj.remove()
			except univention.admin.uexceptions.ldapError, e:
				message = 'Could not remove exam user: %s' % e
				MODULE.warn(message)
				self.finished(request.id, {}, message, success=False)
				return
		else:
			message = 'User not found: %s' % username
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		self.finished(request.id, {}, success=True)
		return

	@LDAP_Connection(ADMIN_WRITE)
	def set_computerroom_exammode(self, request, ldap_admin_write = None, ldap_position = None, search_base = None):
		## store the ldap related objects for calls to the examGroup property
		self._ldap_admin_write = ldap_admin_write
		self._ldap_position = ldap_position
		self._search_base = search_base

		### get parameters
		roomname = request.options.get('room')
		if not roomname:
			message = 'Command failed\nNo room specified'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		### Try to open the room
		udm_filter = '(name=%s)' % roomname
		objs = udm_modules.lookup( 'groups/group', None, ldap_admin_write, filter = udm_filter, scope = 'sub', base = search_base.rooms, unique=1)
		if objs:
			obj = objs[0]
		else:
			message = 'Room not found: %s' % roomname
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		## Add all host members of room to self.examGroup
		hosts = [ univention.admin.uldap.explodeDn(host_dn, 1)[0] for host_dn in room['hosts'] ]
		self.examGroup.fast_member_add( room['hosts'], hosts )	## adds any uniqueMember and member listed if not already present

		self.finished(request.id, {}, success=True)
		return

	@LDAP_Connection(ADMIN_WRITE)
	def unset_computerroom_exammode(self, request, ldap_admin_write = None, ldap_position = None, search_base = None):
		## store the ldap related objects for calls to the examGroup property
		self._ldap_admin_write = ldap_admin_write
		self._ldap_position = ldap_position
		self._search_base = search_base

		### get parameters
		roomname = request.options.get('room')
		if not roomname:
			message = 'Command failed\nNo room specified'
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		### Try to open the room
		udm_filter = '(name=%s)' % roomname
		objs = udm_modules.lookup( 'groups/group', None, ldap_admin_write, filter = udm_filter, scope = 'sub', base = search_base.rooms, unique=1)
		if objs:
			obj = objs[0]
		else:
			message = 'Room not found: %s' % roomname
			MODULE.warn(message)
			self.finished(request.id, {}, message, success=False)
			return

		## Remove all host members of room from self.examGroup
		hosts = [ univention.admin.uldap.explodeDn(host_dn, 1)[0] for host_dn in room['hosts'] ]
		self.examGroup.fast_member_remove( room['hosts'], hosts )	## removes any uniqueMember and member listed if still present

		self.finished(request.id, {}, success=True)
		return

