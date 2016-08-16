#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
#
# Copyright 2012-2016 Univention GmbH
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
import re
import subprocess
import tempfile
import threading
import time

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.config import ucr

from univention.admin.uexceptions import noObject

from ucsschool.lib.schoolldap import LDAP_Connection
from ucsschool.lib.models import User, ComputerRoom, MultipleObjectsError

import notifier
import notifier.signals
import notifier.threads

from PyQt4.QtCore import QObject, pyqtSlot
from PyQt4.QtGui import QImageWriter

import italc
import ldap
import sip
from ldap.filter import filter_format
from ldap.dn import explode_dn

_ = Translation('ucs-school-umc-computerroom').translate

ITALC_DEMO_PORT = int(ucr.get('ucsschool/umc/computerroom/demo/port', 11400))
ITALC_VNC_PORT = int(ucr.get('ucsschool/umc/computerroom/vnc/port', 11100))
ITALC_VNC_UPDATE = float(ucr.get('ucsschool/umc/computerroom/vnc/update', 1))
ITALC_CORE_UPDATE = max(1, int(ucr.get('ucsschool/umc/computerroom/core/update', 1)))
ITALC_CORE_TIMEOUT = max(1, int(ucr.get('ucsschool/umc/computerroom/core/timeout', 10)))

italc.ItalcCore.init()

italc.ItalcCore.config.setLogLevel(italc.Logger.LogLevelDebug)
italc.ItalcCore.config.setLogToStdErr(True)
italc.ItalcCore.config.setLogFileDirectory('/var/log/univention/')
italc.Logger('ucs-school-umc-computerroom')
italc.ItalcCore.config.setLogonAuthenticationEnabled(False)

italc.ItalcCore.setRole(italc.ItalcCore.RoleTeacher)
italc.ItalcCore.initAuthentication(italc.AuthenticationCredentials.PrivateKey)


class ITALC_Error(Exception):
	pass


class UserInfo(object):

	def __init__(self, ldap_dn, username, isTeacher=False, hide_screenshot=False):
		self.dn = ldap_dn
		self.isTeacher = isTeacher
		self.username = username
		self.hide_screenshot = hide_screenshot


class UserMap(dict):

	USER_REGEX = re.compile(r'(?P<username>[^(]*)( \((?P<realname>[^)]*)\))?$')

	def __getitem__(self, user):
		if user not in self:
			self._read_user(user)
		return dict.__getitem__(self, user)

	@LDAP_Connection()
	def _read_user(self, userstr, ldap_user_read=None):
		match = self.USER_REGEX.match(userstr)
		if not match or not userstr:
			raise AttributeError('invalid key "%s"' % userstr)
		username = match.groupdict()['username']
		if not username:
			raise AttributeError('username missing: %s' % userstr)

		lo = ldap_user_read
		try:
			userobj = User.get_only_udm_obj(lo, filter_format('uid=%s', (username,)))
			if userobj is None:
				raise noObject(username)
			user = User.from_udm_obj(userobj, None, lo)
		except (noObject, MultipleObjectsError):
			MODULE.info('Unknown user "%s"' % username)
			dict.__setitem__(self, userstr, UserInfo('', ''))
			return

		blacklisted_groups = set([x.strip().lower() for x in ucr.get('ucsschool/umc/computerroom/hide_screenshots/groups', 'Domain Admins').split(',')])
		users_groupmemberships = set([explode_dn(x, True)[0].lower() for x in userobj['groups']])
		MODULE.info('UserMap: %s: hide screenshots for following groups: %s' % (username, blacklisted_groups,))
		MODULE.info('UserMap: %s: user is member of following groups: %s' % (username, users_groupmemberships,))
		hide_screenshot = bool(blacklisted_groups & users_groupmemberships)

		if ucr.is_true('ucsschool/umc/computerroom/hide_screenshots/teachers', False) and user.is_teacher(lo):
			MODULE.info('UserMap: %s: is teacher hiding screenshot' % (username,))
			hide_screenshot = True

		MODULE.info('UserMap: %s: hide_screenshot=%r' % (username, hide_screenshot))

		dict.__setitem__(self, userstr, UserInfo(user.dn, username, isTeacher=user.is_teacher(lo), hide_screenshot=hide_screenshot))
