#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Administration of groups
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

import traceback
import re
import os

from univention.lib.i18n import Translation

from univention.management.console.config import ucr
from univention.management.console.modules import UMC_OptionTypeError, UMC_CommandError
from univention.management.console.log import MODULE

import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects
import univention.admin.uexceptions as udm_exceptions
import univention.admin.uldap as udm_uldap

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display, USER_READ, USER_WRITE, MACHINE_WRITE
from ucsschool.lib.models import User

_ = Translation( 'ucs-school-umc-groups' ).translate

##### BEGIN: copied (with minor adaptations) from ucs-school-import #####
district_enabled = ucr.is_true('ucsschool/ldap/district/enable')

def extract_district (schoolNr):
	try:
		return schoolNr[:2]
	except IndexError:
		# TODO: add more debug output
		MODULE.error('ERROR: Unable to extract district from school number: %s' % schoolNr +
				'\n\tIf you do not use the district model deactivate UCR variable ucsschool/ldap/district/enable')

def getDN (schoolNr, base='school', basedn=ucr.get('ldap/base')):
	"""
	@param	base Values are either school, district or base
	@return	According to the base a specific part of dn is returned.
			Let's suppose the following school dn:
			ou=SCHOOL,ou=DISTRICT,dc=BASE,dc=DN

			The following is returned
			'base'		-> dc=BASE,dc=DN
			'district'	-> ou=DISTRICT,dc=BASE,dc=DN
			'school'	-> ou=SCHOOL,ou=DISTRICT,dc=BASE,dc=DN
	"""
	dn = '%(school)s%(district)s%(basedn)s'
	values = {'school':'ou=%s,'%schoolNr, 'district':'', 'basedn':basedn}
	if district_enabled:
		district = extract_district (schoolNr)
		if not district:
			raise RuntimeError("ERROR: Unable to continue without district number. School number: %s" % schoolNr)
		values['district'] = 'ou=%s,' % district
	if base == 'district':
		values['school'] = ''
	elif base == 'base':
		values['district'] = ''
		values['school'] = ''
	return dn % values
##### END: copied part #####

