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

import datetime
import fcntl
import importlib
import inspect
import itertools
import os
import signal
import subprocess
import time
import traceback
from ipaddress import ip_address
from pipes import quote
from random import Random

import ldap
import psutil
from ldap.filter import filter_format
from six.moves.urllib_parse import urlsplit

import univention.admin.uexceptions as udm_exceptions
from ucsschool.lib import internetrules

try:
    from .room_management import ComputerRoomError, ComputerRoomManager
except ImportError:
    pass
from ucsschool.lib.models.group import ComputerRoom
from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import User
from ucsschool.lib.roles import create_ucsschool_role_string, role_computer_room_backend_veyon
from ucsschool.lib.school_umc_base import Display, SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from ucsschool.lib.schoollessons import SchoolLessons
from ucsschool.lib.smbstatus import SMB_Status
from ucsschool.veyon_client.models import VeyonConnectionError
from univention.admin.syntax import gid
from univention.admin.uldap import getMachineConnection
from univention.config_registry import handler_set, handler_unset
from univention.config_registry.frontend import ucr_update
from univention.lib import atjobs
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import allow_get_request, sanitize, simple_response
from univention.management.console.modules.sanitizers import (
    BooleanSanitizer,
    ChoicesSanitizer,
    DNSanitizer,
    ListSanitizer,
    Sanitizer,
    StringSanitizer,
)

_ = Translation("ucs-school-umc-computerroom").translate

ROOMDIR = "/var/cache/ucs-school-umc-computerroom"
_SCREENSHOT_DIR = "/usr/share/univention-management-console-frontend/js/dijit/themes/umc/icons/scalable"
FN_SCREENSHOT_DENIED = os.path.join(_SCREENSHOT_DIR, _("screenshot_denied.svg"))
FN_SCREENSHOT_NOTREADY = os.path.join(_SCREENSHOT_DIR, _("screenshot_notready.svg"))


def compare_dn(a, b):
    return a and b and a.lower() == b.lower()


def _getRoomFile(roomDN):
    """Get path to a room file from a computer rooms DN."""
    room_name = ComputerRoomDNSanitizer(required=True, _return_room_name=True).sanitize(
        "roomDN", {"roomDN": roomDN}
    )
    return os.path.join(ROOMDIR, room_name)


def _isUmcProcess(pid):
    if not psutil.pid_exists(pid):
        return False  # process is not running anymore
    # process is running
    cmdline = psutil.Process(pid).cmdline()
    # check if the process is the computerroom UMC module
    return "computerroom" in cmdline and any(
        "univention-management-console-module" in line for line in cmdline
    )


def _readRoomInfo(roomDN):
    """returns a dict of properties for the current room."""
    roomFile = _getRoomFile(roomDN)
    info = {}
    if os.path.exists(roomFile):
        try:
            with open(roomFile) as f:
                # the room file contains key-value pairs, separated by '='
                # ... parse the file as dict
                lines = f.readlines()
                info = dict(iline.strip().split("=", 1) for iline in lines if "=" in iline)
        except (OSError, IOError, ValueError) as exc:
            MODULE.warn("Failed to read file %s: %s" % (roomFile, exc))

    # special handling for the PID
    if "pid" in info:
        try:
            # translate PID to int and verify that it is a UMC process
            pid = int(info.pop("pid"))
            if _isUmcProcess(pid):
                info["pid"] = pid
        except (ValueError, OverflowError):
            pass  # invalid format, do nothing

    return info


def _updateRoomInfo(roomDN, **kwargs):
    """Update infos for a room, i.e., leave unspecified values untouched."""
    info = _readRoomInfo(roomDN)
    new_info = {}
    for key in ("user", "exam", "examDescription", "examEndTime", "atjobID"):
        # set the specified value (can also be None for deleting the attribute)
        # or fallback to currently set value
        new_info[key] = kwargs.get(key, info.get(key))
    _writeRoomInfo(roomDN, **new_info)


