#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
#
# Copyright 2012-2021 Univention GmbH
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
import traceback
import uuid

try:
    from typing import Any, List, Optional, TypeVar
except ImportError:
    pass

import ldap
import notifier
import notifier.signals
import notifier.threads
import sip
from ldap.dn import explode_dn
from ldap.filter import filter_format
from PyQt4.QtCore import QObject, pyqtSlot

import italc
from ucsschool.lib.models.base import MultipleObjectsError
from ucsschool.lib.models.group import ComputerRoom
from ucsschool.lib.models.user import User
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from ucsschool.veyon_client.client import VeyonClient
from ucsschool.veyon_client.models import AuthenticationMethod, Feature, ScreenshotFormat, VeyonError
from univention.admin.uexceptions import noObject
from univention.lib.i18n import Translation
from univention.lib.models.base import LoType
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules.computerroom import wakeonlan

LV = TypeVar("LV")

_ = Translation("ucs-school-umc-computerroom").translate

ITALC_DEMO_PORT = int(ucr.get("ucsschool/umc/computerroom/demo/port", 11400))
ITALC_VNC_PORT = int(ucr.get("ucsschool/umc/computerroom/vnc/port", 11100))
ITALC_VNC_UPDATE = float(ucr.get("ucsschool/umc/computerroom/vnc/update", 1))
ITALC_CORE_UPDATE = max(1, int(ucr.get("ucsschool/umc/computerroom/core/update", 1)))
ITALC_CORE_TIMEOUT = max(1, int(ucr.get("ucsschool/umc/computerroom/core/timeout", 10)))

ITALC_USER_REGEX = r"(?P<username>[^\(]*?)(\((?P<realname>.*?)\))$"
VEYON_USER_REGEX = r"(?P<domain>.*)\\(?P<username>[^\(\\]+)$"

VEYON_KEY_FILE = "/etc/ucsschool-veyon/key.pem"

italc.ItalcCore.init()

italc.ItalcCore.config.setLogLevel(italc.Logger.LogLevelDebug)
italc.ItalcCore.config.setLogToStdErr(True)
italc.ItalcCore.config.setLogFileDirectory("/var/log/univention/")
italc.Logger("ucs-school-umc-computerroom")
italc.ItalcCore.config.setLogonAuthenticationEnabled(False)

italc.ItalcCore.setRole(italc.ItalcCore.RoleTeacher)
italc.ItalcCore.initAuthentication(italc.AuthenticationCredentials.PrivateKey)


class ComputerRoomError(Exception):
    pass


class UserInfo(object):
    def __init__(self, ldap_dn, username, isTeacher=False, hide_screenshot=False):
        # type: (str, str, Optional[bool], Optional[bool]) -> None
        self.dn = ldap_dn
        self.isTeacher = isTeacher
        self.username = username
        self.hide_screenshot = hide_screenshot


class UserMap(dict):
    def __init__(self, user_regex):  # type: (str) -> None
        super(UserMap, self).__init__()
        self._user_regex = re.compile(user_regex)

    def __getitem__(self, user):  # type: (str) -> UserInfo
        if user not in self:
            self._read_user(user)
        return dict.__getitem__(self, user)

    def validate_userstr(self, userstr):  # type: (str) -> str
        match = self._user_regex.match(userstr)
        if not match or not userstr:
            raise AttributeError("invalid key {!r}".format(userstr))
        username = match.groupdict()["username"]
        if not username:
            raise AttributeError("username missing: {!r}".format(userstr))
        return username

    @LDAP_Connection()
    def _read_user(self, userstr, ldap_user_read=None):  # type: (str, Optional[LoType]) -> None
        username = self.validate_userstr(userstr)
        lo = ldap_user_read
        try:
            userobj = User.get_only_udm_obj(lo, filter_format("uid=%s", (username,)))
            if userobj is None:
                raise noObject(username)
            user = User.from_udm_obj(userobj, None, lo)  # type: User
        except (noObject, MultipleObjectsError):
            MODULE.info('Unknown user "%s"' % username)
            dict.__setitem__(self, userstr, UserInfo("", ""))
            return

        blacklisted_groups = set(
            [
                x.strip().lower()
                for x in ucr.get(
                    "ucsschool/umc/computerroom/hide_screenshots/groups", "Domain Admins"
                ).split(",")
            ]
        )
        users_groupmemberships = set([explode_dn(x, True)[0].lower() for x in userobj["groups"]])
        MODULE.info(
            "UserMap: %s: hide screenshots for following groups: %s" % (username, blacklisted_groups)
        )
        MODULE.info(
            "UserMap: %s: user is member of following groups: %s" % (username, users_groupmemberships)
        )
        hide_screenshot = bool(blacklisted_groups & users_groupmemberships)

        if ucr.is_true("ucsschool/umc/computerroom/hide_screenshots/teachers", True) and user.is_teacher(
            lo
        ):
            MODULE.info("UserMap: %s: is teacher hiding screenshot" % (username,))
            hide_screenshot = True

        MODULE.info("UserMap: %s: hide_screenshot=%r" % (username, hide_screenshot))

        dict.__setitem__(
            self,
            userstr,
            UserInfo(user.dn, username, isTeacher=user.is_teacher(lo), hide_screenshot=hide_screenshot),
        )


