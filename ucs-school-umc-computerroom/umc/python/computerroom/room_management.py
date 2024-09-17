#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
#
# Copyright 2012-2024 Univention GmbH
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
import random
import re
import tempfile
import threading
import time
import traceback
import uuid
from typing import TYPE_CHECKING, Any, List, Optional, TypeVar  # noqa: F401

import ldap
from ldap.dn import explode_rdn
from ldap.filter import filter_format

from ucsschool.lib.models.base import MultipleObjectsError
from ucsschool.lib.models.group import ComputerRoom
from ucsschool.lib.models.user import User
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from ucsschool.veyon_client.client import VeyonClient
from ucsschool.veyon_client.models import (
    AuthenticationMethod,
    Dimension,
    Feature,
    ScreenshotFormat,
    VeyonConnectionError,
    VeyonError,
)
from univention.admin.uexceptions import noObject
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules.computerroom import wakeonlan

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType  # noqa: F401

LV = TypeVar("LV")

_ = Translation("ucs-school-umc-computerroom").translate

VEYON_USER_REGEX = r"(?P<domain>.*)\\(?P<username>[^\(\\]+)$"

VEYON_KEY_FILE = "/etc/ucsschool-veyon/key.pem"


class ComputerRoomError(Exception):
    pass


class UserInfo(object):
    def __init__(self, ldap_dn, username, isTeacher=False, hide_screenshot=False):
        # type: (str, str, Optional[bool], Optional[bool], Optional[bool]) -> None
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

        if not userstr:
            raise AttributeError("Received empty user string: {!r}".format(userstr))

        if not match:
            MODULE.warning("Invalid user string format: {!r}".format(userstr))
            return userstr
        else:
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
            MODULE.warning(
                'Unknown user "%s". It is assumed the user is a local account, prepending LOCAL\\.'
                % username
            )
            dict.__setitem__(self, userstr, UserInfo("", "LOCAL\\{}".format(username)))
            return

        blacklisted_groups = {
            x.strip().lower()
            for x in ucr.get(
                "ucsschool/umc/computerroom/hide_screenshots/groups", "Domain Admins"
            ).split(",")
        }
        users_groupmemberships = {explode_rdn(x, True)[0].lower() for x in userobj["groups"]}
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


