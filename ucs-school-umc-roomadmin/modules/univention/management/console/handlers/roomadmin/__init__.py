#!/usr/bin/python2.4
#
# Univention Management Console
#
# Copyright 2007-2010 Univention GmbH
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

import univention.management.console as umc
import univention.management.console.categories as umcc
import univention.management.console.protocol as umcp
import univention.management.console.handlers as umch
import univention.management.console.dialog as umcd
import univention.management.console.tools as umct
import univention.admin.modules
import univention.admin.objects

import univention.debug as ud
import univention.config_registry
import univention.uldap

import notifier
import notifier.popen
import notifier.threads as threads

import italc
from json import JsonReader, JsonWriter
import PyQt4.QtCore

import os, re, fnmatch, time, random
import traceback
random.seed ()

from types import StringTypes

import _revamp
import _types
import _schoolldap

_ = umc.Translation( 'univention.management.console.handlers.roomadmin' ).translate

icon = 'roomadmin/module'
short_description = _( 'Room admin' )
long_description = _( 'Computer room administration' )
categories = [ 'all' ]

italc_update_interval = 5
italc_connection_timeout = 30

italc_connections = {}
# persistent storage for running demo modes
italc_demostorage_path = '/var/lib/univention-management-console/roomadmin'
if not os.path.exists (italc_demostorage_path):
	os.makedirs (italc_demostorage_path)

command_description = {
	'roomadmin/room/search': umch.command(
		short_description = _( 'Administrate rooms' ),
		long_description = _( 'Administrate rooms' ),
		method = 'roomadmin_room_search',
		values = { 'key' : _types.searchkey,
				   'filter' : _types.sfilter,
				   'ou': _types.ou
				   },
		startup = True,
		priority = 90
	),
	'roomadmin/room/add': umch.command(
		short_description = _( 'add room' ),
		long_description = _( 'add room' ),
		method = 'roomadmin_room_add',
		values = {  'ou': _types.ou
					},
		priority = 80
	),
	'roomadmin/room/edit': umch.command(
		short_description = _( 'edit room' ),
		long_description = _( 'edit room' ),
		method = 'roomadmin_room_edit',
		values = {  'room': _types.room,
					'roomdn': _types.roomdn,
					'description': _types.description,
					'roommembers': _types.hostdnlist,
					'ou': _types.ou,
					},
		priority = 80
	),
	'roomadmin/room/set': umch.command(
		short_description = _( 'set room' ),
		long_description = _( 'set room' ),
		method = 'roomadmin_room_set',
		values = {  'room': _types.room,
					'roomdn': _types.roomdn,
					'description': _types.description,
					'roommembers': _types.hostdnlist,
					'ou': _types.ou,
					},
		priority = 80
	),
	'roomadmin/room/remove': umch.command(
		short_description = _( 'remove room' ),
		long_description = _( 'remove room' ),
		method = 'roomadmin_room_remove',
		values = {  'room': _types.room,
					'roomdn': _types.roomdn,
					'ou': _types.ou
					},
		priority = 80
	),

	'roomadmin/wol/send': umch.command(
		short_description = _( 'Power On Computers By Wake On LAN' ),
		long_description = _( 'Power On Computers By Wake On LAN' ),
		method = 'roomadmin_wol_send',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 80
	),

	'roomadmin/room/list': umch.command(
		short_description = _( 'List rooms and associated computers' ),
		long_description = _( 'List rooms and associated computers' ),
		method = 'roomadmin_room_list',
		values = { 'room' : _types.room	},
		startup = True,
		caching = True,
		priority = 100
	),
	'roomadmin/set/access/internet/enable': umch.command(
		short_description = _( 'Enable internet access' ),
		long_description = _( 'Enable access to internet for selected computers' ),
		method = 'roomadmin_set_access_internet_enable',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/set/access/internet/disable': umch.command(
		short_description = _( 'Disable internet access' ),
		long_description = _( 'Disable access to internet for selected computers' ),
		method = 'roomadmin_set_access_internet_disable',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/italc/reboot': umch.command(
		short_description = _( 'Reboot' ),
		long_description = _( 'Reboot selected computers' ),
		method = 'roomadmin_italc_reboot',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/italc/shutdown': umch.command(
		short_description = _( 'Shutdown' ),
		long_description = _( 'Shutdown selected computers' ),
		method = 'roomadmin_italc_shutdown',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/italc/lock/screen': umch.command(
		short_description = _( 'Lock Screen' ),
		long_description = _( 'Lock screen for selected computers' ),
		method = 'roomadmin_italc_lock_screen',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/italc/unlock/screen': umch.command(
		short_description = _( 'Unlock Screen' ),
		long_description = _( 'Unlock screen for selected computers' ),
		method = 'roomadmin_italc_unlock_screen',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/italc/lock/input': umch.command(
		short_description = _( 'Lock Input Devices' ),
		long_description = _( 'Lock input devices for selected computers' ),
		method = 'roomadmin_italc_lock_input',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/italc/unlock/input': umch.command(
		short_description = _( 'Unlock Input Devices' ),
		long_description = _( 'Unlock input devices for selected computers' ),
		method = 'roomadmin_italc_unlock_input',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/italc/logout': umch.command(
		short_description = _( 'Logout User' ),
		long_description = _( 'Logout users for selected computers' ),
		method = 'roomadmin_italc_logout',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/italc/demo/start/window': umch.command(
		short_description = _( 'Start demo mode' ),
		long_description = _( 'Start demo mode for selected clients' ),
		method = 'roomadmin_italc_demo_start_window',
		values = { 'ipaddrs': _types.ipaddrs,
			'masterip': _types.masterip,
			'room': _types.room},
		priority = 90
	),
	'roomadmin/italc/demo/start/fullscreen': umch.command(
		short_description = _( 'Start demo mode' ),
		long_description = _( 'Start demo mode for selected clients' ),
		method = 'roomadmin_italc_demo_start_fullscreen',
		values = { 'ipaddrs': _types.ipaddrs,
			'masterip': _types.masterip,
			'room': _types.room},
		priority = 90
	),
	'roomadmin/italc/demo/stop': umch.command(
		short_description = _( 'Stop demo mode' ),
		long_description = _( 'Stop running demo mode' ),
		method = 'roomadmin_italc_demo_stop',
		values = {'room': _types.room},
		priority = 90
	),
	'roomadmin/italc/request/snapshot': umch.command(
		short_description = _( 'Request snapshot' ),
		long_description = _( 'Request snapshot for selected computers' ),
		method = 'roomadmin_italc_request_snapshot',
		values = { 'ipaddr': _types.ipaddr,
			'date': _types.date },
		priority = 90
	),
	'roomadmin/italc/request/data': umch.command(
		short_description = _( 'Request data' ),
		long_description = _( 'Request JSON encoded data' ),
		method = 'roomadmin_italc_request_data',
		values = { 'room' : _types.room,
			'date': _types.date },
		priority = 90
	),
	'roomadmin/italc/supervising/mode': umch.command(
		short_description = _( 'Supervising mode' ),
		long_description = _( 'Supervising mode' ),
		method = 'roomadmin_italc_supervising_mode',
		values = { 'room' : _types.room,
				   'ipaddrs': _types.ipaddrs, },
		priority = 90
	),
}

