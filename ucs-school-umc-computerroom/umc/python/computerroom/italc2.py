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

from univention.management.console.config import ucr

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE

import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display

import italc
import notifier
import notifier.signals

_ = Translation( 'ucs-school-umc-computerroom' ).translate

ITALC_VNC_PORT = int( ucr.get( 'ucsschool/umc/computerroom/vnc/port', 11100 ) )
ITALC_VNC_UPDATE = int( ucr.get( 'ucsschool/umc/computerroom/vnc/update', 10 ) )
ITALC_CORE_UPDATE = int( ucr.get( 'ucsschool/umc/computerroom/core/update', 5 ) )

italc.ItalcCore.init()

italc.ItalcCore.config.setLogLevel( italc.Logger.LogLevelCritical )
italc.ItalcCore.config.setLogToStdErr( False )
italc.ItalcCore.config.setLogFileDirectory( '/var/log/univention/' )
italc.Logger( 'ucs-school-umc-computerroom' )

italc.ItalcCore.setRole( italc.ItalcCore.RoleTeacher )
italc.ItalcCore.initAuthentication( italc.AuthenticationCredentials.PrivateKey )

class ITALC_Error( Exception ):
	pass

class ITALC_Computer( notifier.signals.Provider ):
	def __init__( self, ldap_dn = None ):
		notifier.signals.Provider.__init__( self )
		self.signal_new( 'connected' )
		self._vnc = None
		self._core = None
		self._dn = ldap_dn
		self._computer = None
		self._timer = None
		self.readLDAP()
		self.open()

	@LDAP_Connection()
	def readLDAP( self, ldap_user_read = None, ldap_position = None, search_base = None ):
		attrs = ldap_user_read.lo.get( self._dn )
		modules = udm_modules.identify( self._dn, attrs, module_base = 'computers/' )
		if len( modules ) != 1:
			MODULE.warn( 'LDAP object %s could not identified (found %d modules)' % ( self._dn, len( modules ) ) )
			raise ITALC_Error( 'Unknown computer type' )
		self._computer = udm_objects.get( modules[ 0 ], None, ldap_user_read, ldap_position, self._dn, attributes = attrs )
		if not self._computer:
			raise ITALC_Error( 'Could not find the computer %s' % self._dn )

		self._computer.open()

	def open( self ):
		if not 'ip' in self._computer.info:
			raise ITALC_Error( 'Unknown IP address' )
		self._vnc = italc.ItalcVncConnection()
		self._vnc.setHost( self._computer.info[ 'ip' ][ 0 ] )
		self._vnc.setPort( ITALC_VNC_PORT )
		self._vnc.setQuality( italc.ItalcVncConnection.ThumbnailQuality )
		self._vnc.setFramebufferUpdateInterval( 200 )
		self._vnc.start()
		notifier.timer_add( 100, self._when_connected )

	def _when_connected( self ):
		if not self._vnc.isConnected():
			return True
		self._core = italc.ItalcCoreConnection( self._vnc )
		self.signal_emit( 'connected', self._computer.info.get( 'name' ) )
		self.start()

	def close( self ):
		print 'CRUNCHY: stop'
		# self._vnc.stop()

	def update( self ):
		self._core.sendGetUserInformationRequest()
		if self._core.user():
			self._core.reportSlaveStateFlags()
		return True

	def start( self ):
		self.stop()
		self.update()
		self._timer = notifier.timer_add( ITALC_CORE_UPDATE * 1000, self.update )

	def stop( self ):
		if self._timer is not None:
			notifier.timer_remove( self._timer )
			self._timer = None

	@property
	def name( self ):
		return self._computer.info.get( 'name', None )

	@property
	def user( self ):
		return self._core and self._core.user() or ''

	@property
	def description( self ):
		return self._computer.info.get( 'description', None )

	@property
	def states( self ):
		return {
			'ScreenLock' : self._core and self._core.isScreenLockRunning() or None,
			'InputLock' :  self._core and self._core.isInputLockRunning() or None,
			'DemoServer' :  self._core and self._core.isDemoServerRunning() or None,
			'DemoClient' :  self._core and self._core.isDemoClientRunning() or None,
			'MessageBox' :  self._core and self._core.isMessageBoxRunning() or None,
			}

	@property
	def connected( self ):
		return self._vnc.isConnected()

	def lockScreen( self, value ):
		if value:
			self._core.lockScreen()
		else:
			self._core.unlockScreen()

	def lockInput( self, value ):
		if value:
			self._core.lockInput()
		else:
			self._core.unlockInput()

	def message( self, text ):
		self._core.displayTextMessage( text )

class ITALC_Manager( dict, notifier.signals.Provider ):
	def __init__( self ):
		dict.__init__( self )
		notifier.signals.Provider.__init__( self )
		self.signal_new( 'initialized' )
		self._room = None
		self._school = None

	# def __del__( self ):
	# 	self._clear()

	@property
	def room( self ):
		return self._room

	@room.setter
	def room( self, value ):
		self._clear()
		self._set( value )

	@property
	def school( self ):
		return self._school

	@school.setter
	def school( self, value ):
		self._school = value
		self._clear()

	def _clear( self ):
		if self._room:
			for name, computer in self.items():
				if computer._core.isConnected():
					computer.stop()
			self.clear()
			self._room = None

	def _connected( self, computer ):
		for comp in self.values():
			if not comp.connected:
				break
		else:
			self.signal_emit( 'initialized' )

	@LDAP_Connection()
	def _set( self, room, ldap_user_read = None, ldap_position = None, search_base = None ):
		grp_module = udm_modules.get( 'groups/group' )
		if not grp_module:
			raise ITALC_Error( 'Unknown computer room' )
		groupresult = udm_modules.lookup( grp_module, None, ldap_user_read, filter = 'cn=%s-%s' % ( search_base.school, room ),scope = 'one', base = search_base.rooms )
		if len( groupresult ) != 1:
			raise ITALC_Error( 'Did not find exactly 1 group for the room (count: %d)' % len( groupresult ) )

		roomgrp = groupresult[ 0 ]
		roomgrp.open()
		computers = filter( lambda host: host.endswith( search_base.computers ), roomgrp[ 'hosts' ] )
		if not computers:
			raise ITALC_Error( 'There are no computers in the selected room.' )

		for dn in computers:
			comp = ITALC_Computer( dn )
			comp.signal_connect( 'connected', self._connected )
			self.__setitem__( comp.name, comp )

