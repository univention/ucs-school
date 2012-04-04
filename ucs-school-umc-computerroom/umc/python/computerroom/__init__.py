#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
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

import os
from random import Random

from univention.management.console.config import ucr

from univention.lib.i18n import Translation
from univention.management.console.modules import UMC_OptionTypeError, UMC_CommandError, Base
from univention.management.console.log import MODULE
from univention.management.console.protocol import MIMETYPE_PNG, MIMETYPE_JPEG, Response

import univention.admin.modules as udm_modules

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display

from italc2 import ITALC_Manager

import notifier

_ = Translation( 'ucs-school-umc-computerroom' ).translate

class Instance( SchoolBaseModule ):
	def init( self ):
		SchoolBaseModule.init( self )
		self._italc = ITALC_Manager( self._username, self._password )
		self._random = Random()
		self._random.seed()

	@LDAP_Connection()
	def query( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Searches for entries:

		requests.options = {}
		  'school'
		  'room' -- DN of the selected room

		return: [ { '$dn$' : <LDAP DN>, 'name': '...', 'description': '...' }, ... ]
		"""
		self.required_options( request, 'school', 'room' )
		MODULE.info( 'computerroom.query: options: %s' % str( request.options ) )

		if self._italc.school != request.options[ 'school' ]:
			self._italc.school = request.options[ 'school' ]
		if self._italc.room != request.options[ 'room' ]:
			self._italc.room = request.options[ 'room' ]

		try:
			result = []
			for computer in self._italc.values():
				item = { 'id' : computer.name,
						 'name' : computer.name,
						 'user' : computer.user.current,
						 'connection' : computer.state.current,
						 'description' : computer.description }
				item.update( computer.flagsDict )
				result.append( item )

				MODULE.info( 'computerroom.query: result: %s' % str( result ) )
			self.finished( request.id, result )
		except Exception, e:
			MODULE.error( 'query failed: %s' % str( e ) )
			self._italc.signal_disconnect( 'initialized', _initialized )
			self.finished( request.id, str( e ), success = False )

	def update( self, request ):
		"""Returns an update for the computers in the selected
		room. Just attributes that have changed since the last call will
		be included in the result

		requests.options = [ <ID>, ... ]

		return: [ { 'id' : <unique identifier>, 'states' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.warn( 'Update: start' )
		MODULE.warn( 'Update: Current school: %s, current room: %s' % ( str( self._italc.school ), str( self._italc.room ) ) )

		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError( 'no room selected' )

		result = []
		for computer in self._italc.values():
			item = dict( id = computer.name )
			modified = False
			if computer.state.hasChanged:
				item[ 'connection' ] = str( computer.state.current )
				modified = True
			if computer.flags.hasChanged:
				item.update( computer.flagsDict )
				modified = True
			if computer.user.hasChanged:
				item[ 'user' ] = str( computer.user.current )
				modified = True
			if modified:
				result.append( item )

		MODULE.info( 'Update: result: %s' % str( result ) )
		self.finished( request.id, result )

	def lock( self, request ):
		"""Returns the objects for the given IDs

		requests.options = { 'computer' : <computer name>, 'device' : (screen|input), 'lock' : <boolean or string> }

		return: { 'success' : True|False, [ 'details' : <message> ] }
		"""
		self.required_options( request, 'computer', 'device', 'lock' )
		success = False
		message = ''
		device = request.options[ 'device' ]
		if not device in ( 'screen', 'input' ):
			raise UMC_OptionTypeError( 'unknown device %s' % device )

		computer = self._italc.get( request.options[ 'computer' ], None )
		if computer is None:
			raise UMC_CommandError( 'Unknown computer %s' % request.options[ 'computer' ] )

		def _answer( new_value, computer, request, message ):
			MODULE.warn( 'Got signal with value %s' % new_value )
			success = new_value == request.options[ 'lock' ]
			computer.signal_disconnect( '%s-lock' % device, _answer )
			self.finished( request.id, { 'success' : success, 'details' : not success and message or '' } )

		MODULE.warn( 'Connecting to signal %s' % '%s-lock' % device )
		# computer.signal_connect( '%s-lock' % device, notifier.Callback( _answer, computer, request, message ) )

		MODULE.warn( 'Locking device %s' % device )
		if device == 'screen':
			computer.lockScreen( request.options[ 'lock' ] )
		else:
			computer.lockInput( request.options[ 'lock' ] )
		self.finished( request.id, { 'success' : True, 'details' : '' } )

	def screenshot( self, request ):
		"""Returns a JPEG image containing a screenshot of the given
		computer. The computer must be in the current room

		requests.options = { 'computer' : <computer name>[, 'size' : (thumbnail|...)] }

		return (MIME-type image/jpeg): screenshot
		"""
		self.required_options( request, 'computer' )
		computer = self._italc.get( request.options[ 'computer' ], None )
		if not computer:
			raise UMC_CommandError( 'Unknown computer' )

		response = Response( mime_type = MIMETYPE_JPEG )
		response.id = request.id
		response.command = 'COMMAND'
		tmpfile = computer.screenshot
		response.body = open( tmpfile.name ).read()
		os.unlink( tmpfile.name )
		self.finished( request.id, response )

	def demo_start( self, request ):
		"""Starts a demo

		requests.options = { 'server' : <computer> }

		return: [True|False)
		"""
		self.required_options( request, 'server' )
		self._italc.startDemo( request.options[ 'server' ], True )
		self.finished( request.id, True )

	def demo_stop( self, request ):
		"""Stops a demo

		requests.options = none

		return: [True|False)
		"""
		self._italc.stopDemo()
		self.finished( request.id, True )