import inspect
def debugmsg( component, level, msg ):
	info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
	printInfo=[]
	if len(info[0])>20:
		printInfo.append('...'+info[0][-17:])
	else:
		printInfo.append(info[0])
	printInfo.extend(info[1:3])
	ud.debug(component, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))

class ItalcConnection (object):
	class states (object):
		Disconnected      = italc.ivsConnection.Disconnected
		Connecting        = italc.ivsConnection.Connecting
		Connected         = italc.ivsConnection.Connected
		HostUnreachable   = italc.ivsConnection.HostUnreachable
		ConnectionRefused = italc.ivsConnection.ConnectionRefused
		ConnectionFailed  = italc.ivsConnection.ConnectionFailed
		InvalidServer     = italc.ivsConnection.InvalidServer
		AuthFailed        = italc.ivsConnection.AuthFailed
		UnknownError      = italc.ivsConnection.UnknownError

	username_regex = re.compile( '^(?P<realname>[^(]+) +\((?P<username>[^ )]+)\)$' )

	def __init__ (self, ipaddr, role=italc.ISD.RoleTeacher, priviledged_user=None, ip2user=None):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.__init__: %s' % (ipaddr, ))
		self.ipaddr         = ipaddr
		self.role           = role
		self._worker        = None
		self._connector     = None
		self.ivs_connection = None
		# BUG: there is a bug in libitalc that prevents an ivsConnetion from
		# successfully calling demoServerRun and hideTrayIcon therefore a
		# separate isdConnection is needed
		self.isd_connection = None
		self.queue          = []
		self._ip2user = ip2user
		self._priviledged_user = priviledged_user
		self._user          = None
		self._username      = None
		self._realname      = None
		self._snapshot_size = (200, 150)
		self.allowed_clients = []
		self._lastmsg = time.time ()
		self._care_take_running = False
		self.reconnect_if_queue_empty = False

	def _care_taker (self):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._care_taker (%s)' % self.ipaddr)
		if not self._care_take_running:
			self._care_take_running = True

		def setUser (*args):
			if self.connected:
				user = self.ivs_connection.user ()
				if unicode (user) and user != self._user:
					if isinstance (user, PyQt4.QtCore.QString):
						user = unicode (user)

					self._username = None
					self._realname = None
					self._user = user
					debugmsg( ud.ADMIN, ud.INFO, \
							'ItalcConnection._care_taker.setUser: %s (%s)' % (user, self.ipaddr))

		# close connection if timeout is reached
		if (self._lastmsg + italc_connection_timeout) < time.time ():
			self.close ()
			self._care_take_running = False
			return False
		else:
			self.execute ('sendGetUserInformationRequest', callback=setUser, send_screen_updates=True)
		return True

	def _work (self, *args):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._work (%s)' % self.ipaddr)
		while self.queue and self.connected:
			action, action_args, callback, callback_args, send_screen_updates = self.queue.pop ()
			debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._work %s (%s)' % ((action, action_args, callback, callback_args, send_screen_updates), self.ipaddr))
			res = None
			# work around for certain commands that can only be executed by a
			# isdConnection
			connection = self.ivs_connection
			if action in ('hideTrayIcon', 'demoServerRun'):
				connection = self.isd_connection

			debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._work connection %s (%s)' % (connection, self.ipaddr))
			if hasattr (connection, action) and callable (getattr (connection, action)):
				try:
					debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._work: %s (%s)' % (action, self.ipaddr))
					res = getattr (connection, action) (*action_args)
					debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._work %s result: %s (%s)' % (action, res, self.ipaddr))
					# convert instances of QString to unicode since it's not
					# known what a QString can do to the system
					if isinstance (res, PyQt4.QtCore.QString):
						res = unicode (res)
				except:
					debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._work: (%s)\n%s' % (self.ipaddr, traceback.format_exc().replace('%','#')))
			else:
				debugmsg( ud.ADMIN, ud.INFO, "Action not available: %s (%s)" % (action, self.ipaddr))
			if callback and callable (callback):
				if res:
					callback_args.append (res)
				try:
					callback (*callback_args)
				except:
					debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._work: (%s)\n%s' % (self.ipaddr, traceback.format_exc().replace('%','#')))
			# run handleServerMessages to complete any started operation
			if connection == self.ivs_connection:
				connection.handleServerMessages (send_screen_updates)
			else:
				connection.handleServerMessages ()

			# Update information regarding the last message timeout
			if action not in ('sendGetUserInformationRequest', ):
				self._lastmsg = time.time ()
		if self.queue and self.connecting:
			time.sleep (1)
			self._work (*args)
		else:
			self._stop_worker ()
		if not self.queue and self.reconnect_if_queue_empty:
			debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._work: queue empty ==> reconnect (%s)' % (self.ipaddr, ))
			self.reconnect()

	def _start_worker (self):
		_d = ud.function('ItalcConnection._start_worker (%s)' % (self.ipaddr, ))
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection._start_worker: _worker=%s  connected=%s  connecting=%s (%s)' % (self._worker, self.connected, self.connecting, self.ipaddr ))
		if not self._worker and (self.connected or self.connecting):
			identifier = 'worker-%s-%d-%d' % (self.ipaddr, int (time.time()), random.randint (1, 10000))
			self._worker = threads.Simple (identifier, self._work, self._stop_worker)
			self._worker.run ()
		else:
			self._stop_worker ()

	def _stop_worker (self, *args):
		_d = ud.function('ItalcConnection._stop_worker (%s)' % (self.ipaddr, ))
		self._worker = None

	def async_open (self):
		_d = ud.function('ItalcConnection.async_open (%s)' % (self.ipaddr, ))
		def connector (*args):
			while not self.connected:
				self.open ()
				time.sleep (2)
			debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.async_open: connected to %s' % (self.ipaddr, ))

		def connector_done (*args):
			self._connector = None

		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.async_open: connecting=%s  connected=%s  _connector=%s (%s)' % (self.connecting, self.connected, self._connector, self.ipaddr ))
		if not (self.connecting or self.connected or self._connector):
			identifier = 'async_open-%s-%d-%d' % (self.ipaddr, int (time.time()), random.randint (1, 10000))
			self._connector = threads.Simple (identifier, connector, connector_done)
			self._connector.run ()
		if not self._care_take_running:
			notifier.timer_add (1000*italc_update_interval, self._care_taker)
			self._care_taker ()

	def open (self):
		_d = ud.function('ItalcConnection.open (%s)' % (self.ipaddr, ))