class LockableAttribute(object):
    def __init__(self, initial_value=None, locking=True):
        # type: (Optional[LV], Optional[bool]) -> None
        self._lock = locking and threading.Lock() or None
        # MODULE.info('Locking object: %s' % self._lock)
        self._old = initial_value
        self._has_changed = False
        self._current = copy.deepcopy(initial_value)

    def lock(self):  # type: () -> None
        if self._lock is None:
            return
        if not self._lock.acquire(3000):
            raise ComputerRoomError("Could not lock attribute")

    def unlock(self):
        if self._lock is None:
            return
        self._lock.release()

    @property
    def current(self):  # type: () -> LV
        self.lock()
        tmp = copy.deepcopy(self._current)
        self.unlock()
        return tmp

    @property
    def old(self):  # type: () -> LV
        self.lock()
        tmp = copy.deepcopy(self._old)
        self.unlock()
        return tmp

    @property
    def isInitialized(self):  # type: () -> bool
        self.lock()
        ret = self._current is not None
        self.unlock()
        return ret

    @property
    def hasChanged(self):  # type: () -> bool
        self.lock()
        diff = self._has_changed
        self._has_changed = False
        self._old = copy.deepcopy(self._current)
        self.unlock()
        return diff

    def reset(self, inital_value=None):  # type: (Optional[LV]) -> None
        self.lock()
        self._old = copy.deepcopy(inital_value)
        self._current = copy.deepcopy(inital_value)
        self.unlock()

    def set(self, value, force=False):  # type: (LV, Optional[bool]) -> None
        self.lock()
        if value != self._current or force:
            if value != self._current:
                self._has_changed = True
            self._old = copy.deepcopy(self._current)
            self._current = copy.deepcopy(value)
        self.unlock()


