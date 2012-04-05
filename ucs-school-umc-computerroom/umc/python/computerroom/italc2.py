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

import copy
import sys
import tempfile
import threading

from univention.management.console.config import ucr

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE

import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display

import notifier
import notifier.signals
import notifier.threads

from PyQt4.QtCore import QObject, pyqtSlot, SIGNAL, Qt, QCoreApplication
from PyQt4.QtGui import QImageWriter

import italc

_ = Translation( 'ucs-school-umc-computerroom' ).translate

ITALC_DEMO_PORT = int( ucr.get( 'ucsschool/umc/computerroom/demo/port', 11400 ) )
ITALC_VNC_PORT = int( ucr.get( 'ucsschool/umc/computerroom/vnc/port', 11100 ) )
ITALC_VNC_UPDATE = int( ucr.get( 'ucsschool/umc/computerroom/vnc/update', 0.5 ) )
ITALC_CORE_UPDATE = int( ucr.get( 'ucsschool/umc/computerroom/core/update', 2 ) )

italc.ItalcCore.init()

italc.ItalcCore.config.setLogLevel( italc.Logger.LogLevelDebug )
italc.ItalcCore.config.setLogToStdErr( True )
italc.ItalcCore.config.setLogFileDirectory( '/var/log/univention/' )
italc.Logger( 'ucs-school-umc-computerroom' )
italc.ItalcCore.config.setLogonAuthenticationEnabled( False )

italc.ItalcCore.setRole( italc.ItalcCore.RoleTeacher )
italc.ItalcCore.initAuthentication( italc.AuthenticationCredentials.PrivateKey )

class ITALC_Error( Exception ):
	pass


class LockableAttribute( object ):
	def __init__( self, initial_value = None, locking = True ):
		self._lock = locking and threading.Lock() or None
		MODULE.warn( 'Locking object: %s' % self._lock )
		self._old = initial_value
		self._current = copy.copy( initial_value )

	def lock( self ):
		if self._lock is None: return
		if not self._lock.acquire( 1000 ):
			raise ITALC_Error( 'Could not lock attribute' )

	def unlock( self ):
		if self._lock is None: return
		self._lock.release()

	@property
	def current( self ):
		self.lock()
		tmp = copy.copy( self._current )
		self.unlock()
		return tmp

	@property
	def old( self ):
		self.lock()
		tmp = copy.copy( self._old )
		self.unlock()
		return tmp

	@property
	def isInitialized( self ):
		self.lock()
		ret = self._current is not None
		self.unlock()
		return ret

	@property
	def hasChanged( self ):
		self.lock()
		MODULE.info( 'hasChanged: %s != %s' % ( self._old, self._current ) )
		diff = self._old != self._current
		self._old = copy.copy( self._current )
		self.unlock()
		return diff

	def reset( self, inital_value = None ):
		self.lock()
		self._old = copy.copy( inital_value )
		self._current = copy.copy( inital_value )
		self.unlock()

	def set( self, value ):
		self.lock()
		if value != self._current:
			self._old = copy.copy( self._current )
			self._current = copy.copy( value )
			MODULE.info( 'set: %s != %s' % ( self._old, self._current ) )
		self.unlock()