#		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.open (%s)' % (self.ipaddr, ))
		if not (self.connecting or self.connected):
			debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.open: not connected (%s)' % (self.ipaddr, ))
			ivs_connection = italc.ivsConnection (self.ipaddr)
			isd_connection = italc.isdConnection (self.ipaddr)
			if not (ivs_connection.initAuthentication(self.role) and isd_connection.initAuthentication(self.role)):
				debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.open Authentication failed: role=%d, IP address=%s' % (self.role, self.ipaddr))
				self.close ()
				return

			# 3 connection failed
			# 2 connection opened and successful authentication
			# 0 connection opened but authentication failed
			if ivs_connection.open () != 2 or isd_connection.open () != 2:
				self.close ()
				return

			self._lastmsg = time.time ()

			self.ivs_connection = ivs_connection
			self.isd_connection = isd_connection
			self.setSnapshotSize (self._snapshot_size[0], self._snapshot_size[1])

			if not self._care_take_running:
				notifier.timer_add (1000*italc_update_interval, self._care_taker)
				self._care_taker ()

	def close (self, flush = True ):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.close (%s)' % (self.ipaddr, ))
		if self.ivs_connection:
			try:
				self.ivs_connection.close ()
			except:
				pass
			self.ivs_connection = None
		if self.isd_connection:
			try:
				self.isd_connection.close ()
			except:
				pass
			self.isd_connection = None
		if flush:
			self._username = None
			self._realname = None
			self._user = None

	def set_reconnect_if_queue_empty(self):
		self.reconnect_if_queue_empty = True

	def reconnect(self):
		_d = ud.function('ItalcConnection.reconnect (%s)' % (self.ipaddr, ))
		self.reconnect_if_queue_empty = False
		self.close( flush = False)
		self.async_open()

	def allowClient (self, client):
		if client:
			if not self.allowed_clients.count (client):
				self.allowed_clients.append (client)
				self.execute ('demoServerAllowClient', [client])
				return client

	def denyClient (self, client):
		if client:
			if self.allowed_clients.count (client):
				self.allowed_clients.remove (client)
				self.execute ('demoServerDenyClient', [client])
				return client

	def denyAllClients (self):
		for client in self.allowed_clients[:]:
			self.denyClient (client)

	@property
	def state (self):
		if self.ivs_connection:
			return self.ivs_connection.state ()
		else:
			return ItalcConnection.states.Disconnected

	@property
	def connected (self):
		return self.state == ItalcConnection.states.Connected

	@property
	def connecting (self):
		return self.state == ItalcConnection.states.Connecting

	def execute (self, action, action_args=None, callback=None, callback_args=None, send_screen_updates=False):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.execute: %s (%s)' % ((action, action_args, callback, callback_args, send_screen_updates), self.ipaddr))
		if action_args is None:
			action_args = []
		if callback_args is None:
			callback_args = []
		if not (self.connected or self.connecting):
			if action in ('sendGetUserInformationRequest', ):
				debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.execute: False (%s)' % (self.ipaddr, ))
				return False
			self.async_open ()

		# Not all actions are desired on every computer:
		# do not perform action if iTALC username is equal to UMC username
		if (self.getUsername() and self._priviledged_user and self.getUsername() == self._priviledged_user) or (self._priviledged_user == self._ip2user.get(self.ipaddr)):
			debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.execute(): action against privileged user: action=%s  privUser=%s  getUsername=%s  ip2user[%s]=%s' % (action,
																																								self._priviledged_user,
																																								self.getUsername(),
																																								self.ipaddr,
																																								self._ip2user.get(self.ipaddr)))
			if action in ('lockDisplay', 'logoutUser', 'powerDownComputer', 'restartComputer'):
				return False
			if action == 'disableLocalInputs':
				if not action_args or action_args[0] == True:
					return False
			if action == 'startDemo':
				if not action_args or len (action_args) < 2:
					return False
				elif action_args[1] == True:
					action_args = list (action_args)
					action_args[1] = False

		self.queue.insert (0, (action, action_args, callback, callback_args, send_screen_updates))
		self._start_worker ()
		return True

	def getSnapshot (self):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.getSnapshot (%s)' % (self.ipaddr, ))
		self._lastmsg = time.time ()
		if self.connected:
			return self.ivs_connection.screen ()
		self.async_open ()
		return None

	def getScaledSnapshot (self):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.getScaledSnapshot (%s)' % (self.ipaddr, ))
		self._lastmsg = time.time ()
		if self.connected:
			return self.ivs_connection.scaledScreen ()
		return None

	def _writeSnapshot (self, qimage, filename, format='PNG'):
		self._lastmsg = time.time ()
		fmt = PyQt4.QtCore.QByteArray (format)
		return PyQt4.QtGui.QImageWriter (filename, fmt).write (qimage)

	def writeSnapshot (self, filename, format='PNG'):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.writeSnapshot (%s)' % (self.ipaddr, ))
		snapshot = self.getSnapshot ()
		if snapshot:
			return self._writeSnapshot (snapshot, filename, format)
		return None

	def writeScaledSnapshot (self, filename, format='PNG'):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.writeScaledSnapshot (%s)' % (self.ipaddr, ))
		snapshot = self.getScaledSnapshot ()
		if snapshot:
			return self._writeSnapshot (snapshot, filename, format)
		return None

	def _set_user_real_name (self):
		if self._user and not (self._username or self._realname):
			matches = ItalcConnection.username_regex.match (self._user)
			if matches:
				items = matches.groupdict ()
				self._username = items['username']
				self._realname = items['realname']
			else:
				self._username = self._user
				self._realname = None

	def getUsername (self):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.getUsername (%s)' % (self.ipaddr, ))
		self._set_user_real_name ()
		self._lastmsg = time.time ()
		if self.connected:
			return self._username
		self.async_open ()
		return None

	def getRealname (self):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.getRealname (%s)' % (self.ipaddr, ))
		self._set_user_real_name ()
		self._lastmsg = time.time ()
		if self.connected:
			return self._realname
		self.async_open ()
		return None

	def getUser (self):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.getUser (%s)' % (self.ipaddr, ))
		self._lastmsg = time.time ()
		if self.connected:
			return self._user
		self.async_open ()
		return None

	def setSnapshotSize (self, width, height):
		self._snapshot_size = (width, height)
		if self.connected:
			self.ivs_connection.setScaledSize (PyQt4.QtCore.QSize (self._snapshot_size[0], self._snapshot_size[1]))

	def getSnapshotSize (self):
		return self._snapshot_size

	@classmethod
	def getConnection (cls, ipaddr, priviledged_user=None, ip2user=None):
		debugmsg( ud.ADMIN, ud.INFO, 'ItalcConnection.getConnection (%s)' % ipaddr)
		con = None
		if italc_connections.has_key (ipaddr):
			con = italc_connections[ipaddr]
		else:
			italc_connections[ipaddr] = ItalcConnection (ipaddr, priviledged_user=priviledged_user, ip2user=ip2user)
			con = cls.getConnection (ipaddr)
		# WARNING: the connection will be opened, immediately 
		con.async_open ()
		return con