class ITALC_Computer(notifier.signals.Provider, QObject):
    CONNECTION_STATES = {
        italc.ItalcVncConnection.Disconnected: "disconnected",
        italc.ItalcVncConnection.Connected: "connected",
        italc.ItalcVncConnection.ConnectionFailed: "error",
        italc.ItalcVncConnection.AuthenticationFailed: "autherror",
        italc.ItalcVncConnection.HostUnreachable: "offline",
    }

    def __init__(self, computer, user_map):
        QObject.__init__(self)
        notifier.signals.Provider.__init__(self)

        self.signal_new("connected")
        self.signal_new("screen-lock")
        self.signal_new("input-lock")
        self.signal_new("access-dialog")
        self.signal_new("demo-client")
        self.signal_new("demo-server")
        self.signal_new("message-box")
        self.signal_new("system-tray-icon")
        self._user_map = user_map
        self._vnc = None
        self._core = None
        self._core_ready = False
        self._computer = computer
        self._dn = self._computer.dn
        self._active_ip = self.get_active_ip(self._computer.info.get("ip"))
        self._active_mac = self.mac_from_ip(self._active_ip)
        self.objectType = self._computer.module
        self._timer = None
        self._resetUserInfoTimeout()
        self._username = LockableAttribute()
        self._homedir = LockableAttribute()
        self._flags = LockableAttribute()
        self._state = LockableAttribute(initial_value="disconnected")
        self._teacher = LockableAttribute(initial_value=False)
        self._allowedClients = []
        self.open()

    def open(self):
        MODULE.info("Opening VNC connection to %s" % (self.ipAddress))
        self._vnc = italc.ItalcVncConnection()
        # transfer responsibility for cleaning self._vnc up from python garbarge collector to C++/QT
        # (Bug #27534)
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
        MODULE.info("Closing VNC connection to %s" % (self.ipAddress))
        if self._vnc:
            self._vnc.stateChanged.disconnect(self._stateChanged)
        if self._core:
            self._core.receivedUserInfo.disconnect(self._userInfo)
            self._core.receivedSlaveStateFlags.disconnect(self._slaveStateFlags)
            # WARNING: destructor of iTalcCoreConnection calls iTalcVncConnection->stop() ; do not call
            # the stop() function again!
            del self._core
            self._core = None
            self._core_ready = False
        elif self._vnc:
            # WARNING: only call stop() if we didn't removed self._core
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
        # self.connected() checks by default if _core_ready==True if not specified by argument to
        # ignore this variable.
        # (used to send initial sendGetUserInformationRequest() via core connection to trigger
        # connection state change).

        if not self._core and self._state.current == "connected" and self._state.old != "connected":
            MODULE.process("%s: VNC connection established" % (self.ipAddress,))
            if self._vnc is None:
                MODULE.error("%s: self._vnc is None!" % (self.ipAddress,))
                return
            self._core = italc.ItalcCoreConnection(self._vnc)
            self._core.receivedUserInfo.connect(self._userInfo)
            self._core.receivedSlaveStateFlags.connect(self._slaveStateFlags)
            self._core_ready = False
            self.start()
        elif self._core and self._state.current == "connected" and self._state.old != "connected":
            MODULE.process(
                "%s: iTALC connection on top of VNC connection established" % (self.ipAddress,)
            )
            self._core_ready = True
            self.signal_emit("connected", self)
        # lost connection ...
        elif self._state.current != "connected" and self._state.old == "connected":
            MODULE.process("%s: lost connection: new state=%r" % (self.ipAddress, self._state.current))
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
        # MODULE.info(
        #     '%s: received slave state flags: (old=%r, new=%r)' % (
        #         self.ipAddress, self._flags.old, flags))
        self._flags.set(flags)
        if self._flags.old is None:
            diff = self._flags.current
        else:
            # which flags have changed: old xor current
            diff = self._flags.old ^ self._flags.current
        self._flags.set(flags, force=True)
        self._emit_flag(diff, italc.ItalcCore.ScreenLockRunning, "screen-lock")
        self._emit_flag(diff, italc.ItalcCore.InputLockRunning, "input-lock")
        self._emit_flag(diff, italc.ItalcCore.AccessDialogRunning, "access-dialog")
        self._emit_flag(diff, italc.ItalcCore.DemoClientRunning, "demo-client")
        self._emit_flag(diff, italc.ItalcCore.DemoServerRunning, "demo-server")
        self._emit_flag(diff, italc.ItalcCore.MessageBoxRunning, "message-box")
        self._emit_flag(diff, italc.ItalcCore.SystemTrayIconRunning, "system-tray-icon")

    def update(self):
        # bug 41752: have a look at _stateChanged() why ignore_core_ready is required for
        # self.connected()
        if not self.connected(ignore_core_ready=True):
            MODULE.warn("%s: not connected - skipping update" % (self.ipAddress,))
            return True

        if self._usernameLastUpdate + ITALC_CORE_TIMEOUT < time.time():
            MODULE.process(
                "connection to %s is dead for %.2fs - reconnecting (timeout=%d)"
                % (self.ipAddress, (time.time() - self._usernameLastUpdate), ITALC_CORE_TIMEOUT)
            )
            self.close()
            self._username.reset()
            self._homedir.reset()
            self._flags.reset()
            self._resetUserInfoTimeout()
            self.open()
            return True
        elif self._usernameLastUpdate + max(ITALC_CORE_TIMEOUT / 2, 1) < time.time():
            MODULE.process(
                "connection to %s seems to be dead for %.2fs"
                % (self.ipAddress, (time.time() - self._usernameLastUpdate))
            )

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
        item = {
            "id": self.name,
            "name": self.name,
            "user": self.user.current,
            "teacher": self.isTeacher,
            "connection": self.state.current,
            "description": self.description,
            "ip": self.ipAddress,
            "mac": self.macAddress,
            "objectType": self.objectType,
        }
        item.update(self.flagsDict)
        return item

    @property
    def hasChanged(self):
        states = (self.state, self.flags, self.user, self.teacher)
        return any(state.hasChanged for state in states)

    # UDM properties
    @property
    def name(self):
        return self._computer.info.get("name", None)

    @property
    def ipAddress(self):
        ips = self._computer.info.get("ip")
        if not ips:
            raise ComputerRoomError("Unknown IP address")
        if not self._active_ip:
            self._active_ip = self.get_active_ip(ips)
        return self._active_ip

    @property
    def macAddress(self):
        udm_macs = self._computer.info.get("mac")
        if not self._active_mac and self._active_ip:
            active_mac = self.mac_from_ip(self._active_ip)
            if active_mac in udm_macs:
                self._active_mac = active_mac
            elif ucr.is_true("ucsschool/umc/computerroom/ping-client-ip-addresses", False):
                MODULE.warn("Active mac {} is not in udm computer object.".format(active_mac))
        return self._active_mac or (self._computer.info.get("mac") or [""])[0]

    @property
    def isTeacher(self):
        try:
            return self._user_map[str(self._username.current)].isTeacher
        except AttributeError:
            return False

    @property
    def hide_screenshot(self):
        try:
            return self._user_map[str(self._username.current)].hide_screenshot
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
        return self._computer.info.get("description", None)

    @property
    def screenLock(self):
        if not self._core:
            return None
        return self._core.isScreenLockRunning()

    @property
    def inputLock(self):
        if not self._core:
            return None
        return self._core.isInputLockRunning()

    @property
    def demoServer(self):
        if not self._core:
            return None
        return self._core.isDemoServerRunning()

    @property
    def demoClient(self):
        if not self._core:
            return None
        return self._core.isDemoClientRunning()

    @property
    def messageBox(self):
        if not self._core:
            return None
        return self._core.isMessageBoxRunning()

    @property
    def flags(self):
        return self._flags

    @property
    def flagsDict(self):
        return {
            "ScreenLock": self.screenLock,
            "InputLock": self.inputLock,
            "DemoServer": self.demoServer,
            "DemoClient": self.demoClient,
            "MessageBox": self.messageBox,
        }

    @property
    def state(self):
        """Returns a LockableAttribute containing an abstracted
        connection state. Possible values: conntected, disconnected,
        error"""
        return self._state

    def connected(self, ignore_core_ready=False):
        # bug 41752: have a look at _stateChanged() why ignore_core_ready is required for
        # self.connected()
        return (
            self._core
            and self._vnc.isConnected()
            and self._state.current == "connected"
            and (self._core_ready or ignore_core_ready)
        )

    # iTalc: screenshots
    @property
    def screenshot(self):
        if not self.connected():
            MODULE.warn("%s: not connected - skipping screenshot" % (self.ipAddress,))
            return None
        image = self._vnc.image()
        if not image.byteCount():
            MODULE.info("%s: no screenshot available yet" % (self.ipAddress,))
            return None
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        tmpfile.close()

        if image.save(tmpfile.name, "JPG"):
            return tmpfile

    @property
    def screenshotQImage(self):
        return self._vnc.image()

    # iTalc: screen locking
    def lockScreen(self, value):
        if not self.connected():
            MODULE.error("%s: not connected - skipping lockScreen" % (self.ipAddress,))
            return
        if value:
            self._core.lockScreen()
        else:
            self._core.unlockScreen()

    # iTalc: input device locking
    def lockInput(self, value):
        if not self.connected():
            MODULE.error("%s: not connected - skipping lockInput" % (self.ipAddress,))
            return
        if value:
            self._core.lockInput()
        else:
            self._core.unlockInput()

    # iTalc: message box
    def message(self, title, text):
        if not self.connected():
            MODULE.warn("%s: not connected - skipping message" % (self.ipAddress,))
            return
        self._core.displayTextMessage(title, text)

    # iTalc: Demo
    def denyClients(self):
        if not self.connected():
            MODULE.error("%s: not connected - skipping denyClients" % (self.ipAddress,))
            return
        for client in self._allowedClients[:]:
            self._core.demoServerUnallowHost(client.ipAddress)
            self._allowedClients.remove(client)

    def allowClients(self, clients):
        if not self.connected():
            MODULE.error("%s: not connected - skipping allowClients" % (self.ipAddress,))
            return
        self.denyClients()
        for client in clients:
            self._core.demoServerAllowHost(client.ipAddress)
            self._allowedClients.append(client)

    def startDemoServer(self, allowed_clients=[]):
        if not self.connected():
            MODULE.error("%s: not connected - skipping startDemoServer" % (self.ipAddress,))
            return
        self._core.stopDemoServer()
        self._core.startDemoServer(ITALC_VNC_PORT, ITALC_DEMO_PORT)
        self.allowClients(allowed_clients)

    def stopDemoServer(self):
        if not self.connected():
            MODULE.warn("%s: not connected - skipping stopDemoServer" % (self.ipAddress,))
            return
        self.denyClients()
        self._core.stopDemoServer()

    def startDemoClient(self, server, fullscreen=True):
        if not self.connected():
            MODULE.error("%s: not connected - skipping startDemoClient" % (self.ipAddress,))
            return
        self._core.stopDemo()
        self._core.unlockScreen()
        self._core.unlockInput()
        self._core.startDemo(server.ipAddress, ITALC_DEMO_PORT, fullscreen)

    def stopDemoClient(self):
        if not self.connected():
            MODULE.warn("%s: not connected - skipping stopDemoClient" % (self.ipAddress,))
            return
        self._core.stopDemo()

    # iTalc: computer control
    def powerOff(self):
        if not self.connected():
            MODULE.warn("%s: not connected - skipping powerOff" % (self.ipAddress,))
            return
        self._core.powerDownComputer()

    def powerOn(self):
        # do not use the italc trick
        # if self._core and self.macAddress:
        # 	self._core.powerOnComputer( self.macAddress )
        if self.macAddress:
            blacklisted_interfaces = [
                x
                for x in ucr.get(
                    "ucsschool/umc/computerroom/wakeonlan/blacklisted/interfaces", ""
                ).split()
                if x
            ]
            blacklisted_interface_prefixes = [
                x
                for x in ucr.get(
                    "ucsschool/umc/computerroom/wakeonlan/blacklisted/interface_prefixes", ""
                ).split()
                if x
            ]
            target_broadcast_ips = [
                x for x in ucr.get("ucsschool/umc/computerroom/wakeonlan/target_nets", "").split() if x
            ]
            target_broadcast_ips = target_broadcast_ips or ["255.255.255.255"]
            wakeonlan.send_wol_packet(
                self.macAddress,
                blacklisted_interfaces=blacklisted_interfaces,
                blacklisted_interface_prefixes=blacklisted_interface_prefixes,
                target_broadcast_ips=target_broadcast_ips,
            )
        else:
            MODULE.error("%s: no MAC address set - skipping powerOn" % (self.ipAddress,))

    @staticmethod
    def mac_from_ip(ip):
        if ucr.is_true("ucsschool/umc/computerroom/ping-client-ip-addresses", False):
            pid = subprocess.Popen(["/usr/sbin/arp", "-n", ip], stdout=subprocess.PIPE)  # nosec
            s = pid.communicate()[0]
            res = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", s)
            mac = ""
            if res:
                mac = res.group(0)
            else:
                MODULE.warn("Ip %r is not in arp cache." % ip)
            return mac
        return ""

    @staticmethod
    def get_active_ip(ips):
        if ucr.is_true("ucsschool/umc/computerroom/ping-client-ip-addresses", False):
            for ip in ips:
                command = ["/usr/bin/timeout", "1", "ping", "-c", "1", ip]
                if subprocess.call(command) == 0:  # nosec
                    return ip
            else:
                MODULE.warn("Non of the ips is pingable: %r" % ips)
        return ips[0] if ips else ""

    def restart(self):
        if not self.connected():
            MODULE.error("%s: not connected - skipping restart" % (self.ipAddress,))
            return
        self._core.restartComputer()

    # iTalc: user functions
    def logOut(self):
        if not self.connected():
            MODULE.error("%s: not connected - skipping logOut" % (self.ipAddress,))
            return
        self._core.logoutUser()

    def __repr__(self):
        return "<%s(%s)>" % (type(self).__name__, self.ipAddress)