class ITALC_Computer( notifier.signals.Provider, QObject ):
	CONNECTION_STATES = {
		italc.ItalcVncConnection.Disconnected : 'disconnected',
		italc.ItalcVncConnection.Connected : 'connected',
		italc.ItalcVncConnection.ConnectionFailed : 'error',
		italc.ItalcVncConnection.AuthenticationFailed : 'error',
		italc.ItalcVncConnection.HostUnreachable : 'error'
		}

	def __init__( self, ldap_dn = None ):
		QObject.__init__( self )
		# notifier.threads.Enhanced.__init__( self, None, None )
		notifier.signals.Provider.__init__( self )

		self.signal_new( 'connected' )
		self.signal_new( 'screen-lock' )
		self.signal_new( 'input-lock' )
		self.signal_new( 'access-dialog' )
		self.signal_new( 'demo-client' )
		self.signal_new( 'demo-server' )
		self.signal_new( 'message-box' )
		self.signal_new( 'system-tray-icon' )
		self._vnc = None
		self._core = None
		self._dn = ldap_dn
		self._computer = None
		self._timer = None
		self._username = LockableAttribute()
		self._homedir = LockableAttribute()
		self._flags = LockableAttribute()
		self._state = LockableAttribute( initial_value = 'disconnected' )
		self._allowedClients = []
		self.readLDAP()
		self.open()

	@LDAP_Connection()
	def readLDAP( self, ldap_user_read = None, ldap_position = None, search_base = None ):
		attrs = ldap_user_read.lo.get( self._dn )
		modules = udm_modules.identify( self._dn, attrs, module_base = 'computers/' )
		if len( modules ) != 1:
			MODULE.warn( 'LDAP object %s could not be identified (found %d modules)' % ( self._dn, len( modules ) ) )
			raise ITALC_Error( 'Unknown computer type' )
		self._computer = udm_objects.get( modules[ 0 ], None, ldap_user_read, ldap_position, self._dn, attributes = attrs )
		if not self._computer:
			raise ITALC_Error( 'Could not find the computer %s' % self._dn )

		self._computer.open()

	def open( self ):
		MODULE.warn( 'Opening VNC connection' )
		self._vnc = italc.ItalcVncConnection()
		self._vnc.setHost( self.ipAddress )
		self._vnc.setPort( ITALC_VNC_PORT )
		self._vnc.setQuality( italc.ItalcVncConnection.ThumbnailQuality )
		self._vnc.setFramebufferUpdateInterval( 1000 * ITALC_VNC_UPDATE )
		self._vnc.start()
		self._vnc.stateChanged.connect( self._stateChanged ) #, Qt.DirectConnection )

	@pyqtSlot( int )
	def _stateChanged( self, state ):
		self._state.set( ITALC_Computer.CONNECTION_STATES[ state ] )

		MODULE.warn( '%s: current state: %s' % ( str( self.name ), str( self._state.current ) ) )
		if not self._core and self._state.current == 'connected' and self._state.old == 'disconnected':
			self._core = italc.ItalcCoreConnection( self._vnc )
			self._core.receivedUserInfo.connect( self._userInfo )
			self._core.receivedSlaveStateFlags.connect( self._slaveStateFlags )
			self.signal_emit( 'connected', self )
			self.start()


	@pyqtSlot( str, str )
	def _userInfo( self, username, homedir ):
		self._username.set( username )
		self._homedir.set( homedir )
		if self._username.current:
			self._core.reportSlaveStateFlags()

	def _emit_flag( self, diff, flag, signal ):
		if diff & flag:
			self.signal_emit( signal, bool( self._flags.current & flag ) )

	@pyqtSlot( int )
	def _slaveStateFlags( self, flags ):
		self._flags.set( flags )
		if self._flags.old is None:
			diff = self._flags.current
		else:
			# which flags have changed: old xor current
			diff = self._flags.old ^ self._flags.current
		self._emit_flag( diff, italc.ItalcCore.ScreenLockRunning, 'screen-lock' )
		self._emit_flag( diff, italc.ItalcCore.InputLockRunning, 'input-lock' )
		self._emit_flag( diff, italc.ItalcCore.AccessDialogRunning, 'access-dialog' )
		self._emit_flag( diff, italc.ItalcCore.DemoClientRunning, 'demo-client' )
		self._emit_flag( diff, italc.ItalcCore.DemoServerRunning, 'demo-server' )
		self._emit_flag( diff, italc.ItalcCore.MessageBoxRunning, 'message-box' )
		self._emit_flag( diff, italc.ItalcCore.SystemTrayIconRunning, 'system-tray-icon' )

	def close( self ):
		pass
		# self._vnc.stop()

	def update( self ):
		if self._state.current != 'connected':
			MODULE.info( 'currently not connected' )
			return True
		self._core.sendGetUserInformationRequest()
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
	def ipAddress( self ):
		if not 'ip' in self._computer.info or not self._computer.info[ 'ip' ]:
			raise ITALC_Error( 'Unknown IP address' )
		return self._computer.info[ 'ip' ][ 0 ]

	@property
	def user( self ):
		return self._username

	@property
	def description( self ):
		return self._computer.info.get( 'description', None )

	@property
	def screenLock( self ):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isScreenLockRunning()

	@property
	def inputLock( self ):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isInputLockRunning()

	@property
	def demoServer( self ):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isDemoServerRunning()

	@property
	def demoClient( self ):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isDemoClientRunning()

	@property
	def messageBox( self ):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isMessageBoxRunning()

	@property
	def flags( self ):
		return self._flags

	@property
	def flagsDict( self ):
		return {
			'ScreenLock' : self.screenLock,
			'InputLock' :  self.inputLock,
			'DemoServer' :  self.demoServer,
			'DemoClient' :  self.demoClient,
			'MessageBox' :  self.messageBox,
			}

	@property
	def state( self ):
		'''Returns a LockableAttribute containing an abstracted
		connection state. Possible values: conntected, disconnected,
		error'''
		return self._state

	@property
	def connected( self ):
		return self._core and self._vnc.isConnected()

	@property
	def hostUnreachable( self ):
		return self._vnc and self._vnc.state() == italc.ItalcVncConnection.HostUnreachable

	@property
	def connectFailed( self ):
		return self._vnc and self._vnc.state() == italc.ItalcVncConnection.ConnectionFailed

	@property
	def screenshot( self ):
		image = self._vnc.image()
		if not image.byteCount():
			return None
		tmpfile = tempfile.NamedTemporaryFile( delete = False )
		tmpfile.close()
		writer = QImageWriter( tmpfile.name, 'JPG' )
		writer.write( image )
		return tmpfile

	@property
	def screenshotQImage( self ):
		return self._vnc.image()

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

	def denyClients( self ):
		for client in self._allowedClients[ : ]:
			self._core.demoServerUnallowHost( client.ipAddress )
			self._allowedClients.remove( client )

	def allowClients( self, clients ):
		self.denyClients()
		for client in clients:
			self._core.demoServerAllowHost( client.ipAddress )
			self._allowedClients.append( client )

	def startDemoServer( self, allowed_clients = [] ):
		if not self.connected:
			raise ITALC_Error( 'not connected' )
		self._core.stopDemoServer()
		self._core.startDemoServer( ITALC_VNC_PORT, ITALC_DEMO_PORT )
		self.allowClients( allowed_clients )

	def stopDemoServer( self ):
		self.denyClients()
		self._core.stopDemoServer()

	def startDemoClient( self, server, fullscreen = True ):
		self._core.stopDemo()
		self._core.unlockScreen()
		self._core.unlockInput()
		self._core.startDemo( server.ipAddress, ITALC_DEMO_PORT, fullscreen )

	def stopDemoClient( self ):
		self._core.stopDemo()