class handler( umch.simpleHandler, _revamp.Web  ):
	def __init__( self ):
		global command_description, italc_update_interval, italc_connection_timeout
		self._ip2user = {}
		umch.simpleHandler.__init__( self, command_description )
		_revamp.Web.__init__( self )

		# generate config objects
		self.configRegistry = univention.config_registry.ConfigRegistry()
		self.configRegistry.load()

		self.ldap_anon = _schoolldap.SchoolLDAPConnection()
		self.ldap_master = _schoolldap.SchoolLDAPConnection( ldapserver = self.configRegistry['ldap/master'] )

		if self.configRegistry.get('umc/roomadmin/italc/updateinterval'):
			try:
				italc_update_interval = int (self.configRegistry['umc/roomadmin/italc/updateinterval'])
			except ValueError:
				pass
			if italc_update_interval < 3:
				italc_update_interval = 3

		if self.configRegistry.get('umc/roomadmin/italc/timeout'):
			try:
				italc_connection_timeout = int (self.configRegistry['umc/roomadmin/italc/timeout'])
			except ValueError:
				pass
			if italc_connection_timeout < 30:
				italc_connection_timeout = 30

		debugmsg( ud.ADMIN, ud.INFO, 'availableOU=%s' % self.ldap_anon.availableOU )



	def _get_groups_and_computers( self, basedn_computers, basedn_groups ):
		"""
		returns ( groupdict, computerdict )

		groupdict[grpdn] = [ grpattrs, memberlist ]
		grpattrs = { 'attr': [ 'val1', 'val2' ], ... }
		memberlist = [ 'dn1', 'dn2', ... ]

		computerdict[ compdn ] = compattr
		compattr = { 'attr': [ 'val1', 'val2' ], ... }
		"""
		groupdict = {}
		computerdict = {}
		computer2grp = {}
		computerflag = {}

		if self.ldap_anon.checkConnection():
			computers = self.ldap_anon.lo.search( filter='objectClass=univentionHost', base=basedn_computers,
										scope='sub', attr=[ 'cn', 'macAddress', 'aRecord', 'objectClass', 'univentionServerRole', 'univentionInventoryNumber' ] )
			# iterate over all computer objects
			for compdn, compattr in computers:
				# create dict dn ==> ( attributes, used_flag )
				computerdict[ compdn ] = compattr
				computerflag[ compdn ] = 0

			debugmsg( ud.ADMIN, ud.INFO, 'got %d computer objects' % len(computerdict) )
#			debugmsg( ud.ADMIN, ud.INFO, 'computer objects = %s' % computerdict )

			debugmsg( ud.ADMIN, ud.INFO, 'basedn_groups=%s' % basedn_groups )
			try:
				groups = self.ldap_anon.lo.search( filter='objectClass=univentionGroup', base=basedn_groups,
												   scope='sub', attr=[ 'cn', 'uniqueMember', 'description' ] )
			except univention.admin.uexceptions.noObject:
				debugmsg( ud.ADMIN, ud.INFO, 'no rooms found' )
				groups = []
			except Exception, e:
				debugmsg( ud.ADMIN, ud.ERROR, 'getting rooms failed: %s' % str(e) )
				import sys
				info = sys.exc_info()
				lines = traceback.format_exc().replace('%','#')
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while getting rooms! Please consult local administrator.')
				groups = []

			debugmsg( ud.ADMIN, ud.INFO, 'groups=%s' % groups )
			# iterate over all groups
			for grpdn, grpattrs in groups:
				memberlist = []
				if grpattrs.has_key('uniqueMember'):

					# check all uniqueMembers
					for memberdn in grpattrs['uniqueMember']:
						# is uniqueMember a computer?
						if memberdn in computerdict:
							# mark computer entry as used
							computerflag[memberdn] = 1
							memberlist.append(memberdn)
				groupdict[grpdn] = [ grpattrs, memberlist ]

			debugmsg( ud.ADMIN, ud.INFO, 'got %d group objects' % len(groupdict) )