class ComputerRoomManager(dict, notifier.signals.Provider):
    SCHOOL = None
    ROOM = None
    ROOM_DN = None
    VEYON_BACKEND = False

    def __init__(self):
        dict.__init__(self)
        notifier.signals.Provider.__init__(self)
        self._user_map = UserMap(ITALC_USER_REGEX)
        self._veyon_client = None  # type: Optional[VeyonClient]

    @property
    def room(self):
        return ComputerRoomManager.ROOM

    @room.setter
    def room(self, value):
        self._clear()
        self._set(value)

    @property
    def roomDN(self):
        return ComputerRoomManager.ROOM_DN

    @property
    def school(self):
        return ComputerRoomManager.SCHOOL

    @school.setter
    def school(self, value):
        self._clear()
        ComputerRoomManager.SCHOOL = value

    @property
    def users(self):
        return [
            self._user_map[x.user.current].username
            for x in self.values()
            if x.user.current and x.connected()
        ]

    @property
    def veyon_backend(self):  # type: () -> bool
        return ComputerRoomManager.VEYON_BACKEND

    @property
    def veyon_client(self):  # type: () -> VeyonClient
        if not self._veyon_client:
            with open(VEYON_KEY_FILE, "r") as fp:
                key_data = fp.read().strip()
            self._veyon_client = VeyonClient(
                "http://localhost:11080/api/v1",
                credentials={"keyname": "teacher", "keydata": key_data},
                auth_method=AuthenticationMethod.AUTH_KEYS,
            )
        return self._veyon_client

    def ipAddresses(self, students_only=True):
        values = self.values()
        if students_only:
            values = [x for x in values if not x.isTeacher]

        return [x.ipAddress for x in values]

    def _clear(self):
        if ComputerRoomManager.ROOM:
            for name, computer in self.items():
                computer.stop()
                computer.close()
                del computer
            self.clear()
            ComputerRoomManager.ROOM = None
            ComputerRoomManager.ROOM_DN = None
            ComputerRoomManager.VEYON_BACKEND = False

    def update_computers(self):
        if self.veyon_backend:
            MODULE.info("Triggering update for computers!")
            for computer in self.values():
                computer.start()

    @LDAP_Connection()
    def _set(self, room, ldap_user_read=None):
        lo = ldap_user_read

        room_dn = room
        try:  # room DN
            ldap.dn.str2dn(room)
        except ldap.DECODING_ERROR:  # room name
            room_dn = None  # got a name instead of a DN

        try:
            if room_dn:
                computerroom = ComputerRoom.from_dn(room, ComputerRoomManager.SCHOOL, lo)
            else:
                computerroom = ComputerRoom.get_only_udm_obj(
                    lo, filter_format("cn=%s-%s", (ComputerRoomManager.SCHOOL, room))
                )
                if computerroom is None:
                    raise noObject(computerroom)
                computerroom = ComputerRoom.from_udm_obj(computerroom, ComputerRoomManager.SCHOOL, lo)
        except noObject:
            raise ComputerRoomError("Unknown computer room")
        except MultipleObjectsError as exc:
            raise ComputerRoomError(
                "Did not find exactly 1 group for the room (count: %d)" % len(exc.objs)
            )

        ComputerRoomManager.ROOM = computerroom.get_relative_name()
        ComputerRoomManager.ROOM_DN = computerroom.dn
        ComputerRoomManager.VEYON_BACKEND = computerroom.veyon_backend
        computers = list(computerroom.get_computers(lo))
        if not computers:
            raise ComputerRoomError("There are no computers in the selected room.")

        MODULE.info(
            "Computerroom {!r} will be initialized with {} Computers.".format(
                self.ROOM, "VEYON" if self.veyon_backend else "ITALC"
            )
        )
        if self.veyon_backend:
            self._user_map = UserMap(VEYON_USER_REGEX)
        else:
            self._user_map = UserMap(ITALC_USER_REGEX)
        for computer in computers:
            if self.veyon_backend:
                try:
                    comp = VeyonComputer(computer.get_udm_object(lo), self.veyon_client, self._user_map)
                    self.__setitem__(comp.name, comp)
                except ComputerRoomError as exc:
                    MODULE.warn("Computer could not be added: {}".format(exc))
            else:
                try:
                    comp = ITALC_Computer(computer.get_udm_object(lo), self._user_map)
                    self.__setitem__(comp.name, comp)
                except ComputerRoomError as exc:
                    MODULE.warn("Computer could not be added: %s" % (exc,))

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
            raise AttributeError("unknown system %s" % demo_server)

        # start demo server
        clients = [
            comp
            for comp in self.values()
            if comp.name != demo_server and comp.connected() and comp.objectType != "computers/ucc"
        ]
        MODULE.info("Demo server is %s" % (demo_server,))
        MODULE.info("Demo clients: %s" % ", ".join(x.name for x in clients))
        MODULE.info("Demo client users: %s" % ", ".join(str(x.user.current) for x in clients))
        try:
            teachers = [
                x.name
                for x in clients
                if not x.user.current or self._user_map[str(x.user.current)].isTeacher
            ]
        except AttributeError as exc:
            MODULE.error("Could not determine the list of teachers: %s" % (exc,))
            return False

        MODULE.info("Demo clients (teachers): %s" % ", ".join(teachers))
        if self.veyon_backend:
            demo_access_token = str(uuid.uuid4())
            server.startDemoServer(token=demo_access_token)
            for client in clients:
                client.startDemoClient(
                    server=server,
                    token=demo_access_token,
                    full_screen=False if client.name in teachers else fullscreen,
                )
        else:  # Can be deleted as soon as italc is unsupported
            server.startDemoServer(clients)
            for client in clients:
                client.startDemoClient(
                    server, fullscreen=False if client.name in teachers else fullscreen
                )

    def stopDemo(self):
        if self.demoServer is not None:
            self.demoServer.stopDemoServer()
        # This is necessary since Veyon has a considerable delay with exposing its demo client status.
        # So we just end the demo client on all computers.
        clients = self.values() if self.veyon_backend else self.demoClients
        for client in clients:
            client.stopDemoClient()