class ComputerRoomManager(dict):
    SCHOOL = None
    ROOM = None
    ROOM_DN = None
    VEYON_BACKEND = True

    def __init__(self):
        dict.__init__(self)
        self._user_map = UserMap(VEYON_USER_REGEX)
        self._veyon_client = None  # type: Optional[VeyonClient]
        self.screenshot_dimension = self.get_screenshot_dimension()

    @staticmethod
    def get_screenshot_dimension():
        ucr_value = ucr.get("ucsschool/umc/computerroom/screenshot_dimension")

        if not ucr_value:
            return None

        ucr_dim = re.match(r"(\d*)x(\d*)", ucr_value)

        if ucr_dim:
            LOWER_BOUND = 240
            UPPER_BOUND = 8000
            try:
                width = int(ucr_dim.group(1))
                if not (LOWER_BOUND <= width <= UPPER_BOUND):
                    MODULE.warning(
                        "Set width of screenshot is not within bounds "
                        "{} and {}, falling back to native resolution.".format(LOWER_BOUND, UPPER_BOUND)
                    )
                    width = None
            except ValueError:
                width = None
            try:
                height = int(ucr_dim.group(2))
                if not (LOWER_BOUND <= height <= UPPER_BOUND):
                    MODULE.warning(
                        "Set height of screenshot is not within bounds "
                        "{} and {}, falling back to native resolution.".format(LOWER_BOUND, UPPER_BOUND)
                    )
                    height = None
            except ValueError:
                height = None

            return Dimension(width, height)
        else:
            MODULE.warning(
                "UCR variable 'ucsschool/umc/computerroom/screenshot_dimension' has "
                "been set to a value with an incorrect format: {}".format(ucr_value)
            )
            return None

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
        """Return a list of valid domain users who are logged into the computers"""
        valid_users = []
        for computer in self.values():
            if computer.user.current and computer.connected():
                user_info = self._user_map[computer.user.current]
                valid_users.append(user_info.username)
        return valid_users

    @property
    def veyon_backend(self):  # type: () -> bool
        return ComputerRoomManager.VEYON_BACKEND

    @property
    def veyon_client(self):  # type: () -> VeyonClient
        if not self._veyon_client:
            with open(VEYON_KEY_FILE) as fp:
                key_data = fp.read().strip()

            self._veyon_client = VeyonClient(
                "http://localhost:8888/api/v1",
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
            for computer in self.values():
                computer.stop()
                computer.close()
                del computer  # FIXME: no-op, needs to be removed from dict
            self.clear()
            ComputerRoomManager.ROOM = None
            ComputerRoomManager.ROOM_DN = None
            ComputerRoomManager.VEYON_BACKEND = True

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

        MODULE.info("Computerroom {!r} will be initialized with Computers.".format(self.ROOM))
        self._user_map = UserMap(VEYON_USER_REGEX)
        for computer in computers:
            try:
                comp = VeyonComputer(
                    computer.get_udm_object(lo),
                    self.veyon_client,
                    self._user_map,
                    self.screenshot_dimension,
                )
                comp.start()
                self.__setitem__(comp.name, comp)
            except ComputerRoomError as exc:
                MODULE.warn("Computer could not be added: {}".format(exc))

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
        clients = [comp for comp in self.values() if comp.name != demo_server and comp.connected()]
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
        demo_access_token = str(uuid.uuid4())
        server.startDemoServer(token=demo_access_token)
        for client in clients:
            client.startDemoClient(
                server=server,
                token=demo_access_token,
                full_screen=False if client.name in teachers else fullscreen,
            )

    def stopDemo(self):
        if self.demoServer is not None:
            self.demoServer.stopDemoServer()
        # This is necessary since Veyon has a considerable delay with exposing its demo client status.
        # So we just end the demo client on all computers.
        clients = self.values()
        for client in clients:
            client.stopDemoClient()


class VeyonComputer(threading.Thread):
    def __init__(self, computer, veyon_client, user_map, screenshot_dimension):
        # type: (Any, VeyonClient, UserMap) -> None
        super(VeyonComputer, self).__init__()
        self._computer = computer  # type: Any
        self._veyon_client = veyon_client  # type: VeyonClient
        self._user_map = user_map
        self._ip_addresses = self._computer.info.get("ip", [])  # type: List[str]
        self._reachable_ip = None
        self._username = LockableAttribute()
        self._update_successful = LockableAttribute(initial_value=True)
        self._state = LockableAttribute(initial_value="disconnected")
        self._teacher = LockableAttribute(initial_value=False)
        self._screen_lock = LockableAttribute(initial_value=None)
        self._input_lock = LockableAttribute(initial_value=None)
        self._demo_server = LockableAttribute(initial_value=None)
        self._demo_client = LockableAttribute(initial_value=None)
        self._timer = None
        self._update_interval = None
        self.should_run = True
        self.screenshot_dimension = screenshot_dimension

    def run(self):
        while self.should_run:
            self.update()
            time.sleep(self.update_interval + random.uniform(0, 1))  # nosec

    @property
    def update_interval(self):
        if not self._update_interval:
            try:
                self._update_interval = int(ucr.get("ucsschool/umc/computerroom/update-interval", 1))
            except ValueError:
                MODULE.warning("ucsschool/umc/computerroom/update-interval is not a valid integer")
                self._update_interval = 1
            if self._update_interval <= 0:
                MODULE.warning("ucsschool/umc/computerroom/update-interval should be positive")
                self._update_interval = 1
        return self._update_interval

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
    def configuration_ok(self):
        if not self._ip_addresses:
            MODULE.warn("Computer {} is missing an IP.".format(self.name))
            return False
        return True

    @property
    def ipAddress(self):
        if self._reachable_ip:
            return self._reachable_ip
        if not ucr.is_true("ucsschool/umc/computerroom/ping-client-ip-addresses", False):
            self._reachable_ip = self._ip_addresses[0] if self._ip_addresses else ""
        if self._ip_addresses:
            try:
                self._reachable_ip = self._find_reachable_ip()
            except VeyonConnectionError as exc:
                if self._update_successful.current:
                    MODULE.warn("Could not connecto to veyon proxy {}".format(exc))
                return ""
            return self._reachable_ip if self._reachable_ip else self._ip_addresses[0]
        return ""

    @property
    def macAddress(self):
        return (self._computer.info.get("mac") or [""])[0]

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

    def screenshot(self, size=None):
        if not self.connected():
            MODULE.warn("{} not connected - skipping screenshot".format(self.name))
            return None
        width = getattr(self.screenshot_dimension, "width", None)
        height = getattr(self.screenshot_dimension, "height", None)
        size_to_width = {"2": 640, "3": 480, "4": 320}
        if size in size_to_width:
            width = min(size_to_width[size], width) if width else size_to_width[size]
        dimension = Dimension(width, height)
        image = None
        for ip_address in self._ip_addresses:
            try:
                image = self._veyon_client.get_screenshot(
                    host=ip_address,
                    screenshot_format=ScreenshotFormat.JPEG,
                    dimension=dimension,
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
            "configurationOK": self.configuration_ok,
        }
        result.update(self.flagsDict)
        if self.user.current:
            try:
                result["user"] = self._user_map[self.user.current].username
            except AttributeError:
                result["user"] = "LOCAL\\{}".format(self.user.current)
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
            # might just be a non reachable IP. TODO: Catch errors other than 404:
            MODULE.error("Fetching feature status failed: {}".format(exc))
        return None

    def connected(self):
        try:
            return self._veyon_client.ping(host=self.ipAddress)
        except VeyonConnectionError as exc:
            MODULE.warning("Connecting to Veyon failed: {}".format(exc))
            return False

    def update(self):
        MODULE.info("{}: updating information.".format(self.name))
        try:
            veyon_user = None
            input_lock = None
            screen_lock = None
            demo_server = None
            demo_client = None
            if not self._veyon_client.ping(self.ipAddress):
                MODULE.info("Ping not successfull for {} with IP {}".format(self.name, self.ipAddress))
                MODULE.info("{}: Updating information was not successful.".format(self.name))
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
                # InvalidConnection (2)from WebAPI
                # remove current session as it is invalid
                # (e.g. webapi has been restarted)
                if exc.code == 2:
                    self._veyon_client.remove_session(host=self.ipAddress)
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
            self._update_successful.set(True)
        except VeyonConnectionError as exc:
            if self._update_successful.current:
                # Only log if previous attempt was successful
                self._update_successful.set(False)
                MODULE.warning("Error updating information for {}: {}".format(self.name, exc))
            self.reset_state()
        except Exception:
            self._update_successful.set(False)
            MODULE.warning(
                "Error updating information for {}: {}".format(self.name, traceback.format_exc())
            )
            self.reset_state()

    def stop(self):
        self.should_run = False

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
            try:
                self._veyon_client.remove_session(ip_address)
            except VeyonConnectionError as exc:
                MODULE.warning("Could not remove veyon session for {}: {}".format(self.name, exc))

    def _set_feature(self, feature, active=True):  # type: (Feature, bool) -> None
        try:
            self._veyon_client.set_feature(feature, host=self.ipAddress, active=active)
        except VeyonError:
            MODULE.warning(
                "{} could not be reached - skipped setting feature{}".format(self.name, feature)
            )
        except VeyonConnectionError:
            MODULE.warning(
                "Error connecting with the veyon proxy - skipped setting feature {} for {}".format(
                    feature, self.name
                )
            )

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