class Instance( SchoolBaseModule ):
	@LDAP_Connection()
	def users( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		# parse group parameter
		group = request.options.get('group')
		user_type = None
		if not group or group == 'None':
			group = None
		elif group.lower() in ( 'teacher', 'student' ):
			user_type = group.lower()
			group = None

		result = [ {
			'id': i.dn,
			'label': Display.user(i)
		} for i in self._users( ldap_user_read, search_base, group = group, user_type = user_type, pattern = request.options.get('pattern') ) ]
		self.finished( request.id, result )

	@LDAP_Connection()
	def query( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Searches for entries:

		requests.options = {}
		  'pattern' -- search pattern (default: '')
		  'school' -- particular school name as internal base for the search parameters
		  		  (default: automatically chosen search base in LDAP_Connection)

		return: [ { '$dn$' : <LDAP DN>, 'name': '...', 'description': '...' }, ... ]
		"""
		MODULE.info( 'schoolgroups.query: options: %s' % str( request.options ) )

		# get the correct base for the search
		base = search_base.classes
		if request.flavor in ( 'workgroup', 'workgroup-admin' ):
			# only show workgroups
			base = search_base.workgroups

		ldapFilter = LDAP_Filter.forAll(request.options.get('pattern', ''), ['name', 'description'])
		groupresult = udm_modules.lookup( 'groups/group', None, ldap_user_read, scope = 'one', base = base, filter = ldapFilter)

		name_pattern = re.compile('^%s-' % (re.escape(search_base.school)), flags=re.I)
		self.finished( request.id, map( lambda grp: { '$dn$' : grp.dn, 'name' : name_pattern.sub('', grp['name']), 'description' : grp[ 'description' ] }, groupresult ) )

	@LDAP_Connection()
	def get( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Returns the objects for the given IDs

		requests.options = [ <DN> ]

		return: { '$dn$' : <unique identifier>, 'name' : <display name> }
		"""
		MODULE.info( 'schoolgroups.get: options: %s' % str( request.options ) )

		grp = udm_objects.get( udm_modules.get( 'groups/group' ), None, ldap_user_read, ldap_position, request.options[ 0 ] )
		if not grp:
			raise UMC_OptionTypeError( 'unknown group object' )

		grp.open()
		result = {}
		result[ '$dn$' ] = grp.dn
		school = result[ 'school' ] = SchoolSearchBase.getOU(grp.dn)
		name_pattern = re.compile('^%s-' % (re.escape(result['school'])), flags=re.I)
		result[ 'name' ] = name_pattern.sub('', grp['name'])
		result[ 'description' ] = grp[ 'description' ]

		if request.flavor == 'class':
			# members are teachers
			memberDNs = [usr for usr in grp['users'] if User.is_teacher(school, usr)]
		elif request.flavor == 'workgroup-admin':
			memberDNs = grp['users']
		else:
			memberDNs = [usr for usr in grp['users'] if User.is_student(school, usr)]

		# read members:
		user_mod = udm_modules.get( 'users/user' )
		members = []
		for member_dn in memberDNs:
			user = udm_objects.get( user_mod, None, ldap_user_read, ldap_position, member_dn )
			if not user:
				continue
			try:
				user.open()
			except udm_exceptions.base as exc:
				MODULE.error('Failed to open user object %s: %s' % (member_dn, exc,))
				continue
			members.append( { 'id' : user.dn, 'label' : Display.user( user ) } )
		result[ 'members' ] = members

		self.finished( request.id, [ result, ] )

	@LDAP_Connection( USER_READ, MACHINE_WRITE )
	def put( self, request, search_base = None, ldap_machine_write = None, ldap_user_read = None, ldap_position = None ):
		"""Returns the objects for the given IDs

		requests.options = [ { object : ..., options : ... }, ... ]

		return: True|<error message>
		"""
		if not request.options:
			raise UMC_CommandError( 'Invalid arguments' )

		group = request.options[ 0 ].get( 'object', {} )
		try:
			grp = udm_objects.get( udm_modules.get( 'groups/group' ), None, ldap_machine_write, ldap_position, group[ '$dn$' ] )
			if not grp:
				raise UMC_OptionTypeError( 'unknown group object' )

			grp.open()
			MODULE.info('Modifying group "%s" with members: %s' % (grp.dn, grp['users']))
			MODULE.info('New members: %s' % group['members'])
			school = SchoolSearchBase.getOU(grp.dn)
			if request.flavor == 'class':
				# class -> update only the group's teachers (keep all non teachers)
				grp[ 'users' ] = [usr for usr in grp['users'] if not User.is_teacher(school, usr)] + [usr for usr in group['members'] if User.is_teacher(school, usr)]
			elif request.flavor == 'workgroup-admin':
				# workgroup (admin view) -> update teachers and students
				grp[ 'users' ] = group[ 'members' ]
				grp[ 'description' ] = group[ 'description' ]
				# do not allow groups to renamed in order to avoid conflicts with shares
				#grp[ 'name' ] = '%(school)s-%(name)s' % group
			elif request.flavor == 'workgroup':
				# workgroup (teacher view) -> update only the group's students
				user_diff = set(group['members']) - set(grp['users'])
				if any(User.is_teacher(school, dn) for dn in user_diff):
					raise UMC_CommandError( 'Adding teachers is not allowed' )
				grp[ 'users' ] = [usr for usr in grp['users'] if not User.is_student(school, usr)] + [usr for usr in group['members'] if User.is_student(school, usr)]

			grp.modify()
			MODULE.info('Modified, group has now members: %s' % grp['users'])
		except udm_exceptions.base, e:
			MODULE.process('An error occurred while modifying "%s": %s' % (group['$dn$'], e.message))
			raise UMC_CommandError( _('Failed to modify group (%s).') % e.message )

		self.finished( request.id, True )

	def _remove_group_share( self, groupName, ldap_connection, search_base):
		# check whether a share with the same name already exists
		MODULE.info('Seek for shares within: %s' % search_base.shares)
		results = udm_modules.lookup('shares/share', None, ldap_connection,
				scope = 'sub', base = search_base.shares,
				filter = 'cn=%s' % groupName)
		for ishare in results:
			try:
				MODULE.info('Removing share: %s' % ishare.dn)
				ishare.open()
				ishare.remove()
			except udm_exceptions.base, e:
				MODULE.error('Failed to remove share: %s' % e)
		if not results:
			MODULE.info('No share could be associated with the group "%s", searchBase=%s' % (groupName, search_base.schoolDN))

	def _add_group_share( self, groupName, groupDN, ldap_connection, search_base ):
		shareDN = 'cn=%s,%s' % (groupName, search_base.shares)

		# check whether a share with the same name already exists
		results = udm_modules.lookup('share/share', None, ldap_connection,
				scope = 'sub', base = search_base.schoolDN,
				filter = 'cn=%s' % groupName)
		if results:
			MODULE.info('share for workgroup "%s" already exists: %s' % (groupName, results[0].dn))
			return

		# share does not exists -> create a new one
		MODULE.info('creating new share for workgroup "%s": %s' % (groupName, shareDN))

		# get gid form corresponding group
		gid = 0
		groupModule = udm_modules.get('groups/group')
		groupObj = groupModule.object(None, ldap_connection, None, groupDN)
		groupObj.open()
		gid = groupObj['gidNumber']
		MODULE.info('using gid=%s' % gid)

		# get default fileserver
		# if UCR variable is set, use that value instead of building the serverFQDN manually
		serverFQDN = ucr.get('ucsschool/ldap/groups/fileserver', "%s.%s" % (ucr.get('hostname', ''), ucr.get('domainname', '')))

		##### BEGIN: copied (with minor adaptations) from ucs-school-import #####
		# get alternative server (defined at ou object if a dc slave is responsible for more than one ou)
		lo = ldap_connection
		domainname = ucr.get('domainname')
		ou_attr_LDAPAccessWrite = lo.get(search_base.schoolDN,['univentionLDAPAccessWrite'])
		alternativeServer_dn = None
		if len(ou_attr_LDAPAccessWrite) > 0:
			alternativeServer_dn = ou_attr_LDAPAccessWrite["univentionLDAPAccessWrite"][0]
			if len(ou_attr_LDAPAccessWrite) > 1:
				MODULE.warn("WARNING: more than one corresponding univentionLDAPAccessWrite found at ou=%s" % search_base.school)

		# build fqdn of alternative server and set serverFQDN
		if alternativeServer_dn:
			alternativeServer_attr = lo.get(alternativeServer_dn,['uid'])
			if len(alternativeServer_attr) > 0:
				alternativeServer_uid = alternativeServer_attr['uid'][0]
				alternativeServer_uid = alternativeServer_uid.replace('$','')
				if len(alternativeServer_uid) > 0:
					serverFQDN = "%s.%s" % (alternativeServer_uid, domainname)

		# fetch serverFQDN from OU
		result = lo.get(getDN (search_base.school, basedn=ucr.get('ldap/base')), ['ucsschoolClassShareFileServer'])
		if result:
			serverDomainName = lo.get(result['ucsschoolClassShareFileServer'][0], ['associatedDomain'])
			if serverDomainName:
				serverDomainName = serverDomainName['associatedDomain'][0]
			else:
				serverDomainName = domainname
			result = lo.get(result['ucsschoolClassShareFileServer'][0], ['cn'])
			if result:
				serverFQDN = "%s.%s" % (result['cn'][0], serverDomainName)
		##### END: copied part #####

		shareModule = udm_modules.get('shares/share')
		position = udm_uldap.position(ucr.get('ldap/base'))
		position.setDn(search_base.shares)
		shareObj = shareModule.object(None, ldap_connection, position)
		shareObj.open()
		shareObj["name"] = "%s" % groupName
		shareObj["host"] = serverFQDN
		if ucr.is_true('ucsschool/import/roleshare', True):
			shareObj["path"] = "/home/" + os.path.join(search_base.school, "groups/%s" % (groupName,))
		else:
			shareObj["path"] = "/home/groups/%s" % (groupName,)
		shareObj["writeable"] = "1"
		shareObj["sambaWriteable"] = "1"
		shareObj["sambaBrowseable"] = "1"
		shareObj["sambaForceGroup"] = "+%s" % groupName
		shareObj["sambaCreateMode"] = "0770"
		shareObj["sambaDirectoryMode"] = "0770"
		shareObj["owner"] = "0"
		shareObj["group"] = gid
		shareObj["directorymode"] = "0770"

		try:
			shareObj.create()
		except udm_exceptions.objectExists:
			MODULE.warn('Tried to create share, but share already exists: %s' % shareDN)
		except udm_exceptions.base:
			strTraceback = traceback.format_exc()
			MODULE.error('Failed to create share: %s\nTRACEBACK:%s' % (shareDN, strTraceback))

	@LDAP_Connection( USER_READ, USER_WRITE )
	def add( self, request, search_base = None, ldap_user_write = None, ldap_user_read = None, ldap_position = None ):
		"""Returns the objects for the given IDs

		requests.options = [ { $dn$ : ..., }, ... ]

		return: True|<error message>
		"""
		if not request.options:
			raise UMC_CommandError( 'Invalid arguments' )

		if request.flavor != 'workgroup-admin':
			raise UMC_CommandError( 'not supported' )
		group = request.options[ 0 ].get( 'object', {} )
		search_base = SchoolSearchBase( search_base.availableSchools, group[ 'school' ] )
		ldap_position.setDn( search_base.workgroups )
		try:
			# create group
			grp = udm_modules.get( 'groups/group' ).object( None, ldap_user_write, ldap_position )
			grp.open()

			grp[ 'name' ] = '%(school)s-%(name)s' % group
			grp[ 'description' ] = group[ 'description' ]
			grp[ 'users' ] = group[ 'members' ]

			dn = grp.create()

			# create corresponding share object
			self._add_group_share(grp['name'], dn, ldap_user_write, search_base)
		except udm_exceptions.base, e:
			MODULE.process('An error occurred while creating the group "%s": %s' % (group['name'], e.message))
			raise UMC_CommandError( _('Failed to create group (%s).') % e.message )

		self.finished( request.id, True )

	@LDAP_Connection( USER_READ, USER_WRITE )
	def remove( self, request, search_base = None, ldap_user_write = None, ldap_user_read = None, ldap_position = None ):
		"""Deletes a workgroup

		requests.options = [ <LDAP DN>, ... ]

		return: True|<error message>
		"""
		if not request.options:
			raise UMC_CommandError( 'Invalid arguments' )

		if request.flavor != 'workgroup-admin':
			raise UMC_CommandError( 'not supported' )

		# load group object
		group = request.options[ 0 ].get( 'object', {} )
		grp = udm_modules.get( 'groups/group' ).object( None, ldap_user_write, ldap_position, group[ 0 ] )

		# get the SchoolSearchBase based on the DN of the group to be deleted
		schoolDN = SchoolSearchBase.getOUDN(grp.dn)
		if not schoolDN:
			raise UMC_CommandError( 'Group must within the scope of a school OU: %s' % grp.dn )
		school = ldap_user_write.explodeDn( schoolDN, 1 )[0]
		MODULE.info('schoolDN=%s school=%s availableSchools=%s' % (schoolDN, school, search_base.availableSchools))
		search_base = SchoolSearchBase( search_base.availableSchools, school )
		MODULE.info('Search base is: %s' % search_base.schoolDN)

		try:
			# remove group share
			self._remove_group_share(grp['name'], ldap_user_write, search_base)

			# remove group
			grp.remove()

		except udm_exceptions.base as e:
			MODULE.error('Could not remove group "%s": %s' % (grp.dn, e))
			self.finished( request.id, [ { 'success' : False, 'message' : str( e ) } ] )

		self.finished( request.id, [ { 'success' : True } ] )

