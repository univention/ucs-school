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
'''
UCS@School UMC module schoolexam-master
 UMC module delivering backend services for ucs-school-umc-exam
'''

from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_CommandError, UMC_OptionTypeError
from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, SchoolSearchBase, SchoolBaseModule, ADMIN_WRITE, USER_READ

import univention.admin.modules
univention.admin.modules.update()

import traceback

from univention.lib.i18n import Translation
_ = Translation( 'ucs-school-umc-exam-master' ).translate

class Instance( SchoolBaseModule ):
	def __init__( self ):
		SchoolBaseModule.__init__(self)

		self._examUserPrefix = ucr.get('ucsschool/ldap/default/userprefix/exam', 'exam-')

		## cache objects
		self._udm_modules = dict()
		self._examGroup = None
		self._examUserContainerDN = None
		
		## Context for @property examGroup
		self._ldap_user_read = None
		self._ldap_position = None
		self._search_base = None

	def init(self):
		SchoolBaseModule.init(self)
	@property
	def examGroup(self):
		'''fetch the examGroup object, create it if missing'''
		if not self._examGroup:
			if 'groups/group' in self._udm_modules:
				module_groups_group = self._udm_modules['groups/group']
			else:
				univention.admin.modules.init(self._ldap_admin_write, self._ldap_position, module_groups_group)
				self._udm_modules['groups/group'] = module_groups_group

			## Determine exam_group_dn
			try:
				ldap_filter = '(objectClass=univentionGroup)'
				exam_group_dn = self._ldap_admin_write.searchDn(ldap_filter, self._search_base.examGroup, scope='base')
				self._examGroup = module_groups_group.object(None, self._ldap_admin_write, self._ldap_position, self._search_base.examGroup)
				## self._examGroup.create() # currently not necessary
			except univention.admin.uexceptions.noObject:
				try:
					position = univention.admin.uldap.position(self._search_base._ldapBase)
					position.setDn(self._ldap_admin_write.parentDn(self._search_base.examGroup))
					self._examGroup = module_groups_group.object(None, self._ldap_admin_write, position, self._search_base.examGroup)
					self._examGroup.open()
					self._examGroup['name'] = self._search_base.examGroupName
					self._examGroup['sambaGroupType'] = self._examGroup.descriptions['sambaGroupType'].base_default[0]
					self._examGroup.create()
				except univention.admin.uexceptions.base, e:
					message = _('Failed to create exam group\n%s') % traceback.format_exc()
					raise UMC_CommandError( message )

		return self._examGroup

	@property
	def examUserContainerDN(self):
		'''lookup examUserContainerDN, create it if missing'''
		if not self._examUserContainerDN:
			try:
				ldap_filter = '(objectClass=organizationalRole)'
				exam_user_container_dn = self._ldap_admin_write.searchDn(ldap_filter, self._search_base.examUsers, scope='base')
			except univention.admin.uexceptions.noObject:
				try:
					module_containers_cn = univention.admin.modules.get('container/cn')
					univention.admin.modules.init(self._ldap_admin_write, self._ldap_position, module_containers_cn)
					position = univention.admin.uldap.position(self._search_base._ldapBase)
					position.setDn(self._ldap_admin_write.parentDn(self._search_base.examUsers))
					exam_user_container = module_containers_cn.object(None, self._ldap_admin_write, position, self._search_base.examUsers)
					exam_user_container.open()
					exam_user_container['name'] = self._search_base._examUserContainerName
					exam_user_container.create()
				except univention.admin.uexceptions.base, e:
					message = _('Failed to create exam container\n%s') % traceback.format_exc()
					raise UMC_CommandError( message )

			self._examUserContainerDN = self._search_base.examUsers

		return self._examUserContainerDN

	@LDAP_Connection(USER_READ, ADMIN_WRITE)
	def create_exam_user(self, request, ldap_user_read = None, ldap_admin_write = None, ldap_position = None, search_base = None):
		'''Create an exam account cloned from a given user account.
		   The exam account is added to a special exam group to allow GPOs and other restrictions
		   to be enforced via the name of this group.
		   The group has to be created earlier, e.g. by create_ou (ucs-school-import).'''

		### Origin user
		self.required_options(request, 'userdn')
		userdn = request.options.get('userdn')

		### get search base for OU of given user dn
		school = SchoolSearchBase.getOU(userdn)
		if not school:
			raise UMC_CommandError( _('User is not below a school OU: %s') % userdn )
		search_base = SchoolSearchBase(search_base.availableSchools, school)

		## store the ldap related objects for calls to the examGroup property
		self._ldap_admin_write = ldap_admin_write
		self._ldap_position = ldap_position
		self._search_base = search_base

		## Try to open the object
		if 'users/user' in self._udm_modules:
			module_users_user = self._udm_modules['users/user']
		else:
			module_users_user = univention.admin.modules.get('users/user')
			univention.admin.modules.init(ldap_admin_write, ldap_position, module_users_user)
			self._udm_modules['users/user'] = module_users_user

		try:
			user_orig = module_users_user.object(None, ldap_admin_write, ldap_position, userdn)
			user_orig.open()
		except univention.admin.uexceptions.ldapError, e:
			raise UMC_OptionTypeError( _('Invalid username (%s)') % userdn )

		### uid and DN of exam_user
		exam_user_uid = "".join( (self._examUserPrefix, user_orig['username']) )
		exam_user_dn = "uid=%s,%s" % (exam_user_uid, self.examUserContainerDN)

		### Check if it's blacklisted
		prohibited_objects = univention.admin.handlers.settings.prohibited_username.lookup(None, ldap_admin_write, '')
		if prohibited_objects and len(prohibited_objects) > 0:
			for i in range(0, len(prohibited_objects)):
				if exam_user_uid in prohibited_objects[i]['usernames']:
					message = _('Requested exam username %s is not allowed according to settings/prohibited_username object %s') % ( exam_user_uid, prohibited_objects[i]['name'])
					raise UMC_CommandError( message )

		### Allocate new uid
		alloc = []
		try:
			uid = univention.admin.allocators.request(ldap_admin_write, ldap_position, 'uid', value=exam_user_uid)
			alloc.append(('uid', uid))
		except univention.admin.uexceptions.noLock, e:
			univention.admin.allocators.release(ldap_admin_write, ldap_position, 'uid', exam_user_uid)
			MODULE.warn( _('The exam account does already exist for: %s') % exam_user_uid )
			self.finished(request.id, dict(
				success=True,
				userdn=userdn,
				examuserdn=exam_user_dn,
			), success=True)
			return


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
					userSid = 'S-1-4-%s' % uidNum
				else:
					try:
						userSid = univention.admin.allocators.requestUserSid(ldap_admin_write, ldap_position, uidNum)
					except:
						message = _('Failed to allocate userSid\n%s') % traceback.format_exc()
						raise UMC_CommandError( message )
				if not userSid or userSid == 'None':
					num = uidNum
					while not userSid or userSid == 'None':
						num = str(int(num)+1)
						try:
							userSid = univention.admin.allocators.requestUserSid(ldap_admin_write, ldap_position, num)
						except univention.admin.uexceptions.noLock, e:
							num = str(int(num)+1)
					alloc.append(('sid', userSid))


			## Determine description attribute for exam_user
			exam_user_description = request.options.get('description')
			if not exam_user_description:
				exam_user_description = _('Exam for user %s') % user_orig['username']

			## Now create the addlist, fixing up attributes as we go
			al = []
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

			message = _('ERROR: Creation of exam user account failed\n%s') % traceback.format_exc()
			raise UMC_CommandError( message )

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

		## Add exam_user to examGroup
		self.examGroup.fast_member_add( [ exam_user_dn ], [ exam_user_uid ] )

		## finally confirm allocated IDs
		univention.admin.allocators.confirm(ldap_admin_write, ldap_position, 'uid', exam_user_uid)
		if 'samba' in user_orig.options:
			univention.admin.allocators.confirm(ldap_admin_write, ldap_position, 'sid', userSid)
		if 'posix' in user_orig.options:
			univention.admin.allocators.confirm(ldap_admin_write, ldap_position, 'uidNumber', uidNum)

		self.finished(request.id, dict(
			success=True,
			userdn=userdn,
			examuserdn=exam_user_dn,
		), success=True)

	@LDAP_Connection(USER_READ, ADMIN_WRITE)
	def remove_exam_user(self, request, ldap_user_read = None, ldap_admin_write = None, ldap_position = None, search_base = None):
		'''Remove an exam account cloned from a given user account.
		   The exam account is removed from the special exam group.'''

		### Origin user
		self.required_options(request, 'userdn')
		userdn = request.options.get('userdn')

		### get search base for OU of given user dn
		school = SchoolSearchBase.getOU(userdn)
		if not school:
			raise UMC_CommandError( _('User is not below a school OU: %s') % userdn )
		search_base = SchoolSearchBase(search_base.availableSchools, school)

		### uid and DN of exam_user
		exam_user_uid = univention.admin.uldap.explodeDn(userdn, 1)[0]

		### open the users module
		if 'users/user' in self._udm_modules:
			module_users_user = self._udm_modules['users/user']
		else:
			module_users_user = univention.admin.modules.get('users/user')
			univention.admin.modules.init(ldap_admin_write, ldap_position, module_users_user)
			self._udm_modules['users/user'] = module_users_user

		### try to remove object
		try:
			user_orig = module_users_user.object(None, ldap_admin_write, ldap_position, userdn)
			user_orig.remove()
		except univention.admin.uexceptions.ldapError, e:
			message = _('Could not remove exam user: %s') % e
			raise UMC_CommandError( message )

		self.finished(request.id, {}, success=True)
		return

	@LDAP_Connection(USER_READ, ADMIN_WRITE)
	def set_computerroom_exammode(self, request, ldap_user_read = None, ldap_admin_write = None, ldap_position = None, search_base = None):
		'''Add all member hosts of a given computer room to the special exam group.'''

		### get parameters
		self.required_options(request, 'roomdn')
		roomdn = request.options.get('roomdn')

		### get search base for OU of given room DN
		school = SchoolSearchBase.getOU(roomdn)
		if not school:
			raise UMC_CommandError( _('Room is not below a school OU: %s') % userdn )
		search_base = SchoolSearchBase(search_base.availableSchools, school)

		## store the ldap related objects for calls to the examGroup property
		self._ldap_admin_write = ldap_admin_write
		self._ldap_position = ldap_position
		self._search_base = search_base

		### Try to open the room
		if 'groups/group' in self._udm_modules:
			module_groups_group = self._udm_modules['groups/group']
		else:
			module_groups_group = univention.admin.modules.get('groups/group')
			univention.admin.modules.init(ldap_admin_write, ldap_position, module_groups_group)
			self._udm_modules['groups/group'] = module_groups_group

		try:
			room = module_groups_group.object(None, ldap_admin_write, ldap_position, roomdn)
			room.open()
		except univention.admin.uexceptions.ldapError, e:
			raise UMC_OptionTypeError( _('Invalid Room DN') )

		## Add all host members of room to examGroup
		examGroup = self.examGroup
		if examGroup:
			host_uid_list = [ univention.admin.uldap.explodeDn(uniqueMember, 1)[0] for uniqueMember in room['hosts'] ]
			examGroup.fast_member_add( room['hosts'], host_uid_list )	## adds any uniqueMember and member listed if not already present
		else:
			return ## self.examGroup called finished in this case, so just return

		self.finished(request.id, {}, success=True)
		return

	@LDAP_Connection(USER_READ, ADMIN_WRITE)
	def unset_computerroom_exammode(self, request, ldap_user_read = None, ldap_admin_write = None, ldap_position = None, search_base = None):
		'''Remove all member hosts of a given computer room from the special exam group.'''

		### get parameters
		self.required_options(request, 'roomdn')
		roomdn = request.options.get('roomdn')

		### get search base for OU of given room DN
		school = SchoolSearchBase.getOU(roomdn)
		if not school:
			raise UMC_CommandError( _('Room is not below a school OU: %s') % userdn )
		search_base = SchoolSearchBase(search_base.availableSchools, school)

		## store the ldap related objects for calls to the examGroup property
		self._ldap_admin_write = ldap_admin_write
		self._ldap_position = ldap_position
		self._search_base = search_base

		### Try to open the room
		if 'groups/group' in self._udm_modules:
			module_groups_group = self._udm_modules['groups/group']
		else:
			module_groups_group = univention.admin.modules.get('groups/group')
			univention.admin.modules.init(ldap_admin_write, ldap_position, module_groups_group)
			self._udm_modules['groups/group'] = module_groups_group

		try:
			room = module_groups_group.object(None, ldap_admin_write, ldap_position, roomdn)
			room.open()
		except univention.admin.uexceptions.ldapError, e:
			raise UMC_OptionTypeError( 'Invalid Room DN' )

		## Remove all host members of room from examGroup
		examGroup = self.examGroup
		if examGroup:
			host_uid_list = [ univention.admin.uldap.explodeDn(uniqueMember, 1)[0] for uniqueMember in room['hosts'] ]
			examGroup.fast_member_remove( room['hosts'], host_uid_list )	## removes any uniqueMember and member listed if still present

		self.finished(request.id, {}, success=True)
		return