_usermap = UserMap()


class LockableAttribute(object):

	def __init__(self, initial_value=None, locking=True):
		self._lock = locking and threading.Lock() or None
		# MODULE.info('Locking object: %s' % self._lock)
		self._old = initial_value
		self._current = copy.deepcopy(initial_value)

	def lock(self):
		if self._lock is None:
			return
		if not self._lock.acquire(3000):
			raise ITALC_Error('Could not lock attribute')

	def unlock(self):
		if self._lock is None:
			return
		self._lock.release()

	@property
	def current(self):
		self.lock()
		tmp = copy.deepcopy(self._current)
		self.unlock()
		return tmp

	@property
	def old(self):
		self.lock()
		tmp = copy.deepcopy(self._old)
		self.unlock()
		return tmp

	@property
	def isInitialized(self):
		self.lock()
		ret = self._current is not None
		self.unlock()
		return ret

	@property
	def hasChanged(self):
		self.lock()
		diff = self._old != self._current
		self._old = copy.deepcopy(self._current)
		self.unlock()
		return diff

	def reset(self, inital_value=None):
		self.lock()
		self._old = copy.deepcopy(inital_value)
		self._current = copy.deepcopy(inital_value)
		self.unlock()

	def set(self, value, force=False):
		self.lock()
		if value != self._current or force:
			self._old = copy.deepcopy(self._current)
			self._current = copy.deepcopy(value)
		self.unlock()