#			debugmsg( ud.ADMIN, ud.INFO, 'group objects = %s' % groupdict )

		return (groupdict, computerdict)


	def roomadmin_room_list( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadm	in_room_list: options=%s' % object.options )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		groupdict = {}
		computerdict = {}

		for ou in self.ldap_anon.availableOU:
			self.ldap_anon.switch_ou(ou)
			(tmpgroupdict, tmpcomputerdict) = self._get_groups_and_computers( self.ldap_anon.searchbaseComputers, self.ldap_anon.searchbaseRooms )
			groupdict.update(tmpgroupdict)
			computerdict.update(tmpcomputerdict)

		# get all ip addresses blocked for internet access
		computers_blocked4internet = []

		umc.registry.load()
		keylist = umc.registry.keys()
		for key in keylist:
			if key.startswith('proxy/filter/hostgroup/blacklisted/'):
				value = umc.registry[ key ]

				computers_blocked4internet.extend( value.split(' ') )

		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_list: computers_blocked4internet=%s' % computers_blocked4internet )


		cmd = '/usr/bin/smbstatus -b'
		result = umct.run_process( cmd, timeout = 0, output = True )

#root@master30:/root# smbstatus -b
#
#Samba version 3.2.13
#PID     Username      Group         Machine
#-------------------------------------------------------------------
#23355   schueler312   Account Operators  007bondpc    (10.200.18.100)
#18646     Administrator  Domain Admins  labor-pc2    (::ffff:10.200.10.152)
#4764      g.lehmann1    Domain Users musterschule  winxpsp3-italc (::ffff:10.200.10.143)

		buffer = result.get('stdout','').read().split('\n')

		self._ip2user.clear()
		host2user = {}
		user2realname = {}
		userlist = []
		regex = re.compile( '^\s*?(?P<pid>[0-9]+)\s\s+(?P<username>[^ ]+)\s\s+(?P<group>.+)\s\s+(?P<host>[^ ]+)\s+\((::ffff:)?(?P<ipaddr>[.0-9]+)\)\s*$' )

		debugmsg( ud.ADMIN, ud.INFO, 'smbstatus -b: (%s)\n%s' % (result.get('exit'), '\n'.join(buffer)) )

		for line in buffer:
			matches = regex.match(line)
			if matches:
				items = matches.groupdict()
				username = items['username'].strip()
				# if this line describes the login of a machine account it should be ignored
				if username[ -1 ] == '$':
					continue
				host2user[ items['host'].strip().lower() ] = username
				self._ip2user[ items['ipaddr'].strip() ] = username
				userlist.append( username )

		debugmsg( ud.ADMIN, ud.INFO, 'host2user=%s' % host2user )

		if self.ldap_anon.checkConnection(username = self._username, bindpw = self._password):
			while userlist:
				# get only 10 user realnames at a time
				usersubset = userlist[0:10]
				del userlist[0:10]

				filter = '(|'
				for user in usersubset:
					filter += '(uid=%s)' % user
				filter += ')'
				users = self.ldap_anon.lo.search( filter=filter, base=self.configRegistry[ 'ldap/base' ],
												  scope='sub', attr=[ 'cn', 'uid' ] )
				# iterate over all groups
				for userdn, userattrs in users:
					if userattrs.has_key('cn'):
						user2realname[ userattrs['uid'][0] ] = userattrs['cn'][0]

#		debugmsg( ud.ADMIN, ud.INFO, 'user2realname=%s' % user2realname )

		# get ip addresses of current group
		room = object.options.get( 'room', None )

		curgrpmembers = {}
		for grpdn, grpdata in groupdict.items():
			if grpdata[0]['cn'][0] == room:
				curgrpmembers = grpdata[1]

		if room == '::all':
			curgrpmembers = computerdict.keys()


		hideitems = self.configRegistry.get('umc/roomadmin/hideitems','').lower().replace(" ","").split(',')

		demomode = {}

		if room and os.path.isfile (os.path.sep.join ((italc_demostorage_path, room))):
			try:
				# restore persistent demo mode details
				fd = open (os.path.sep.join ((italc_demostorage_path, room)), 'r')
				demomode = JsonReader ().read (fd.read ())
				fd.close ()
			except:
				debugmsg( ud.ADMIN, ud.ERROR, '_roomadmin_room_list_return: unable to restore demo mode details\n%s' % traceback.format_exc().replace('%','#'))

		cmd = '/usr/bin/fping -C1'
		ipaddrs = []
		runfping = False
		for memberdn in curgrpmembers:
			computer = computerdict[memberdn]
			if computer.has_key('aRecord') and computer['aRecord']:
				cmd += ' %s' % computer['aRecord'][0]
				ipaddrs.append (computer['aRecord'][0])
				runfping = True

		if not runfping:
			debugmsg( ud.ADMIN, ud.INFO, 'do not call fping' )
			self.finished( object.id(), ( computers_blocked4internet, groupdict, computerdict, host2user, user2realname, {}, demomode, hideitems ) )
			return

		debugmsg( ud.ADMIN, ud.INFO, 'cmd=%s' % cmd )

		result = umct.run_process( cmd, timeout = 0, output = True )

#root@master30:/root# fping -C1 10.200.18.30 10.200.18.31 10.200.18.100 10.200.18.32 > /dev/null
#10.200.18.30  : 0.54
#10.200.18.31  : -
#10.200.18.100 : 0.53
#10.200.18.32  : -

		try:
			bufstdout = result.get('stdout').read()
		except:
			bufstdout = ''
		try:
			bufstderr = result.get('stderr').read()
		except:
			bufstderr = ''
		debugmsg( ud.ADMIN, ud.INFO, '%s: (%s)\n%s\n---\n%s' % (cmd, result.get('exit'), bufstdout, bufstderr))
		onlinestatus={}

		regex = re.compile( '^(?P<ipaddr>[.0-9]+) +\: (?P<status>[-.0-9]+)$' )

		for line in bufstderr.splitlines():
			matches = regex.match(line)
			if matches:
				items = matches.groupdict()
				onlinestatus[ items['ipaddr'] ] = (items['status'] != '-')

		# find user names via italc connection
		for ip in ipaddrs:
			con = ItalcConnection.getConnection (ip, priviledged_user=self._username, ip2user=self._ip2user)
			if not host2user.has_key (ip) and con.connected:
				for dn in computerdict.keys ():
					if computerdict[dn].has_key ('aRecord') \
							and ip in computerdict[dn]['aRecord'] \
							and computerdict[dn].has_key ('cn') \
							and computerdict[dn]['cn']:
						cn = computerdict[dn]['cn'][0]
						onlinestatus[ip] = True

						username = con.getUsername ()
						realname = con.getRealname ()
						if username and realname:
							host2user[cn] = username
							user2realname[username] = realname
						elif con.getUser ():
							host2user[cn] = con.getUser ()

		debugmsg( ud.ADMIN, ud.INFO, 'onlinestatus=%s' % onlinestatus )

		# try again to read demostorage file
		room = object.options.get( 'room', None )
		if room and os.path.isfile (os.path.sep.join ((italc_demostorage_path, room))):
			try:
				# restore persistent demo mode details
				fd = open (os.path.sep.join ((italc_demostorage_path, room)), 'r')
				demomode = JsonReader ().read (fd.read ())
				fd.close ()
			except:
				debugmsg( ud.ADMIN, ud.ERROR, '_roomadmin_room_list_return2: unable to restore demo mode details\n%s' % traceback.format_exc().replace('%','#'))

		self.finished( object.id(), ( computers_blocked4internet, groupdict, computerdict, host2user, user2realname, onlinestatus, demomode, hideitems ) )


	def _get_option( self, object, key, default = None ):
		if object.options.has_key( key ):
			return object.options[ key ]
		return default


	def roomadmin_wol_send( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_wol_send: options=%s' % object.options )

		ipaddrs = object.options.get('ipaddrs', None)

		ipfilter = ''
		for ipaddr in ipaddrs:
			ipfilter += '(aRecord=%s)' % ipaddr
		maclist = []

		if self.ldap_anon.checkConnection():
			computers = self.ldap_anon.lo.search( filter='(&(objectClass=univentionHost)(|%s))' % ipfilter,
												  base=self.ldap_anon.searchbaseComputers,
												  scope='sub',
												  attr=[ 'cn', 'macAddress', 'aRecord', 'objectClass' ] )

			# iterate over all found computer objects
			for compdn, compattr in computers:
				maclist.extend( compattr.get('macAddress',[]) )

		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_wol_send: waking up following systems: %s' % str(maclist) )
		if maclist:
			for mac in maclist:
				proc = notifier.popen.Shell( '/usr/bin/wakeonlan %s' % mac, stdout = False, stderr = False )
				proc.start()
				# start process in background
				time.sleep(0.15)
				notifier.step()
				time.sleep(0.15)
				notifier.step()
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_wol_send: all magic packets sent' )

		self.finished( object.id(), () )


	def roomadmin_set_access_internet_enable( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_set_access_internet_enable: options=%s' % object.options )

		ipaddrs = object.options.get('ipaddrs', None)

		umc.registry.load()
		keylist = umc.registry.keys()
		for key in keylist:
			if key.startswith('proxy/filter/hostgroup/blacklisted/'):
				blockedlist = umc.registry[ key ].split(' ')

				# remove selected ip addresses from blocklist
				blockedlist = [ x for x in blockedlist if x not in ipaddrs ]

				if not blockedlist:
					univention.config_registry.handler_unset( [ key ] )
					debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_set_access_internet_enable: removed %s' % key )
				else:
					univention.config_registry.handler_set( [ '%s=%s'  % (key.encode(), ' '.join(blockedlist).encode()) ] )

		self.finished( object.id(), () )


	def roomadmin_set_access_internet_disable( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_set_access_internet_disable: options=%s' % object.options )

		ipaddrs = object.options.get('ipaddrs', None)

		if ipaddrs:
			key = 'proxy/filter/hostgroup/blacklisted/global'
			umc.registry.load()
			if umc.registry.has_key(key):
				blockedlist = umc.registry[ key ].split(' ')
				blockedlist = [ x for x in blockedlist if x not in ipaddrs ]
			else:
				blockedlist = []
			blockedlist.extend(ipaddrs)
			univention.config_registry.handler_set( [ '%s=%s'  % (key.encode(), ' '.join(blockedlist).encode()) ] )

		self.finished( object.id(), () )


	def roomadmin_room_search( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_search=%s' % object.options )

		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		# get searchfilter
		sfilter = object.options.get('filter', '*')

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_anon.switch_ou( '438' )
			self.ldap_master.switch_ou( '438' )
		else:
			if object.options.get('ou',None):
				self.ldap_anon.switch_ou( object.options.get('ou') )
				self.ldap_master.switch_ou( object.options.get('ou') )

		roomgroupdict = {}
		computerdict = {}

		if not object.incomplete:
			(tmpgroupdict, tmpcomputerdict) = self._get_groups_and_computers( self.ldap_anon.searchbaseComputers, self.ldap_anon.searchbaseRooms )
			roomgroupdict.update(tmpgroupdict)
			computerdict.update(tmpcomputerdict)

			debugmsg( ud.ADMIN, ud.INFO, 'roomgroupdict=%s' % roomgroupdict )
			# remove nonmatching groups
			for key in roomgroupdict.keys():
				searchkey = 'cn'
				if object.options.get('key','') in [ 'description' ]:
					searchkey = object.options.get('key')
				if roomgroupdict[key][0].has_key(searchkey):
					if not fnmatch.fnmatch( roomgroupdict[key][0][searchkey][0], sfilter ):
						del roomgroupdict[key]
				else:
					del roomgroupdict[key]

		self.finished( object.id(), (self.ldap_anon.availableOU, roomgroupdict) )


	def roomadmin_room_edit( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_edit=%s' % object.options )

		if not self.ldap_master.checkConnection(username = self._username, bindpw = self._password):
			self.finished( object.id(), None,
						   report = _( 'No admin connection to the LDAP database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_master.switch_ou( '438' )
			self.ldap_anon.switch_ou( '438' )
		else:
			if object.options.get('ou',None):
				self.ldap_master.switch_ou( object.options.get('ou') )
				self.ldap_anon.switch_ou( object.options.get('ou') )

		# get room DN and room description
		roomdn = object.options.get( 'roomdn', None )
		description = object.options.get( 'description', None )
		if description == None and roomdn:
			try:
				result = univention.admin.modules.lookup( self.ldap_master.groupmodule, self.ldap_master.co, self.ldap_master.lo,
														  scope = 'sub', superordinate = None,
														  base = roomdn, filter = '')
				if result and result[0]:
					room = result[0]
					room.open()
					description = room['description']
			except Exception, e:
				debugmsg( ud.ADMIN, ud.ERROR, 'getting room description failed (room=%s): %s' % (roomdn, e) )
				import sys
				info = sys.exc_info()
				lines = traceback.format_exc().replace('%','#')
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while getting group description! Please consult local administrator.')
		else:
			description = None

		# get computers assigned to selected room
		roommember = self.ldap_master.get_group_member_list( roomdn, filterbase=self.ldap_master.searchbaseComputers, attrib='hosts' )

		roomnamedefault = None
		if self.configRegistry.get('umc/roomadmin/groups/defaultgroupprefix'):
			roomnamedefault = self.configRegistry['umc/roomadmin/groups/defaultgroupprefix']
			roomnamedefault = roomnamedefault % { 'departmentNumber': self.ldap_master.departmentNumber }
			debugmsg( ud.ADMIN, ud.INFO, 'roomnamedefault = %s' % roomnamedefault)

		self.finished( object.id(), ( self.ldap_master.availableOU, self.ldap_master.searchbaseComputers, description, roommember, roomnamedefault ) )


	def roomadmin_room_add( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_add=%s' % object.options )

		if not self.ldap_master.checkConnection(username = self._username, bindpw = self._password):
			self.finished( object.id(), None,
						   report = _( 'No admin connection to the LDAP database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_master.switch_ou( '438' )
			self.ldap_anon.switch_ou( '438' )
		else:
			if object.options.get('ou',None):
				self.ldap_master.switch_ou( object.options.get('ou') )
				self.ldap_anon.switch_ou( object.options.get('ou') )

		description = None
		roommember = []

		roomnamedefault = None
		if self.configRegistry.get('umc/roomadmin/groups/defaultgroupprefix'):
			roomnamedefault = self.configRegistry['umc/roomadmin/groups/defaultgroupprefix']
			roomnamedefault = roomnamedefault % { 'departmentNumber': self.ldap_master.departmentNumber }
			debugmsg( ud.ADMIN, ud.INFO, 'roomnamedefault = %s' % roomnamedefault)

		self.finished( object.id(), ( self.ldap_master.availableOU, self.ldap_master.searchbaseComputers, description, roommember, roomnamedefault ) )


	def roomadmin_room_set( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_set=%s' % object.options )

		# test if user is allowed to execute roomadmin/room/add
		if not object.options.get('roomdn',False) and not self.permitted('roomadmin/room/add', {} ):
			debugmsg( ud.ADMIN, ud.ERROR, _('user is not allowed to execute %s') % 'roomadmin/room/add')
			self.finished( object.id(), None,
						   report = _( 'You are not allowed to execute this action. Please contact local administrator.' ),
						   success = False )
			return

		# test if user is allowed to execute roomadmin/room/edit
		if object.options.get('roomdn',False) and not self.permitted('roomadmin/room/edit', {} ):
			debugmsg( ud.ADMIN, ud.ERROR, _('user is not allowed to execute %s') % 'roomadmin/room/edit')
			self.finished( object.id(), None,
						   report = _( 'You are not allowed to execute this action. Please contact local administrator.' ),
						   success = False )
			return


# {  'roomdn': u'cn=002-Raum017b,cn=raeume,cn=groups,ou=002,dc=schule,dc=bremen,dc=de',
#	 'roommembers': [u'cn=win002-01,cn=computers,ou=002,dc=schule,dc=bremen,dc=de',
#						u'cn=w002pc01,cn=computers,ou=002,dc=schule,dc=bremen,dc=de',
#						u'cn=w002pc02,cn=computers,ou=002,dc=schule,dc=bremen,dc=de',
#						u'cn=w002pc03,cn=computers,ou=002,dc=schule,dc=bremen,dc=de'],
#	 'createroom': False,
#	 'description': u'Beschreibung',
# 	 'room': u'002-Raum017b'
# }

		if not self.ldap_master.checkConnection(username = self._username, bindpw = self._password):
			self.finished( object.id(), None,
						   report = _( 'No admin connection to the LDAP database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_anon.switch_ou('438')
			self.ldap_master.switch_ou('438')
		else:
			if object.options.get('ou',None):
				self.ldap_anon.switch_ou( object.options.get('ou') )
				self.ldap_master.switch_ou( object.options.get('ou') )

		roomdn = object.options.get( 'roomdn', None )
		room = object.options.get( 'room', None )
		roommembers = object.options.get( 'roommembers', None )
		description = object.options.get( 'description', None )

		report = ''

		if roommembers == None:
			debugmsg( ud.ADMIN, ud.ERROR, 'cannot change room members: roommembers == None')
			self.finished( object.id(), None, success = False, report = _( 'Cannot change room members') )
			return

		if roomdn:
			# change room (group) object
			report = ''

			try:
				groupresult = univention.admin.modules.lookup( self.ldap_master.groupmodule, self.ldap_master.co, self.ldap_master.lo,
															   scope = 'sub', superordinate = None,
															   base = roomdn, filter = '')
				if groupresult and groupresult[0]:
					gr = groupresult[0]
					gr.open()
					gr['description'] = description
					gr['hosts'] = roommembers
					dn = gr.modify()
			except Exception, e:
				debugmsg( ud.ADMIN, ud.ERROR, 'change of room members failed (group=%s): %s' % (roomdn, e) )
				import sys
				info = sys.exc_info()
				lines = traceback.format_exc().replace('%','#')
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while updating room! Please consult local administrator. (%s)') % ''.join(traceback.format_exception_only(*(info[0:2])))
		else:
			# no roomdn present ==> create new room (group)

			tmpPosition = univention.admin.uldap.position(self.configRegistry['ldap/base'])
			tmpPosition.setDn(self.ldap_master.searchbaseRooms)

			try:
				groupObject=self.ldap_master.groupmodule.object(self.ldap_master.co, self.ldap_master.lo, position=tmpPosition)
				groupObject.open()
				groupObject.options = [ 'posix' ]
				groupObject['name'] = room
				groupObject['description'] = description
				groupObject['hosts'] = roommembers
				dn = groupObject.create()
				debugmsg( ud.ADMIN, ud.INFO, 'created object %s' % dn )

			except univention.admin.uexceptions.objectExists:
				debugmsg( ud.ADMIN, ud.WARN, 'creating room %s failed: objectExists' % room )
				report = _('Cannot create room - object already exists!')
			except univention.admin.uexceptions.groupNameAlreadyUsed:
				debugmsg( ud.ADMIN, ud.WARN, 'creating room %s failed: groupNameAlreadyUsed' % room )
				report = _('Cannot create room - groupname already used!')
			except Exception, e:
				import sys
				info = sys.exc_info()
				lines = traceback.format_exc().replace('%','#')
				debugmsg( ud.ADMIN, ud.ERROR, 'creating room %s at %s failed: %s' % (room, tmpPosition.getDn(), ''.join(traceback.format_exception_only(*(info[0:2])))) )
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while creating room! Please consult local administrator.  (%s)') % ''.join(traceback.format_exception_only(*(info[0:2])))

		self.finished( object.id(), ( ), success = (len(report) == 0), report = report )


	def roomadmin_room_remove( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_remove=%s' % object.options )

		if not self.ldap_master.checkConnection(username = self._username, bindpw = self._password):
			self.finished( object.id(), None,
						   report = _( 'No admin connection to the LDAP database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_anon.switch_ou('438')
			self.ldap_master.switch_ou('438')
		else:
			if object.options.get('ou',None):
				self.ldap_anon.switch_ou( object.options.get('ou') )
				self.ldap_master.switch_ou( object.options.get('ou') )

		roomdnlist = object.options.get( 'roomdn', [] )
		confirmed = object.options.get( 'confirmed', False )

		message = []

		if confirmed:
			for dn in roomdnlist:
				try:
					tmpPosition = univention.admin.uldap.position(self.ldap_master.searchbaseRooms)
					obj = univention.admin.objects.get( self.ldap_master.groupmodule, self.ldap_master.co,
														self.ldap_master.lo, tmpPosition, dn = dn )
					obj.open()
					obj.remove()
					ud.debug( ud.ADMIN, ud.ERROR, 'removed %s' % dn )
				except Exception, e:
					ud.debug( ud.ADMIN, ud.ERROR, 'removal of group %s failed: %s' % (dn, e) )
					message.append( dn )
					import sys
					info = sys.exc_info()
					lines = traceback.format_exc().replace('%','#')
					ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK:\n%s' % lines )

		roomdnlist = sorted( roomdnlist )

		ud.debug( ud.ADMIN, ud.INFO, 'confirmed=%s  roomdnlist=%s' % (confirmed, roomdnlist))

		self.finished( object.id(), (self.ldap_master.availableOU, len(message)==0, message) )

	def _roomadmin_italc_exec_action ( self, action, object, args=None, finish_args=None ):
		debugmsg( ud.ADMIN, ud.INFO, '_roomadmin_italc_exec_action: action=%s, options=%s' % (action, object.options) )

		if args is None:
			args = []
		if finish_args is None:
			finish_args = []
		ipaddrs = object.options.get('ipaddrs', None)

		if ipaddrs:
			for ip in ipaddrs:
				con = ItalcConnection.getConnection (ip, priviledged_user=self._username, ip2user=self._ip2user)
				con.execute (action, args)

		self.finished( object.id(), finish_args )

	def roomadmin_italc_reboot ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_reboot: options=%s' % object.options )

		self._roomadmin_italc_exec_action ('restartComputer', object)

	def roomadmin_italc_shutdown ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_shutdown: options=%s' % object.options )

		self._roomadmin_italc_exec_action ('powerDownComputer', object)

	def roomadmin_italc_lock_screen ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_lock_screen: options=%s' % object.options )

		self._roomadmin_italc_exec_action ('lockDisplay', object)

	def roomadmin_italc_unlock_screen ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_unlock_screen: options=%s' % object.options )

		self._roomadmin_italc_exec_action ('unlockDisplay', object)

	def roomadmin_italc_lock_input ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_lock_input: options=%s' % object.options )

		self._roomadmin_italc_exec_action ('disableLocalInputs', object, [True])

	def roomadmin_italc_unlock_input ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_unlock_input: options=%s' % object.options )

		self._roomadmin_italc_exec_action ('disableLocalInputs', object, [False])

	def roomadmin_italc_logout ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_logout: options=%s' % object.options )

		self._roomadmin_italc_exec_action ('logoutUser', object)

	def roomadmin_italc_demo_start_fullscreen ( self, object ):
		self._roomadmin_italc_demo_start (object, fullscreen=True)

	def roomadmin_italc_demo_start_window ( self, object ):
		self._roomadmin_italc_demo_start (object, fullscreen=False)

	def _roomadmin_italc_demo_start ( self, object, fullscreen=False ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_start: options=%s' % object.options )

		masterip = object.options.get('masterip', None)
		ipaddrs = object.options.get('ipaddrs', None)
		room = object.options.get('room', None)

		def startClientDemo (*args):
			debugmsg( ud.ADMIN, ud.ERROR, 'startClientDemo')
			for ipaddr in ipaddrs:
				if ipaddr and ipaddr != masterip:
					client_con = ItalcConnection.getConnection (ipaddr, priviledged_user=self._username, ip2user=self._ip2user)
					if client_con.connected or client_con.connecting:
						demoserver_db['ipaddrs'].append (ipaddr)
						client_con.execute ('stopDemo')
						client_con.execute ('unlockDisplay')
						client_con.execute ('disableLocalInputs', (False, ))
						client_con.execute ('startDemo', ('%s:%d' % (master_con.ipaddr, port), fullscreen))
					else:
						debugmsg( ud.ADMIN, ud.ERROR, 'startClientDemo: ignoring not connected client %s' % ipaddr)

			# persistently store the details of the demo mode
			try:
				fd = open (os.path.sep.join ((italc_demostorage_path, room)), 'w')
				fd.write (JsonWriter ().write (demoserver_db))
				fd.close ()
			except:
				debugmsg( ud.ADMIN, ud.ERROR, 'roomadmin_italc_demo_start: unable to store demo mode details\n%s' % traceback.format_exc().replace('%','#'))


		if not room or room != '::all' or os.path.exists (os.path.sep.join ((italc_demostorage_path, room))):
			self.finished( object.id(), None )
			# TODO: display appropriate error message

		if masterip and ipaddrs:
			master_con = ItalcConnection.getConnection (masterip, priviledged_user=self._username, ip2user=self._ip2user)
			if master_con.connected:
				port = 5858
				demoserver_db = {'masterip': masterip, 'ipaddrs': []}

				debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_start: connected')
				# the port number should be a random int
				master_con.execute ('stopDemo')
				master_con.denyAllClients ()
				master_con.execute ('demoServerRun', (italc.ivsConnection.QualityLow, port), startClientDemo)
				for ipaddr in ipaddrs:
					if ipaddr and ipaddr != masterip:
						master_con.allowClient (ipaddr)
			else:
				debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_start: disconnected')

		cb = notifier.Callback( self._roomadmin_italc_demo_start_delay_callback, object )
		notifier.timer_add(2000, cb)
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_start: umc response delayed')

	def _roomadmin_italc_demo_start_delay_callback(self, object):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_start_delay_callback: sending umc response')
		self.finished( object.id(), None )
		return False

	def roomadmin_italc_demo_stop ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_stop: options=%s' % object.options )
		room = object.options.get('room', None)
		demoserver_db = None

		if room and os.path.isfile (os.path.sep.join ((italc_demostorage_path, room))):
			try:
				# restore persistent demo mode details
				fd = open (os.path.sep.join ((italc_demostorage_path, room)), 'r')
				demoserver_db = JsonReader ().read (fd.read ())
				fd.close ()
			except:
				debugmsg( ud.ADMIN, ud.ERROR, 'roomadmin_italc_demo_stop: unable to restore demo mode details\n%s' % traceback.format_exc().replace('%','#'))
				self.finished( object.id(), None )
				return

			for clientip in demoserver_db['ipaddrs']:
				client_con = ItalcConnection.getConnection (clientip, priviledged_user=self._username, ip2user=self._ip2user)
				client_con.execute ('stopDemo')
				if client_con.connected:
					debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_stop client: %s connected' % client_con.ipaddr)
				else:
					debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_stop client: %s disconnected' % client_con.ipaddr)

			if demoserver_db['masterip']:
				master_con = ItalcConnection.getConnection (demoserver_db['masterip'], priviledged_user=self._username, ip2user=self._ip2user)
				master_con.denyAllClients ()
				master_con.execute ('stopDemo')
				if master_con.connected:
					debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_stop master: %s connected' % master_con.ipaddr)
				else:
					debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_demo_stop master: %s disconnected' % master_con.ipaddr)
				master_con.set_reconnect_if_queue_empty()
			# finally delete the demo mode details
			os.unlink (os.path.sep.join ((italc_demostorage_path, room)))

		self.finished( object.id(), None )

	def roomadmin_italc_request_snapshot ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_request_snapshot: options=%s' % object.options )

		ipaddr = object.options.get('ipaddr', None)
		content_type = 'image/png'
		content = ''
		if ipaddr:
			con = ItalcConnection.getConnection (ipaddr, priviledged_user=self._username, ip2user=self._ip2user)
			snapshot = con.getScaledSnapshot ()
			if snapshot:
				try:
					ba = PyQt4.QtCore.QByteArray ()
					buf = PyQt4.QtCore.QBuffer (ba)
					buf.open (PyQt4.QtCore.QIODevice.WriteOnly)
					snapshot.save (buf, 'PNG')
					content = ba.data ()
				except:
					debugmsg( ud.ADMIN, ud.ERROR, 'roomadmin_italc_request_snapshot: TRACEBACK WHILE PREPARING SCREENSHOT=\n%s' % str(traceback.format_exc().replace('%','#')) )
			elif con.connected or con.connecting:
				try:
					fd = open ('/var/www/univention-management-console/themes/images/default/misc/roomadmin/loading.png', 'r')
					content = fd.read ()
					fd.close ()
				except:
					debugmsg( ud.ADMIN, ud.ERROR, 'roomadmin_italc_request_snapshot: TRACEBACK WHILE PREPARING DEFAULT SCREENSHOT=\n%s' % str(traceback.format_exc().replace('%','#')) )
		if not len (content):
			debugmsg( ud.ADMIN, ud.ERROR, 'roomadmin_italc_request_snapshot: No Screenshot found' )
			try:
				fd = open ('/var/www/univention-management-console/themes/images/default/misc/roomadmin/no.png', 'r')
				content = fd.read ()
				fd.close ()
			except:
				debugmsg( ud.ADMIN, ud.ERROR, 'roomadmin_italc_request_snapshot: TRACEBACK WHILE PREPARING DEFAULT SCREENSHOT=\n%s' % str(traceback.format_exc().replace('%','#')) )

		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_request_snapshot: prepared "%s" with length %d' % ( content_type, len(content)) )
		self.finished( object.id(), ( content_type, content ) )

	def roomadmin_italc_request_data ( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_request_data: options=%s' % object.options )
		content_type = 'application/json'
		#content_type = 'text/json-comment-filtered'
		content = ''

		data = {}
		data['identifier'] = 'ipaddr'
		data['label'] = 'roomadmin data'
		data['items'] = []
		for ipaddr in italc_connections.keys ():
			con = ItalcConnection.getConnection (ipaddr, priviledged_user=self._username, ip2user=self._ip2user)
			if con and con.connected:
				item = {}
				if con.getUser ():
					item['username'] = con.getUser ()
				if item:
					item['ipaddr'] = ipaddr
					data['items'].append (item)
		try:
			json = JsonWriter ()
			content = json.write (data)
		except:
			debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_request_data: failed to create JSON: %s' % (traceback.format_exc().replace('%','#')) )

		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_request_data: prepared "%s" with length %s' % (content_type, content) )
		self.finished( object.id(), ( content_type, content ) )

	def roomadmin_italc_supervising_mode( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_italc_supervising_mode: options=%s' % object.options )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		groupdict = {}
		computerdict = {}

		for ou in self.ldap_anon.availableOU:
			self.ldap_anon.switch_ou(ou)
			(tmpgroupdict, tmpcomputerdict) = self._get_groups_and_computers( self.ldap_anon.searchbaseComputers, self.ldap_anon.searchbaseRooms )
			groupdict.update(tmpgroupdict)
			computerdict.update(tmpcomputerdict)

		resultlist = []
		ipaddrs = object.options.get( 'ipaddrs', [] )
		for compdn, comp in computerdict.items():
			ipaddr = comp.get('aRecord',[''])[0]

			if ipaddr in ipaddrs:
				username = _('unknown')
				realname = _('unknown')

				con = ItalcConnection.getConnection (ipaddr, priviledged_user=self._username, ip2user=self._ip2user)
				if con.connected:
					username = con.getUsername ()
					realname = con.getRealname ()
					if not username and not realname:
						username = con.getUser()
						realname = _('unknown')

				resultlist.append( { 'objectClass': comp['objectClass'],
									 'hostname': comp['cn'][0],
									 'aRecord': ipaddr,
									 'username': username,
									 'realname': realname,
									 } )

		self.finished( object.id(), ( resultlist ) )
