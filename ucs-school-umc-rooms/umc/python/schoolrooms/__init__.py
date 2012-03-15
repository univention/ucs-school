#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Manage room and their associated computers
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

from univention.management.console.config import ucr

from univention.lib.i18n import Translation
from univention.management.console.modules import UMC_OptionTypeError, Base
from univention.management.console.log import MODULE
from univention.management.console.protocol.definitions import *

import univention.admin.modules as udm_modules

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display, USER_READ, USER_WRITE

_ = Translation( 'ucs-school-umc-rooms' ).translate

class Instance( SchoolBaseModule ):
	def __init__( self ):
		# initiate list of internal variables
		SchoolBaseModule.__init__(self)
		# ... custom code

	def init(self):
		SchoolBaseModule.init(self)
		# ... custom code

	@LDAP_Connection()
	def computers( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""
		requests.options = {}
		  'pattern' -- search pattern for name (default: '')
		  'school'
		"""
		MODULE.info( 'schoolrooms.query: options: %s' % str( request.options ) )
		pattern = request.options.get('name', '')
		ldapFilter = LDAP_Filter.forComputers(pattern)

		objs = udm_modules.lookup( 'computers/computer', None, ldap_user_read, scope = 'one', base = search_base.computers, filter = ldapFilter)
		result = [ {
			'label': i['name'],
			'id': i.dn
		} for i in objs ]
		result = sorted( result, cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'label' ] )

		MODULE.info( 'schoolrooms.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	@LDAP_Connection()
	def query( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""
		requests.options = {}
		  'name' -- search pattern for name or description (default: '')
		  'school'
		"""
		MODULE.info( 'schoolrooms.query: options: %s' % str( request.options ) )
		pattern = request.options.get('pattern', '')
		ldapFilter = LDAP_Filter.forGroups(pattern, search_base.school)

		objs = udm_modules.lookup( 'groups/group', None, ldap_user_read, scope = 'one', base = search_base.rooms, filter = ldapFilter)
		result = [ {
			'name': i['name'].replace('%s-' % search_base.school, '', 1),
			'description': i.oldinfo.get('description',''),
			'$dn$': i.dn
		} for i in objs ]
		result = sorted( result, cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'name' ] )

		MODULE.info( 'schoolrooms.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	def get( self, request ):
		"""Returns the objects for the given IDs

		requests.options = [ <ID>, ... ]

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info( 'schoolrooms.get: options: %s' % str( request.options ) )

		self.finished( request.id, {} )

	@LDAP_Connection(USER_READ, USER_WRITE)
	def add(self, request, search_base=None, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		"""Adds a new room

		requests.options = [ { $dn$ : ..., }, ... ]

		return: True|<error message>
		"""
		MODULE.info('schoolrooms.add: object: %s' % str(request.options[0]))
		if not request.options:
			raise UMC_CommandError('Invalid arguments')

		room = request.options[0].get('object', {})
		ldap_position.setDn(search_base.rooms)
		new_room = udm_modules.get('groups/group').object(None, ldap_user_write, ldap_position)
		new_room.open()

		new_room['name'] = '%s-%s' % (search_base.school, room['name'])
		new_room['description'] = room['description']
		new_room['users'] = room['computers']

		new_room.create()

		self.finished(request.id, True)