class ITALC_Manager( dict, notifier.signals.Provider ):
	def __init__( self, username, password ):
		dict.__init__( self )
		notifier.signals.Provider.__init__( self )
		self.signal_new( 'initialized' )
		self._room = None
		self._school = None
		self._demoServer = None
		self._initialized = False
		italc.ItalcCore.authenticationCredentials.setLogonUsername( username )
		italc.ItalcCore.authenticationCredentials.setLogonPassword( password )

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
		self._clear()
		self._school = value

	@property
	def initialized( self ):
		return self._initialized

	def _clear( self ):
		if self._room:
			for name, computer in self.items():
				if computer.connected:
					computer.stop()
			self.clear()
			self._room = None
			self._initialized = False

	def _connected( self, computer ):
		MODULE.info( 'New computer is connected ' + computer.name )
		for comp in self.values():
			if not comp.connected and not comp.hostUnreachable and not comp.connectFailed:
				break
		else:
			self._initialized = True
			self.signal_emit( 'initialized' )

	@LDAP_Connection()
	def _set( self, room, ldap_user_read = None, ldap_position = None, search_base = None ):
		grp_module = udm_modules.get( 'groups/group' )
		if not grp_module:
			raise ITALC_Error( 'Unknown computer room' )
		if room.startswith( 'cn=' ):
			groupresult = [ udm_objects.get( grp_module, None, ldap_user_read, ldap_position, room ) ]
		else:
			groupresult = udm_modules.lookup( grp_module, None, ldap_user_read, filter = 'cn=%s-%s' % ( search_base.school, room ),scope = 'one', base = search_base.rooms )
		if len( groupresult ) != 1:
			raise ITALC_Error( 'Did not find exactly 1 group for the room (count: %d)' % len( groupresult ) )

		roomgrp = groupresult[ 0 ]
		roomgrp.open()
		self._room = roomgrp[ 'name' ].lstrip( '%s-' % search_base.school )
		computers = filter( lambda host: host.endswith( search_base.computers ), roomgrp[ 'hosts' ] )
		if not computers:
			raise ITALC_Error( 'There are no computers in the selected room.' )

		for dn in computers:
			try:
				comp = ITALC_Computer( dn )
				comp.signal_connect( 'connected', self._connected )
				self.__setitem__( comp.name, comp )
			except ITALC_Error, e:
				MODULE.warn( 'Computer could not be added: %s' % str( e ) )

	@LDAP_Connection()
	def startDemo( self, demo_server, fullscreen = True, ldap_user_read = None, ldap_position = None, search_base = None ):
		server = self.get( demo_server )
		if server is None:
			raise AttributeError( 'unknown system %s' % demo_server )

		# start demo server
		MODULE.info( 'Demo server is %s' % demo_server )
		clients = filter( lambda comp: comp.name != demo_server and comp.connected, self.values() )
		MODULE.info( 'Demo clients: %s' % ', '.join( map( lambda x: x.name, clients ) ) )
		teachers = map( lambda x: x.name, filter( lambda comp: not comp.user.current or str( comp.user.current ).endswith( search_base.teachers ), self.values() ) )
		server.startDemoServer( clients )
		for client in clients:
			if client.name in teachers:
				client.startDemoClient( server, False )
			else:
				client.startDemoClient( server, fullscreen )
		self._demoServer = server

	def stopDemo( self, demo_server = None ):
		if demo_server is None and self._demoServer is None:
			raise ITALC_Error( 'Unknown demoserver' )
		elif demo_server is None:
			demo_server = self._demoServer
		elif isinstance( demo_server, basestring ):
			demo_server = self[ demo_server ]

		demo_server.stopDemoServer()
		for client in filter( lambda comp: comp.name != demo_server, self.values() ):
			client.stopDemoClient()