class ITALC_Computer(notifier.signals.Provider, QObject):
	CONNECTION_STATES = {
		italc.ItalcVncConnection.Disconnected: 'disconnected',
		italc.ItalcVncConnection.Connected: 'connected',
		italc.ItalcVncConnection.ConnectionFailed: 'error',
		italc.ItalcVncConnection.AuthenticationFailed: 'autherror',
		italc.ItalcVncConnection.HostUnreachable: 'offline'
	}

	def __init__(self, computer):
		QObject.__init__(self)
		notifier.signals.Provider.__init__(self)

		self.signal_new('connected')
		self.signal_new('screen-lock')
		self.signal_new('input-lock')
		self.signal_new('access-dialog')
		self.signal_new('demo-client')
		self.signal_new('demo-server')
		self.signal_new('message-box')
		self.signal_new('system-tray-icon')
		self._vnc = None
		self._core = None
		self._core_ready = False
		self._computer = computer
		self._dn = self._computer.dn
		self.objectType = self._computer.module
		self._timer = None
		self._resetUserInfoTimeout()
		self._username = LockableAttribute()
		self._homedir = LockableAttribute()
		self._flags = LockableAttribute()
		self._state = LockableAttribute(initial_value='disconnected')
		self._teacher = LockableAttribute(initial_value=False)
		self._allowedClients = []
		self.open()

	def open(self):
		MODULE.info('Opening VNC connection to %s' % (self.ipAddress))
		self._vnc = italc.ItalcVncConnection()
		# transfer responsibility for cleaning self._vnc up from python garbarge collector to C++/QT (Bug #27534)
		sip.transferto(self._vnc, None)
		self._vnc.setHost(self.ipAddress)
		self._vnc.setPort(ITALC_VNC_PORT)
		self._vnc.setQuality(italc.ItalcVncConnection.ThumbnailQuality)
		self._vnc.setFramebufferUpdateInterval(int(1000 * ITALC_VNC_UPDATE))
		self._vnc.start()
		self._vnc.stateChanged.connect(self._stateChanged)

	def __del__(self):
		self.close()

	def close(self):
		MODULE.info('Closing VNC connection to %s' % (self.ipAddress))
		if self._core:
			# WARNING: destructor of iTalcCoreConnection calls iTalcVncConnection->stop() ; do not call the stop() function again!
			del self._core
			self._core = None
			self._core_ready = False
		elif self._vnc:
			self._vnc.stop()
		del self._vnc
		self._vnc = None
		self._state.set(ITALC_Computer.CONNECTION_STATES[italc.ItalcVncConnection.Disconnected])

	@pyqtSlot(int)
	def _stateChanged(self, state):
		self._state.set(ITALC_Computer.CONNECTION_STATES[state])

		# Comments for bug #41752:
		# The iTALC core connection is used on top of the iTALC VNC connection.
		# The core connection is set up after the VNC connection emits a state change ??? ==> connected.
		# Tests have shown that the core connection is not ready/usable right after setup.
		# That's why _core_ready is set to False.
		# After the first usage of the core connection, two state changes are triggered:
		# connected ==> disconnected ==> connected.
		# Now the core connection is ready for use ==> _core_ready is set to True and the
		# "connected" signal is emitted.
		#
		# self.connected() checks by default if _core_ready==True if not specified by argument to ignore this variable.
		# (used to send initial sendGetUserInformationRequest() via core connection to trigger connection state change).

		if not self._core and self._state.current == 'connected' and self._state.old != 'connected':
			MODULE.process('%s: VNC connection established' % (self.ipAddress,))
			self._core = italc.ItalcCoreConnection(self._vnc)
			self._core.receivedUserInfo.connect(self._userInfo)
			self._core.receivedSlaveStateFlags.connect(self._slaveStateFlags)
			self._core_ready = False
			self.start()
		elif self._core and self._state.current == 'connected' and self._state.old != 'connected':
			MODULE.process('%s: iTALC connection on top of VNC connection established' % (self.ipAddress,))
			self._core_ready = True
			self.signal_emit('connected', self)
		# lost connection ...
		elif self._state.current != 'connected' and self._state.old == 'connected':
			MODULE.process('%s: lost connection: new state=%r' % (self.ipAddress, self._state.current))
			self._core_ready = False
			self._username.reset()
			self._homedir.reset()
			self._flags.reset()
			self._teacher.reset(False)

	def _resetUserInfoTimeout(self, guardtime=ITALC_CORE_TIMEOUT):
		self._usernameLastUpdate = time.time() + guardtime

	@pyqtSlot(str, str)
	def _userInfo(self, username, homedir):
		self._resetUserInfoTimeout(0)
		self._username.set(str(username))
		self._homedir.set(str(homedir))
		self._teacher.set(self.isTeacher)
		if self._username.current:
			self._core.reportSlaveStateFlags()

	def _emit_flag(self, diff, flag, signal):
		if diff & flag:
			self.signal_emit(signal, bool(self._flags.current & flag))

	@pyqtSlot(int)
	def _slaveStateFlags(self, flags):
		self._flags.set(flags)
		if self._flags.old is None:
			diff = self._flags.current
		else:
			# which flags have changed: old xor current
			diff = self._flags.old ^ self._flags.current
		self._flags.set(flags, force=True)
		self._emit_flag(diff, italc.ItalcCore.ScreenLockRunning, 'screen-lock')
		self._emit_flag(diff, italc.ItalcCore.InputLockRunning, 'input-lock')
		self._emit_flag(diff, italc.ItalcCore.AccessDialogRunning, 'access-dialog')
		self._emit_flag(diff, italc.ItalcCore.DemoClientRunning, 'demo-client')
		self._emit_flag(diff, italc.ItalcCore.DemoServerRunning, 'demo-server')
		self._emit_flag(diff, italc.ItalcCore.MessageBoxRunning, 'message-box')
		self._emit_flag(diff, italc.ItalcCore.SystemTrayIconRunning, 'system-tray-icon')

	def update(self):
		# bug 41752: have a look at _stateChanged() why ignore_core_ready is required for self.connected()
		if not self.connected(ignore_core_ready=True):
			MODULE.warn('%s: not connected - skipping update' % (self.ipAddress,))
			return True

		if self._usernameLastUpdate + ITALC_CORE_TIMEOUT < time.time():
			MODULE.process('connection to %s is dead for %.2fs - reconnecting (timeout=%d)' % (self.ipAddress, (time.time() - self._usernameLastUpdate), ITALC_CORE_TIMEOUT))
			self.close()
			self._username.reset()
			self._homedir.reset()
			self._flags.reset()
			self._resetUserInfoTimeout()
			self.open()
			return True
		elif self._usernameLastUpdate + max(ITALC_CORE_TIMEOUT / 2, 1) < time.time():
			MODULE.process('connection to %s seems to be dead for %.2fs' % (self.ipAddress, (time.time() - self._usernameLastUpdate)))

		self._core.sendGetUserInformationRequest()
		return True

	def start(self):
		self.stop()
		self._resetUserInfoTimeout()
		self.update()
		self._timer = notifier.timer_add(ITALC_CORE_UPDATE * 1000, self.update)

	def stop(self):
		if self._timer is not None:
			notifier.timer_remove(self._timer)
			self._timer = None

	@property
	def dict(self):
		item = {'id': self.name,
				 'name': self.name,
				 'user': self.user.current,
				 'teacher': self.isTeacher,
				 'connection': self.state.current,
				 'description': self.description,
				 'ip': self.ipAddress,
				 'mac': self.macAddress,
				 'objectType': self.objectType}
		item.update(self.flagsDict)
		return item

	@property
	def hasChanged(self):
		states = (self.state, self.flags, self.user, self.teacher)
		return any(state.hasChanged for state in states)

	# UDM properties
	@property
	def name(self):
		return self._computer.info.get('name', None)

	@property
	def ipAddress(self):
		ip = self._computer.info.get('ip')
		if not ip:
			raise ITALC_Error('Unknown IP address')
		return ip[0]

	@property
	def macAddress(self):
		return (self._computer.info.get('mac') or [''])[0]

	@property
	def isTeacher(self):
		try:
			return _usermap[str(self._username.current)].isTeacher
		except AttributeError:
			return False

	@property
	def hide_screenshot(self):
		try:
			return _usermap[str(self._username.current)].hide_screenshot
		except AttributeError:
			return False

	@property
	def teacher(self):
		return self._teacher

	# iTalc properties
	@property
	def user(self):
		return self._username

	@property
	def description(self):
		return self._computer.info.get('description', None)

	@property
	def screenLock(self):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isScreenLockRunning()

	@property
	def inputLock(self):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isInputLockRunning()

	@property
	def demoServer(self):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isDemoServerRunning()

	@property
	def demoClient(self):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isDemoClientRunning()

	@property
	def messageBox(self):
		if not self._core or self._core.slaveStateFlags() == 0:
			return None
		return self._core.isMessageBoxRunning()

	@property
	def flags(self):
		return self._flags

	@property
	def flagsDict(self):
		return {
			'ScreenLock': self.screenLock,
			'InputLock': self.inputLock,
			'DemoServer': self.demoServer,
			'DemoClient': self.demoClient,
			'MessageBox': self.messageBox,
		}

	@property
	def state(self):
		'''Returns a LockableAttribute containing an abstracted
		connection state. Possible values: conntected, disconnected,
		error'''
		return self._state

	def connected(self, ignore_core_ready=False):
		# bug 41752: have a look at _stateChanged() why ignore_core_ready is required for self.connected()
		return self._core and self._vnc.isConnected() and self._state.current == 'connected' and (self._core_ready or ignore_core_ready)

	# iTalc: screenshots
	@property
	def screenshot(self):
		if not self.connected():
			MODULE.warn('%s: not connected - skipping screenshot' % (self.ipAddress,))
			return None
		image = self._vnc.image()
		if not image.byteCount():
			MODULE.info('%s: no screenshot available yet' % (self.ipAddress,))
			return None
		tmpfile = tempfile.NamedTemporaryFile(delete=False)
		tmpfile.close()
		writer = QImageWriter(tmpfile.name, 'JPG')
		writer.write(image)
		return tmpfile

	@property
	def screenshotQImage(self):
		return self._vnc.image()

	# iTalc: screen locking
	def lockScreen(self, value):
		if not self.connected():
			MODULE.error('%s: not connected - skipping lockScreen' % (self.ipAddress,))
			return
		if value:
			self._core.lockScreen()
		else:
			self._core.unlockScreen()

	# iTalc: input device locking
	def lockInput(self, value):
		if not self.connected():
			MODULE.error('%s: not connected - skipping lockInput' % (self.ipAddress,))
			return
		if value:
			self._core.lockInput()
		else:
			self._core.unlockInput()

	# iTalc: message box
	def message(self, text):
		if not self.connected():
			MODULE.warn('%s: not connected - skipping message' % (self.ipAddress,))
			return
		self._core.displayTextMessage(text)

	# iTalc: Demo
	def denyClients(self):
		if not self.connected():
			MODULE.error('%s: not connected - skipping denyClients' % (self.ipAddress,))
			return
		for client in self._allowedClients[:]:
			self._core.demoServerUnallowHost(client.ipAddress)
			self._allowedClients.remove(client)

	def allowClients(self, clients):
		if not self.connected():
			MODULE.error('%s: not connected - skipping allowClients' % (self.ipAddress,))
			return
		self.denyClients()
		for client in clients:
			self._core.demoServerAllowHost(client.ipAddress)
			self._allowedClients.append(client)

	def startDemoServer(self, allowed_clients=[]):
		if not self.connected():
			MODULE.error('%s: not connected - skipping startDemoServer' % (self.ipAddress,))
			return
		self._core.stopDemoServer()
		self._core.startDemoServer(ITALC_VNC_PORT, ITALC_DEMO_PORT)
		self.allowClients(allowed_clients)

	def stopDemoServer(self):
		if not self.connected():
			MODULE.warn('%s: not connected - skipping stopDemoServer' % (self.ipAddress,))
			return
		self.denyClients()
		self._core.stopDemoServer()

	def startDemoClient(self, server, fullscreen=True):
		if not self.connected():
			MODULE.error('%s: not connected - skipping startDemoClient' % (self.ipAddress,))
			return
		self._core.stopDemo()
		self._core.unlockScreen()
		self._core.unlockInput()
		self._core.startDemo(server.ipAddress, ITALC_DEMO_PORT, fullscreen)

	def stopDemoClient(self):
		if not self.connected():
			MODULE.warn('%s: not connected - skipping stopDemoClient' % (self.ipAddress,))
			return
		self._core.stopDemo()

	# iTalc: computer control
	def powerOff(self):
		if not self.connected():
			MODULE.warn('%s: not connected - skipping powerOff' % (self.ipAddress,))
			return
		self._core.powerDownComputer()

	def powerOn(self):
		# do not use the italc trick
		# if self._core and self.macAddress:
		# 	self._core.powerOnComputer( self.macAddress )
		if self.macAddress:
			subprocess.Popen(['/usr/bin/wakeonlan', self.macAddress])
		else:
			MODULE.error('%s: no MAC address set - skipping powerOn' % (self.ipAddress,))

	def restart(self):
		if not self.connected():
			MODULE.error('%s: not connected - skipping restart' % (self.ipAddress,))
			return
		self._core.restartComputer()

	# iTalc: user functions
	def logOut(self):
		if not self.connected():
			MODULE.error('%s: not connected - skipping logOut' % (self.ipAddress,))
			return
		self._core.logoutUser()