class VeyonComputer:
    def __init__(self, computer, veyon_client, user_map):
        # type: (Any, VeyonClient, UserMap) -> None
        self._computer = computer  # type: Any
        self._veyon_client = veyon_client  # type: VeyonClient
        self._user_map = user_map
        self._ip_addresses = self._computer.info.get("ip", [])  # type: List[str]
        self._reachable_ip = None
        self._username = LockableAttribute()
        self._state = LockableAttribute(initial_value="disconnected")
        self._teacher = LockableAttribute(initial_value=False)
        self._screen_lock = LockableAttribute(initial_value=None)
        self._input_lock = LockableAttribute(initial_value=None)
        self._demo_server = LockableAttribute(initial_value=None)
        self._demo_client = LockableAttribute(initial_value=None)
        self._timer = None
        self.start()

    @property
    def name(self):  # type: () -> Optional[str]
        return self._computer.info.get("name", None)

    @property
    def user(self):
        return self._username

    @property
    def state(self):
        return self._state

    @property
    def teacher(self):
        return self._teacher

    @property
    def isTeacher(self):
        try:
            return self._user_map[str(self._username.current)].isTeacher
        except AttributeError:
            return False

    @property
    def description(self):  # type: () -> Optional[str]
        return self._computer.info.get("description", None)

    @property
    def ipAddress(self):
        if self._reachable_ip:
            return self._reachable_ip
        if len(self._ip_addresses) > 0:
            self._reachable_ip = self._find_reachable_ip()
            return self._reachable_ip if self._reachable_ip else self._ip_addresses[0]
        raise ComputerRoomError("Unknown IP address")

    @property
    def macAddress(self):
        ip_addresses = self._computer.info.get("mac", [""])
        return ip_addresses[0]

    @property
    def objectType(self):
        return self._computer.module

    @property
    def hasChanged(self):
        return any(
            state.hasChanged
            for state in (
                self.state,
                self.user,
                self.teacher,
                self._screen_lock,
                self._input_lock,
                self._demo_client,
                self._demo_server,
            )
        )

    @property
    def screenshot(self):
        if not self.connected():
            MODULE.warn("{} not connected - skipping screenshot".format(self.name))
            return None
        image = None
        for ip_address in self._ip_addresses:
            try:
                image = self._veyon_client.get_screenshot(
                    host=ip_address, screenshot_format=ScreenshotFormat.JPEG
                )
            except VeyonError:
                pass  # might just be a non reachable IP. TODO: Catch errors other than 404
            if image:
                break
        if image:
            tmp_file = tempfile.NamedTemporaryFile(delete=False)
            tmp_file.write(image)
            return tmp_file
        else:
            MODULE.warn("{}: no screenshot available yet".format(self.name))
            return None

    @property
    def hide_screenshot(self):
        try:
            return self._user_map[str(self._username.current)].hide_screenshot
        except AttributeError:
            return False

    @property
    def flagsDict(self):
        return {
            "ScreenLock": self._screen_lock.current,
            "InputLock": self._input_lock.current,
            "DemoServer": self._demo_server.current,
            "DemoClient": self._demo_client.current,
        }

    @property
    def dict(self):
        result = {
            "id": self.name,
            "name": self.name,
            "teacher": self.isTeacher,
            "connection": self.state.current,
            "description": self.description,
            "ip": self.ipAddress,
            "mac": self.macAddress,
            "objectType": self.objectType,
        }
        result.update(self.flagsDict)
        if self.user.current:
            try:
                result["user"] = self._user_map[self.user.current].username
            except AttributeError:
                result["user"] = self.user.current
        else:
            result["user"] = self.user.current
        return result

    @property
    def screenLock(self):
        return self._screen_lock.current

    @property
    def inputLock(self):
        return self._input_lock.current

    @property
    def demoServer(self):
        return self._demo_server.current

    @property
    def demoClient(self):
        return self._demo_client.current

    def _find_reachable_ip(self):  # type: () -> Optional[str]
        for ip_address in self._ip_addresses:
            try:
                reachable = self._veyon_client.ping(host=ip_address)
            except VeyonError:
                reachable = False
            if reachable:
                return ip_address
        return None

    def _fetch_feature_status(self, feature):  # type: (Feature) -> Optional[bool]
        try:
            return self._veyon_client.get_feature_status(feature, host=self.ipAddress)
        except VeyonError as exc:
            MODULE.error(
                "Fetching feature status failed: {}".format(exc)
            )  # might just be a non reachable IP. TODO: Catch errors other than 404
        return None

    def connected(self):
        return self._veyon_client.ping(host=self.ipAddress)

    def update(self):
        MODULE.info("{}: updating information.".format(self.name))
        try:
            # Big try-except block, as python-notifier silently eats exceptions.
            # Additionally python-notifier will not remove the timer if the function does not return,
            # resulting in a fast growing number of timer threads!
            veyon_user = None
            input_lock = None
            screen_lock = None
            demo_server = None
            demo_client = None
            if not self._veyon_client.ping(self.ipAddress):
                MODULE.warn("Ping not successfull for {} with IP {}".format(self.name, self.ipAddress))
                MODULE.warn("{}: Updating information was not successful.".format(self.name))
                self.reset_state()
                return
            try:
                veyon_user = self._veyon_client.get_user_info(host=self.ipAddress)
                input_lock = self._fetch_feature_status(Feature.INPUT_DEVICE_LOCK)
                screen_lock = self._fetch_feature_status(Feature.SCREEN_LOCK)
                demo_server = self._fetch_feature_status(Feature.DEMO_SERVER)
                demo_client = any(
                    [
                        self._fetch_feature_status(Feature.DEMO_CLIENT_FULLSCREEN),
                        self._fetch_feature_status(Feature.DEMO_CLIENT_WINDOWED),
                    ]
                )
            except VeyonError as exc:
                MODULE.warn("Veyon error on {}: {}".format(self.name, exc))
            if veyon_user is None:
                MODULE.warn("{}: Updating information was not successful.".format(self.name))
                self.reset_state()
                return
            self.state.set("connected")
            self.user.set(veyon_user.login)
            self._input_lock.set(input_lock)
            self._screen_lock.set(screen_lock)
            self.teacher.set(self.isTeacher)
            self._demo_server.set(demo_server)
            self._demo_client.set(demo_client)
        except Exception as exc:
            MODULE.error(
                "{}: Error updating information (raise loglevel for full traceback): {}".format(
                    self.name, exc
                )
            )
            MODULE.info("\n".join(traceback.format_stack()))
            self.reset_state()

    def start(self):
        MODULE.info("{}: Starting update timer".format(self.name))
        notifier.timer_add(ITALC_CORE_UPDATE * 1000, self.update)

    def stop(self):
        pass

    def reset_state(self):
        self.state.set("disconnected")
        self.user.set(None)
        self.teacher.set(False)
        self._input_lock.set(None)
        self._screen_lock.set(None)
        self._demo_client.set(None)
        self._demo_server.set(None)

    def open(self):
        pass  # Nothing to do for the VeyonComputer

    def close(self):
        for ip_address in self._ip_addresses:
            self._veyon_client.remove_session(ip_address)

    def _set_feature(self, feature, active=True):  # type: (Feature, bool) -> None
        if not self.connected():
            MODULE.warn("{} not connected - skipping setting feature {}".format(self.name, feature))
            return None
        try:
            self._veyon_client.set_feature(feature, host=self.ipAddress, active=active)
        except VeyonError:
            pass

    def lockScreen(self, lock):  # type: (bool) -> None
        self._set_feature(Feature.SCREEN_LOCK, lock)

    def lockInput(self, lock):  # type: (bool) -> None
        self._set_feature(Feature.INPUT_DEVICE_LOCK, lock)

    def startDemoServer(self, token):  # type: (str) -> None
        MODULE.process("Starting demo server on %s with token: %s" % (self.ipAddress, token))
        self._veyon_client.set_feature(
            Feature.DEMO_SERVER, host=self.ipAddress, active=True, arguments={"demoAccessToken": token}
        )

    def stopDemoServer(self):
        self._set_feature(Feature.DEMO_SERVER, active=False)

    def startDemoClient(self, server, token, full_screen=False):
        MODULE.process(
            "Starting demo client on %s with token %s, server %s and fullscreen: %s"
            % (self.ipAddress, token, server.ipAddress, full_screen)
        )
        arguments = {"demoAccessToken": token, "demoServerHost": server.ipAddress}
        feature = Feature.DEMO_CLIENT_FULLSCREEN if full_screen else Feature.DEMO_CLIENT_WINDOWED
        self._veyon_client.set_feature(feature, host=self.ipAddress, active=True, arguments=arguments)

    def stopDemoClient(self):
        self._set_feature(Feature.DEMO_CLIENT_FULLSCREEN, active=False)
        self._set_feature(Feature.DEMO_CLIENT_WINDOWED, active=False)

    def powerOff(self):
        self._set_feature(Feature.POWER_DOWN)

    def powerOn(self):
        if self.macAddress:
            blacklisted_interfaces = [
                x
                for x in ucr.get(
                    "ucsschool/umc/computerroom/wakeonlan/blacklisted/interfaces", ""
                ).split()
                if x
            ]
            blacklisted_interface_prefixes = [
                x
                for x in ucr.get(
                    "ucsschool/umc/computerroom/wakeonlan/blacklisted/interface_prefixes", ""
                ).split()
                if x
            ]
            target_broadcast_ips = [
                x for x in ucr.get("ucsschool/umc/computerroom/wakeonlan/target_nets", "").split() if x
            ]
            target_broadcast_ips = target_broadcast_ips or ["255.255.255.255"]
            wakeonlan.send_wol_packet(
                self.macAddress,
                blacklisted_interfaces=blacklisted_interfaces,
                blacklisted_interface_prefixes=blacklisted_interface_prefixes,
                target_broadcast_ips=target_broadcast_ips,
            )
        else:
            MODULE.error("%s: no MAC address set - skipping powerOn" % (self.ipAddress,))

    def restart(self):
        self._set_feature(Feature.REBOOT)

    def logOut(self):
        self._set_feature(Feature.USER_LOGOFF)