def _writeRoomInfo(roomDN, user=None, exam=None, examDescription=None, examEndTime=None, atjobID=None):
    """Set infos for a room and lock the room."""
    info = {
        "room": roomDN,
        "user": user,
        "exam": exam,
        "examDescription": examDescription,
        "examEndTime": examEndTime,
        "atjobID": atjobID,
        "pid": os.getpid(),
    }
    MODULE.info('Writing info file for room "%s": %s' % (roomDN, info))
    try:
        # write user DN in the room file
        with open(_getRoomFile(roomDN), "w") as fd:
            fcntl.lockf(fd, fcntl.LOCK_EX)
            try:
                for key, val in info.items():
                    if val is not None:
                        fd.write("%s=%s\n" % (key, val))
            finally:
                # make sure that the file is unlocked
                fcntl.lockf(fd, fcntl.LOCK_UN)
    except EnvironmentError:
        MODULE.warn("Failed to write file: %s" % _getRoomFile(roomDN))


def _getRoomOwner(roomDN):
    """Read the room lock file and return the saved user DN. If it does not exist, return None."""
    info = _readRoomInfo(roomDN)
    if "pid" not in info:
        return None
    return info.get("user")


def _freeRoom(roomDN, userDN):
    """Remove the lock file if the room is locked by the given user"""
    roomFile = _getRoomFile(roomDN)
    MODULE.warn("lockDN: %s, userDN: %s" % (_getRoomOwner(roomDN), userDN))
    if _getRoomOwner(roomDN) == userDN:
        try:
            os.unlink(roomFile)
        except (OSError, IOError):
            MODULE.warn("Failed to remove room lock file: %s" % roomFile)


def check_room_access(func):
    """Block access to session from other users"""

    def _decorated(self, request, *args, **kwargs):
        self._checkRoomAccess(request)
        return func(self, request, *args, **kwargs)

    return _decorated


def reset_room_settings(room, hosts):
    unset_vars = [
        "samba/printmode/room/{}",
        "samba/sharemode/room/{}",
        "proxy/filter/room/{}/rule",
    ]
    extract_from_vars = [
        "samba/printmode/hosts/none",
        "cups/printmode/hosts/none",
        "samba/othershares/hosts/deny",
        "samba/share/Marktplatz/hosts/deny",
        "proxy/filter/room/{}/ip",
    ]
    update_vars = {key.format(room): None for key in unset_vars}
    ucr.load()
    hosts = set(hosts)

    for variable in (v.format(room) for v in extract_from_vars):
        if ucr.get(variable):
            old = set(ucr[variable].split(" "))
        else:
            old = set()
        new = old.difference(hosts)
        if new:
            update_vars[variable] = " ".join(new)
        else:
            update_vars[variable] = None
    ucr_update(ucr, update_vars)


class IPAddressSanitizer(Sanitizer):
    def _sanitize(self, value, name, further_fields):
        try:
            return ip_address(value)
        except ValueError as exc:
            self.raise_validation_error("%s" % (exc,))


class PeriodSanitizer(StringSanitizer):
    def _sanitize(self, value, name, further_fields):
        try:
            return datetime.datetime.strptime(value or "00:00", "%H:%M").time()
        except ValueError as exc:
            self.raise_validation_error("Failed to read end time: %s" % (exc,))


class ComputerSanitizer(StringSanitizer):

    instance = None

    def _sanitize(self, value, name, further_args):
        value = super(ComputerSanitizer, self)._sanitize(value, name, further_args)
        try:
            return self.instance._computerroom.get(value)
        except KeyError:
            raise UMC_Error(_("Unknown computer"))


class ComputerRoomDNSanitizer(DNSanitizer):
    def __init__(self, *args, **kwargs):
        # don't want to modify request.options, so cannot use "may_change_value"
        try:
            self._return_room_name = kwargs.pop("_return_room_name")
        except KeyError:
            self._return_room_name = False
        super(ComputerRoomDNSanitizer, self).__init__(*args, **kwargs)

    def _sanitize(self, value, name, further_args):
        value = super(ComputerRoomDNSanitizer, self)._sanitize(value, name, further_args)
        try:
            room_name = ldap.dn.str2dn(value)[0][0][1]
        except (KeyError, ldap.DECODING_ERROR):
            raise UMC_Error(_("Invalid room DN: %s") % (value,))
        try:
            gid.parse(room_name)
        except udm_exceptions.valueError:
            raise UMC_Error(_("Invalid room DN: %s") % (value,))
        if not os.path.basename(room_name) == room_name:
            #  Check for path traversal
            raise UMC_Error(_("Invalid room DN: %s") % (value,))
        if room_name and self._return_room_name:
            return room_name
        elif not self._return_room_name:
            return value
        else:
            raise UMC_Error(_("Invalid room DN: %s") % value)


