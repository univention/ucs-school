#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Administration of groups
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

import copy

from univention.lib.i18n import Translation

from univention.management.console.config import ucr
from univention.management.console.modules import UMC_OptionTypeError, UMC_CommandError, Base
from univention.management.console.log import MODULE
from univention.management.console.protocol.definitions import *

import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects
import univention.admin.uexceptions as udm_exceptions

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display, USER_READ, USER_WRITE

_ = Translation( 'ucs-school-umc-groups' ).translate

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

		groupresult = udm_modules.lookup( 'groups/group', None, ldap_user_read, scope = 'one', base = base, filter = LDAP_Filter.forGroups( request.options.get( 'pattern', '' ), search_base.school ) )

		self.finished( request.id, map( lambda grp: { '$dn$' : grp.dn, 'name' : grp[ 'name' ].replace( '%s-' % search_base.school, '', 1 ), 'description' : grp[ 'description' ] }, groupresult ) )

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
		result[ 'name' ] = grp[ 'name' ].replace( '%s-' % search_base.school, '', 1 )
		result[ 'description' ] = grp[ 'description' ]

		if request.flavor == 'class':
			# members are teachers
			memberDNs = [ usr for usr in grp[ 'users' ] if usr.endswith( search_base.teachers ) ]
		elif request.flavor == 'workgroup-admin':
			memberDNs = grp[ 'users' ]
		else:
			memberDNs = [ usr for usr in grp[ 'users' ] if usr.endswith( search_base.students ) ]

		# read members:
		user_mod = udm_modules.get( 'users/user' )
		members = []
		for member_dn in memberDNs:
			user = udm_objects.get( user_mod, None, ldap_user_read, ldap_position, member_dn )
			if not user:
				continue
			user.open()
			members.append( { 'id' : user.dn, 'label' : Display.user( user ) } )
		result[ 'members' ] = members

		self.finished( request.id, [ result, ] )

	def _remove_users_by_base( self, members, base ):
		"""Removes the LDAP objects from the given list of LDAP-DN that match teachers"""
		students = []
		for user in members:
			if user.endswith( base ):
				continue
			students.append( user )
		return students

	@LDAP_Connection( USER_READ, USER_WRITE )
	def put( self, request, search_base = None, ldap_user_write = None, ldap_user_read = None, ldap_position = None ):
		"""Returns the objects for the given IDs

		requests.options = [ { object : ..., options : ... }, ... ]

		return: True|<error message>
		"""
		if not request.options:
			raise UMC_CommandError( 'Invalid arguments' )

		group = request.options[ 0 ].get( 'object', {} )
		grp = udm_objects.get( udm_modules.get( 'groups/group' ), None, ldap_user_write, ldap_position, group[ '$dn$' ] )
		if not grp:
			raise UMC_OptionTypeError( 'unknown group object' )

		grp.open()
		grp[ 'description' ] = group[ 'description' ]
		if request.flavor == 'class':
			grp[ 'users' ] = self._remove_users_by_base( grp[ 'users' ], search_base.teachers ) + group[ 'members' ]
		elif request.flavor == 'workgroup-admin':
			grp[ 'users' ] = group[ 'members' ]
		elif request.flavor == 'workgroup':
			if [ dn for dn in grp[ 'users' ] if dn.endswith( search_base.teachers ) ]:
				raise UMC_CommandError( 'Adding teachers is not allowed' )
			grp[ 'users' ] = self._remove_users_by_base( grp[ 'users' ], search_base.students ) + group[ 'members' ]

		grp.modify()

		self.finished( request.id, True )

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
		ldap_position.setDn( search_base.workgroups )
		grp = udm_modules.get( 'groups/group' ).object( None, ldap_user_write, ldap_position )
		grp.open()

		grp[ 'name' ] = '%s-' % search_base.school + group[ 'name' ]
		grp[ 'description' ] = group[ 'description' ]
		grp[ 'users' ] = group[ 'members' ]

		grp.create()

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
		group = request.options[ 0 ].get( 'object', {} )
		grp = udm_modules.get( 'groups/group' ).object( None, ldap_user_write, ldap_position, group[ 0 ] )

		try:
			grp.remove()
		except udm_exceptions.base as e:
			MODULE.error('Could not remove group "%s": %s' % (grp.dn, e))
			self.finished( request.id, [ { 'success' : False, 'message' : str( e ) } ] )

		self.finished( request.id, [ { 'success' : True } ] )