class ITALC_Manager(dict, notifier.signals.Provider):
	SCHOOL = None
	ROOM = None
	ROOM_DN = None

	def __init__(self):
		dict.__init__(self)
		notifier.signals.Provider.__init__(self)

	@property
	def room(self):
		return ITALC_Manager.ROOM

	@room.setter
	def room(self, value):
		self._clear()
		self._set(value)

	@property
	def roomDN(self):
		return ITALC_Manager.ROOM_DN

	@property
	def school(self):
		return ITALC_Manager.SCHOOL

	@school.setter
	def school(self, value):
		self._clear()
		ITALC_Manager.SCHOOL = value

	@property
	def users(self):
		return [_usermap[x.user.current].username for x in self.values() if x.user.current and x.connected()]

	def ipAddresses(self, students_only=True):
		values = self.values()
		if students_only:
			values = [x for x in values if not x.isTeacher]

		return [x.ipAddress for x in values]

	def _clear(self):
		if ITALC_Manager.ROOM:
			for name, computer in self.items():
				computer.stop()
				computer.close()
				del computer
			self.clear()
			ITALC_Manager.ROOM = None
			ITALC_Manager.ROOM_DN = None

	@LDAP_Connection()
	def _set(self, room, ldap_user_read=None):
		lo = ldap_user_read

		room_dn = room
		try:  # room DN
			ldap.dn.str2dn(room)
		except ldap.DECODING_ERROR:  # room name
			room_dn = None # got a name instead of a DN

		try:
			if room_dn:
				computerroom = ComputerRoom.from_dn(room, ITALC_Manager.SCHOOL, lo)
			else:
				computerroom = ComputerRoom.get_only_udm_obj(lo, filter_format('cn=%s-%s', (ITALC_Manager.SCHOOL, room)))
				if computerroom is None:
					raise noObject(computerroom)
				computerroom = ComputerRoom.from_udm_obj(computerroom, ITALC_Manager.SCHOOL, lo)
		except noObject:
			raise ITALC_Error('Unknown computer room')
		except MultipleObjectsError as exc:
			raise ITALC_Error('Did not find exactly 1 group for the room (count: %d)' % len(exc.objs))

		ITALC_Manager.ROOM = computerroom.get_relative_name()
		ITALC_Manager.ROOM_DN = computerroom.dn

		computers = list(computerroom.get_computers(lo))
		if not computers:
			raise ITALC_Error('There are no computers in the selected room.')

		for computer in computers:
			try:
				comp = ITALC_Computer(computer.get_udm_object(lo))
				self.__setitem__(comp.name, comp)
			except ITALC_Error as exc:
				MODULE.warn('Computer could not be added: %s' % (exc,))

	@property
	def isDemoActive(self):
		return any(comp for comp in self.values() if comp.demoServer or comp.demoClient)

	@property
	def demoServer(self):
		for comp in self.values():
			if comp.demoServer:
				return comp

	@property
	def demoClients(self):
		return [comp for comp in self.values() if comp.demoClient]

	def startDemo(self, demo_server, fullscreen=True):
		if self.isDemoActive:
			self.stopDemo()

		server = self.get(demo_server)
		if server is None:
			raise AttributeError('unknown system %s' % demo_server)

		# start demo server
		clients = [comp for comp in self.values() if comp.name != demo_server and comp.connected() and comp.objectType != 'computers/ucc']
		MODULE.info('Demo server is %s' % (demo_server,))
		MODULE.info('Demo clients: %s' % ', '.join(x.name for x in clients))
		MODULE.info('Demo client users: %s' % ', '.join(str(x.user.current) for x in clients))
		try:
			teachers = [x.name for x in clients if not x.user.current or _usermap[str(x.user.current)].isTeacher]
		except AttributeError as exc:
			MODULE.error('Could not determine the list of teachers: %s' % (exc,))
			return False

		MODULE.info('Demo clients (teachers): %s' % ', '.join(teachers))
		server.startDemoServer(clients)
		for client in clients:
			client.startDemoClient(server, fullscreen=False if client.name in teachers else fullscreen)

	def stopDemo(self):
		if self.demoServer is not None:
			self.demoServer.stopDemoServer()
		for client in self.demoClients:
			client.stopDemoClient()