class Plugin(object):

    gettext_domain = "ucs-school-umc-computerroom"

    def __init__(self, computerroom, manager):
        self.computerroom = computerroom
        self.manager = manager
        self._ = Translation(self.gettext_domain).translate

    @property
    def name(self):
        return type(self).__name__

    def button(self):
        return {"name": self.name}


class Instance(SchoolBaseModule):
    ATJOB_KEY = "UMC-computerroom"

    def prepare(self, request):
        super(Instance, self).prepare(request)
        self.__init_user_dn = request.user_dn

    def init(self):
        SchoolBaseModule.init(self)
        ComputerSanitizer.instance = self
        self._computerroom = ComputerRoomManager()
        self._random = Random()
        self._random.seed()
        self._lessons = SchoolLessons()
        self._ruleEndAt = None
        self._load_plugins()

    def _load_plugins(self):
        self._plugins = {}
        for module in os.listdir(os.path.join(os.path.dirname(__file__), "plugins")):
            if module.endswith(".py"):
                try:
                    module = importlib.import_module(
                        "univention.management.console.modules.computerroom.plugins.%s" % (module[:-3],)
                    )
                except ImportError:
                    MODULE.error(traceback.format_exc())
                for name, plugin in inspect.getmembers(module, inspect.isclass):
                    MODULE.info("Loading plugin %r from module %r" % (plugin, module))
                    if not name.startswith("_") and plugin is not Plugin and issubclass(plugin, Plugin):
                        try:
                            plugin = plugin(self, self._computerroom)
                        except Exception:
                            MODULE.error(traceback.format_exc())
                        else:
                            self._plugins[plugin.name] = plugin

    def destroy(self):
        """Remove lock file when UMC module exists"""
        MODULE.info("Cleaning up")
        if self._computerroom.room:
            # do not remove lock file during exam mode
            info = _readRoomInfo(self._computerroom.roomDN)
            MODULE.info("room info: %s" % (info,))
            if info and not info.get("exam"):
                MODULE.info(
                    "Removing lock file for room %s (%s)"
                    % (self._computerroom.room, self._computerroom.roomDN)
                )
                _freeRoom(self._computerroom.roomDN, self.__init_user_dn)
            for comp in self._computerroom.values():
                comp.should_run = False
            while any(comp.is_alive() for comp in self._computerroom.values()):
                time.sleep(0.1)
            MODULE.info("All threads dead!")

    def lessons(self, request):
        """Returns a list of school lessons. Lessons in the past are filtered out"""
        current = self._lessons.current
        if current is None:
            current = self._lessons.previous

        if current:
            lessons = [x for x in self._lessons.lessons if x.begin >= current.begin]
        else:
            lessons = self._lessons.lessons
        self.finished(request.id, [x.name for x in lessons])

    def internetrules(self, request):
        """Returns a list of available internet rules"""
        self.finished(request.id, [x.name for x in internetrules.list()])

    def _room_acquire(self, request, roomDN, ldap_user_read):
        """Acquires the specified computerroom"""
        success = True
        message = "OK"

        umc_veyon_client_error_message = _(
            "Computers in the computerroom can currently not be remote controlled, "
            "because the associated service is not available. "
            "The system will try to restart this service, please try again "
            "in a few moments. "
            "If the problem persists, please contact the system administrator."
        )
        umc_veyon_client_error_log_message = (
            "Connection to Veyon WebAPI Server (UCS@school Veyon Proxy) failed."
        )
        try:
            self._computerroom.veyon_client.test_connection()
        except VeyonConnectionError:
            MODULE.warning(umc_veyon_client_error_log_message)

        # match the corresponding school OU
        try:
            room = ComputerRoom.from_dn(roomDN, None, ldap_user_read)
            school = room.school
        except udm_exceptions.noObject:
            success = False
            message = "UNKNOWN_ROOM"
        else:
            # set room and school
            if self._computerroom.school != school:
                self._computerroom.school = school
            if self._computerroom.room != roomDN:
                try:
                    self._computerroom.room = roomDN
                except ComputerRoomError:
                    success = False
                    message = "EMPTY_ROOM"
                except VeyonConnectionError:
                    MODULE.error(umc_veyon_client_error_log_message)
                    MODULE.error(traceback.format_exc())
                    raise UMC_Error(
                        message=umc_veyon_client_error_message, traceback=traceback.format_exc()
                    )

        # update the room info file
        if success:
            _updateRoomInfo(roomDN, user=request.user_dn)
            if not compare_dn(_getRoomOwner(roomDN), request.user_dn):
                success = False
                message = "ALREADY_LOCKED"

        info = {}
        if success:
            info = _readRoomInfo(roomDN)
        return success, message, info

    @sanitize(room=ComputerRoomDNSanitizer(required=True))
    @LDAP_Connection()
    def room_acquire(self, request, ldap_user_read=None):
        """Acquires the specified computerroom"""
        roomDN = request.options["room"]

        success, message, info = self._room_acquire(request, roomDN, ldap_user_read)

        self.finished(
            request.id,
            {
                "success": success,
                "message": message,
                "info": {
                    "exam": info.get("exam"),
                    "examDescription": info.get("examDescription"),
                    "examEndTime": info.get("examEndTime"),
                    "room": info.get("room"),
                    "user": info.get("user"),
                },
            },
        )

    @sanitize(school=SchoolSanitizer(required=True))
    @LDAP_Connection()
    def rooms(self, request, ldap_user_read=None):
        """Returns a list of all available rooms"""
        rooms = []
        veyon_backend_role = create_ucsschool_role_string(role_computer_room_backend_veyon, "-")
        try:
            all_rooms = ComputerRoom.get_all(
                ldap_user_read,
                request.options["school"],
                filter_str="(ucsschoolRole={})".format(veyon_backend_role),
            )
        except udm_exceptions.noObject:
            all_rooms = []

        for room in all_rooms:
            room_info = _readRoomInfo(room.dn)
            user_dn = room_info.get("user")

            locked = (
                user_dn
                and not compare_dn(user_dn, request.user_dn)
                and ("pid" in room_info or "exam" in room_info)
            )
            if locked:
                try:
                    # open the corresponding UDM object to get a displayable user name
                    user_dn = Display.user(
                        User.from_dn(user_dn, None, ldap_user_read).get_udm_object(ldap_user_read)
                    )
                except udm_exceptions.base as exc:
                    MODULE.warn("Cannot open LDAP information for user %r: %s" % (user_dn, exc))

            rooms.append(
                {
                    "id": room.dn,
                    "label": room.get_relative_name(),
                    "user": user_dn,
                    "locked": locked,
                    "exam": room_info.get("exam"),
                    "examDescription": room_info.get("examDescription"),
                    "examEndTime": room_info.get("examEndTime"),
                }
            )

        self.finished(request.id, rooms)

    @sanitize(
        ipaddress=ListSanitizer(
            required=True, sanitizer=IPAddressSanitizer(), min_elements=1, max_elements=10
        )
    )
    @LDAP_Connection()
    def guess_room(self, request, ldap_user_read=None):
        ipaddress = request.options["ipaddress"]
        host_filter = self._get_host_filter(ipaddress)
        computers = ldap_user_read.searchDn(host_filter)
        if computers:
            room_filter = self._get_room_filter(computers)
            for school in School.get_all(ldap_user_read):
                school = school.name
                for room in ComputerRoom.get_all(ldap_user_read, school, room_filter):
                    self.finished(request.id, {"school": school, "room": room.dn})
                    return
        self.finished(request.id, {"school": None, "room": None})

    def _get_room_filter(self, computers):
        return "(|(%s))" % ")(".join(
            filter_format("uniqueMember=%s", (computer,)) for computer in computers
        )

    def _get_host_filter(self, ipaddresses):
        records = {4: "aRecord=%s", 6: "aAAARecord=%s"}
        return "(|(%s))" % ")(".join(
            filter_format(records[ipaddress.version], (ipaddress.exploded,)) for ipaddress in ipaddresses
        )

    def _checkRoomAccess(self, request):
        if not self._computerroom.room:
            return  # no room has been selected so far

        # make sure that we run the current room session
        userDN = _getRoomOwner(self._computerroom.roomDN)
        if userDN and not compare_dn(userDN, request.user_dn):
            raise UMC_Error(_("A different user is already running a computer room session."))

    def _get_computers(self, only_changed=False):
        result = []
        for computer in self._computerroom.values():
            if only_changed and not computer.hasChanged:
                continue
            result.append(computer.dict)
        return result

    @LDAP_Connection()
    def query(self, request, ldap_user_read=None):
        """Searches for entries. This is not allowed if the room could not be acquired."""
        if not self._computerroom.school or not self._computerroom.room:
            raise UMC_Error(_("no room selected"))

        if request.options.get("reload", False):
            self._computerroom.room = self._computerroom.room  # believe me that makes sense :)
        result = self._get_computers()
        result.sort(key=lambda c: c["id"])
        MODULE.info("computerroom.query: result: %s" % (result,))
        self.finished(request.id, result)

    @LDAP_Connection()
    def update(self, request, ldap_user_read=None):
        """
        Returns an update for the computers in the selected
        room. Just attributes that have changed since the last call will
        be included in the result
        """
        if not self._computerroom.school or not self._computerroom.room:
            raise UMC_Error(_("no room selected"))
        computers = self._get_computers(only_changed=True)
        info = _readRoomInfo(self._computerroom.roomDN)
        result = {
            "computers": computers,
            "room_info": info,
            "locked": info.get("user", request.user_dn) != request.user_dn,
            "user": request.user_dn,
        }

        if result["locked"] and "pid" in info:
            result["user"] = info["user"]
            # somebody else acquired the room, the room is locked
            try:
                # open the corresponding UDM object to get a displayable user name
                result["user"] = Display.user(
                    User.from_dn(result["user"], None, ldap_user_read).get_udm_object(ldap_user_read)
                )
            except udm_exceptions.base as exc:
                # could not oben the LDAP object, show the DN
                MODULE.warn("Cannot open LDAP information for user %r: %s" % (result["user"], exc))

        # settings info
        if self._ruleEndAt is not None:
            diff = self._positiveTimeDiff()
            if diff is not None:
                result["settingEndsIn"] = diff.seconds // 60

        MODULE.info("Update: result: %s" % (result,))
        self.finished(request.id, result)

    def _positiveTimeDiff(self):
        now = datetime.datetime.now()
        end = datetime.datetime.now()
        end = end.replace(hour=self._ruleEndAt.hour, minute=self._ruleEndAt.minute)
        if now > end:
            return None
        return end - now

    @check_room_access
    @sanitize(
        computer=ComputerSanitizer(required=True),
        device=ChoicesSanitizer(["screen", "input"], required=True),
        lock=BooleanSanitizer(required=True),
    )
    @simple_response
    def lock(self, computer, device, lock):
        """Lock or Unlock the screen or input of a specific computer"""
        MODULE.warn("Locking device %s" % (device,))
        if device == "screen":
            computer.lockScreen(lock)
        else:
            computer.lockInput(lock)

    @allow_get_request
    @check_room_access
    @sanitize(computer=ComputerSanitizer(required=True))
    def screenshot(self, request):
        """
        Returns a JPEG image containing a screenshot of the given computer
        or a premade SVG image for special situations like when a screenshots is not ready yet
        """
        computer = request.options["computer"]
        tmpfile = computer.screenshot(size=request.options.get("size", None))
        if computer.hide_screenshot:
            mimetype = "image/svg+xml"
            filename = FN_SCREENSHOT_DENIED
        elif tmpfile is None:
            mimetype = "image/svg+xml"
            filename = FN_SCREENSHOT_NOTREADY
        else:
            mimetype = "image/jpeg"
            filename = tmpfile.name

        MODULE.info("screenshot(%s): hide screenshot = %r" % (computer.name, computer.hide_screenshot))
        try:
            with open(filename, "rb") as fd:
                response = fd.read()
        except EnvironmentError as exc:
            MODULE.error("Unable to load screenshot file %r: %s" % (filename, exc))
        try:
            if tmpfile:
                os.unlink(tmpfile.name)
        except EnvironmentError as exc:
            MODULE.error("Unable to remove temporary screenshot file %r: %s" % (tmpfile.name, exc))

        self.finished(request.id, response, mimetype=mimetype)

    def _read_rules_end_at(self):
        room_file = _getRoomFile(self._computerroom.roomDN)
        rule_end_at = None
        if os.path.exists(room_file):
            roomInfo = _readRoomInfo(self._computerroom.roomDN)
            atjob_id = roomInfo.get("atjobID")
            if atjob_id is not None:
                job = atjobs.load(atjob_id, extended=True)
                if job is not None and job.execTime >= datetime.datetime.now():
                    rule_end_at = job.execTime
        else:
            # Fallback in case the roomInfo file was deleted
            MODULE.warn("No room file {}".format(self._computerroom.roomDN))
            for job in atjobs.list(extended=True):
                if job.comments.get(Instance.ATJOB_KEY, False) == self._computerroom.room:
                    if job.execTime >= datetime.datetime.now():
                        rule_end_at = job.execTime
                    break
        return rule_end_at

    @simple_response(with_request=True)
    def settings_get(self, request):
        """Return the current settings for a room"""
        if not self._computerroom.school or not self._computerroom.room:
            raise UMC_Error(_("no room selected"))

        ucr.load()
        rule = ucr.get("proxy/filter/room/%s/rule" % self._computerroom.room, "none")
        if rule == request.username:
            rule = "custom"
        shareMode = ucr.get("samba/sharemode/room/%s" % self._computerroom.room, "all")
        # load custom rule:
        key_prefix = "proxy/filter/setting-user/%s/domain/whitelisted/" % request.username
        custom_rules = []
        for key in ucr:
            if key.startswith(key_prefix):
                custom_rules.append(ucr[key])

        printMode = ucr.get("samba/printmode/room/%s" % self._computerroom.room, "default")

        # find end of lesson
        period = self._lessons.current
        if period is None:
            if self._lessons.next:  # between two lessons
                period = self._lessons.next.end
            else:  # school is out ... 1 hour should be good (FIXME: configurable?)
                period = datetime.datetime.now() + datetime.timedelta(hours=1)
                period = period.time()
        else:
            period = period.end

        if rule == "none" and shareMode == "all" and printMode == "default":
            self._ruleEndAt = None
        else:
            self._ruleEndAt = self._read_rules_end_at()

        if self._ruleEndAt:
            time = self._ruleEndAt.time()
            for lesson in self._lessons.lessons:
                if time == lesson.begin:
                    period = lesson
                    break

        return {
            "internetRule": rule,
            "customRule": "\n".join(custom_rules),
            "shareMode": shareMode,
            "printMode": printMode,
            "period": str(period),
        }

    @check_room_access
    @simple_response(with_request=True)
    def finish_exam(self, request):
        """Finish the exam in the current room"""
        self._settings_set(
            request, printMode="default", internetRule="none", shareMode="all", customRule=""
        )
        _updateRoomInfo(self._computerroom.roomDN, exam=None, examDescription=None, examEndTime=None)

    @check_room_access
    def _start_exam(self, request, room, exam, examDescription, examEndTime):
        """Start an exam in the current room"""
        info = _readRoomInfo(room)
        if info.get("exam"):
            raise UMC_Error(
                _("In this room an exam is currently already written. Please select another room.")
            )

        _updateRoomInfo(
            self._computerroom.roomDN,
            exam=exam,
            examDescription=examDescription,
            examEndTime=examEndTime,
        )

    @sanitize(
        room=ComputerRoomDNSanitizer(required=True),
        exam=StringSanitizer(required=True),
        examDescription=StringSanitizer(required=True),
        examEndTime=StringSanitizer(required=True),
    )
    @simple_response(with_request=True)
    def start_exam(self, request, room, exam, examDescription, examEndTime):
        """Start an exam in the current room"""
        self._start_exam(request, room, exam, examDescription, examEndTime)

    @sanitize(
        printMode=ChoicesSanitizer(["none", "default"], required=True),
        internetRule=StringSanitizer(required=True),
        shareMode=ChoicesSanitizer(["home", "all"], required=True),
        period=PeriodSanitizer(default="00:00", required=False),
        customRule=StringSanitizer(allow_none=True, required=False),
    )
    @simple_response(with_request=True)
    def settings_set(self, request, printMode, internetRule, shareMode, period=None, customRule=None):
        return self._settings_set(request, printMode, internetRule, shareMode, period, customRule)

    @check_room_access
    def _settings_set(self, request, printMode, internetRule, shareMode, period=None, customRule=None):
        """Defines settings for a room"""
        if not self._computerroom.school or not self._computerroom.room:
            raise UMC_Error(_("no room selected"))

        MODULE.debug("set settings for {}".format(self._computerroom.roomDN))
        # find AT jobs for the room at remove them
        jobs = atjobs.list(extended=True)
        for job in jobs:
            if job.comments.get(Instance.ATJOB_KEY, False) == self._computerroom.room:
                job.rm()
        lo, po = getMachineConnection()
        hosts = list(
            itertools.chain.from_iterable(
                [
                    c.ip_address
                    for c in ComputerRoom.from_dn(self._computerroom.roomDN, None, lo).get_computers(lo)
                    if not c.teacher_computer
                ]
            )
        )
        reset_room_settings(self._computerroom.room, hosts)
        _updateRoomInfo(self._computerroom.roomDN, atjobID=None)

        roomInfo = _readRoomInfo(self._computerroom.roomDN)
        in_exam_mode = roomInfo.get("exam")

        # reset to defaults. No atjob is necessary.
        if internetRule == "none" and shareMode == "all" and printMode == "default":
            self._ruleEndAt = None
            self.reset_smb_connections()
            self.reload_cups()
            return

        # collect new settings
        vset = {}
        vappend = {}
        vunset_now = []

        # print mode
        if printMode == "none":
            vappend["samba/printmode/hosts/%s" % printMode] = hosts
            vappend["cups/printmode/hosts/%s" % printMode] = hosts
            vset["samba/printmode/room/%s" % self._computerroom.room] = printMode
        else:
            vunset_now.append("samba/printmode/room/%s" % self._computerroom.room)

        # share mode
        if shareMode == "home":
            vset["samba/sharemode/room/%s" % self._computerroom.room] = shareMode
            vappend["samba/othershares/hosts/deny"] = hosts
            vappend["samba/share/Marktplatz/hosts/deny"] = hosts
        else:
            vunset_now.append("samba/sharemode/room/%s" % self._computerroom.room)

        # internet rule
        if internetRule != "none":
            vappend["proxy/filter/room/%s/ip" % self._computerroom.room] = hosts
            if internetRule == "custom":
                # remove old rules
                i = 1
                while True:
                    var = "proxy/filter/setting-user/%s/domain/whitelisted/%d" % (request.username, i)
                    if var in ucr:
                        vunset_now.append(var)
                        i += 1
                    else:
                        break
                vset["proxy/filter/room/%s/rule" % self._computerroom.room] = request.username
                vset["proxy/filter/setting-user/%s/filtertype" % request.username] = "whitelist-block"
                i = 1
                for domain in (customRule or "").split("\n"):
                    MODULE.info("Setting whitelist entry for domain %s" % domain)
                    if not domain:
                        continue
                    parsed = urlsplit(domain)
                    MODULE.info("Setting whitelist entry for domain %s" % str(parsed))
                    if parsed.netloc:
                        vset[
                            "proxy/filter/setting-user/%s/domain/whitelisted/%d" % (request.username, i)
                        ] = parsed.netloc
                        i += 1
                    elif parsed.path:
                        vset[
                            "proxy/filter/setting-user/%s/domain/whitelisted/%d" % (request.username, i)
                        ] = parsed.path
                        i += 1
            else:
                vset["proxy/filter/room/%s/rule" % self._computerroom.room] = internetRule
        else:
            vunset_now.append("proxy/filter/room/%s/ip" % self._computerroom.room)
            vunset_now.append("proxy/filter/room/%s/rule" % self._computerroom.room)
        # write configuration
        # remove old values
        handler_unset(vunset_now)

        # append values
        ucr.load()
        MODULE.info("Merging UCR variables")
        for key, value in vappend.items():
            if ucr.get(key):
                old = set(ucr[key].split(" "))
                MODULE.info("Old value: %s" % old)
            else:
                old = set()
                MODULE.info("Old value empty")
            new = set(value)
            MODULE.info("New value: %s" % new)
            new = old.union(new)
            MODULE.info("Merged value of %s: %s" % (key, new))
            if new:
                vset[key] = " ".join(new)

        # Workaround for bug 30450:
        # if samba/printmode/hosts/none is not set but samba/printmode/hosts/all then all other hosts
        # are unable to print on samba shares. Solution: set empty value for .../none if no host is on
        # deny list.
        varname = "samba/printmode/hosts/none"
        if varname not in vset:
            ucr.load()
            if not ucr.get(varname):
                vset[varname] = '""'
        else:
            # remove empty items ('""') in list
            vset[varname] = " ".join(x for x in vset[varname].split(" ") if x != '""')

        # set values
        ucr_vars = sorted("%s=%s" % x for x in vset.items())
        MODULE.info("Writing room rules: %s" % "\n".join(ucr_vars))
        handler_set(ucr_vars)

        # create at job to remove settings
        cmd = "/usr/share/ucs-school-umc-computerroom/ucs-school-deactivate-rules --room %s" % (
            quote(self._computerroom.roomDN)
        )
        MODULE.info("command for reinitialization is: %s" % (cmd,))

        if not in_exam_mode:
            starttime = datetime.datetime.now()
            MODULE.info("Now: %s" % starttime)
            MODULE.info("Endtime: %s" % period)
            starttime = starttime.replace(
                hour=period.hour, minute=period.minute, second=0, microsecond=0
            )
            while starttime < datetime.datetime.now():  # prevent problems due to intra-day limit
                starttime += datetime.timedelta(days=1)

            # AT job for the normal case
            MODULE.info("Remove settings at %s" % (starttime,))
            atjob_id = atjobs.add(cmd, starttime, {Instance.ATJOB_KEY: self._computerroom.room}).nr
            _updateRoomInfo(self._computerroom.roomDN, atjobID=atjob_id)
            self._ruleEndAt = starttime

        self.reset_smb_connections()
        self.reload_cups()

    def reload_cups(self):
        if not subprocess.call(  # nosec
            ["/bin/systemctl", "is-enabled", "--quiet", "cups.service"],
            stdout=open("/dev/null", "w"),
            stderr=subprocess.STDOUT,
        ):
            MODULE.info("Reloading cups")
            if subprocess.call(["/bin/systemctl", "reload", "cups.service"]) != 0:  # nosec
                MODULE.error("Failed to reload cups! Printer settings not applied.")

    def reset_smb_connections(self):
        smbstatus = SMB_Status()
        veyon_users = [x.lower() for x in self._computerroom.users if x]
        MODULE.info("veyon users: %s" % ", ".join(veyon_users))
        for process in smbstatus:
            MODULE.info("SMB process: %s" % str(process))
            if process.username and process.username.lower() in veyon_users:
                MODULE.info("Kill SMB process %s" % process.pid)
                try:
                    os.kill(int(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    # Bug 56904
                    # It is possible (though rare) that an smb process is stopped
                    # between the `smbstatus` call and the os.kill, resulting in a ProcessLookupError
                    MODULE.info(
                        "Tried to kill SMB process with pid %s, but process does not exist anymore."
                        % (process.pid)
                    )
                except Exception:
                    MODULE.error("Unable to kill SMB process %s." % (process.pid))
                    MODULE.error(traceback.format_exc())

    @sanitize(server=StringSanitizer(required=True))
    @check_room_access
    def demo_start(self, request):
        """Starts a presentation mode"""
        self._computerroom.startDemo(request.options["server"], True)
        self.finished(request.id, True)

    @check_room_access
    def demo_stop(self, request):
        """Stops a presentation mode"""
        self._computerroom.stopDemo()
        self.finished(request.id, True)

    @sanitize(
        state=ChoicesSanitizer(["poweroff", "poweron", "restart"]),
        computer=ComputerSanitizer(required=True),
    )
    @check_room_access
    @simple_response
    def computer_state(self, computer, state):
        """Stops, starts or restarts a computer"""
        if state == "poweroff":
            computer.powerOff()
        elif state == "poweron":
            computer.powerOn()
        elif state == "restart":
            computer.restart()
        return True

    @check_room_access
    @sanitize(computer=ComputerSanitizer(required=True))
    @simple_response
    def user_logout(self, computer):
        """Log out the user at the given computer"""
        computer.logOut()
        return True

    @simple_response
    def plugins_load(self):
        plugins = {"buttons": []}
        for plugin in self._plugins.values():
            plugins["buttons"].append(plugin.button())
        return plugins

    @check_room_access
    @sanitize(plugin=StringSanitizer(required=True), computer=StringSanitizer(required=True))
    def plugins_execute(self, request):
        plugin = self._plugins.get(request.options["plugin"])
        if not plugin:
            raise UMC_Error(_("Plugin not found."))
        result = plugin.execute(request.options["computer"])
        self.finished(request.id, result)
