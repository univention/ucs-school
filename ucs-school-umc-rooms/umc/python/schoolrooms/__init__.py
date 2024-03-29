#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Manage room and their associated computers
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

from typing import TYPE_CHECKING, List  # noqa: F401

import univention.admin.uexceptions as udm_exceptions
from ucsschool.lib.models.computer import SchoolComputer
from ucsschool.lib.models.group import ComputerRoom
from ucsschool.lib.models.utils import add_module_logger_to_schoollib
from ucsschool.lib.school_umc_base import LDAP_Filter, SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import USER_READ, USER_WRITE, LDAP_Connection
from univention.lib.i18n import Translation
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import (
    DictSanitizer,
    DNSanitizer,
    LDAPSearchSanitizer,
    ListSanitizer,
)

if TYPE_CHECKING:
    import univention.admin.uldap.access  # noqa: F401


_ = Translation("ucs-school-umc-rooms").translate


class Instance(SchoolBaseModule):
    def init(self):
        super(Instance, self).init()
        add_module_logger_to_schoollib()

    @sanitize(
        school=SchoolSanitizer(required=True),
        pattern=LDAPSearchSanitizer(required=False, default="", use_asterisks=True, add_asterisks=False),
    )
    @LDAP_Connection()
    def computers(self, request, ldap_user_read=None):
        pattern = LDAP_Filter.forComputers(request.options.get("pattern", ""))
        result = [
            {"label": x.name, "id": x.dn, "teacher_computer": x.teacher_computer}
            for x in SchoolComputer.get_all(ldap_user_read, request.options["school"], pattern)
        ]
        result = sorted(result, key=lambda x: x["label"])  # TODO: still necessary?

        self.finished(request.id, result)

    @sanitize(
        school=SchoolSanitizer(required=True),
        pattern=LDAPSearchSanitizer(required=False, default="", use_asterisks=True, add_asterisks=False),
    )
    @LDAP_Connection()
    def query(self, request, ldap_user_read=None):
        school = request.options["school"]
        pattern = LDAP_Filter.forGroups(
            request.options.get("pattern", ""), school, _escape_filter_chars=False, school_prefix=school
        )
        result = [
            {"name": x.get_relative_name(), "description": x.description or "", "$dn$": x.dn}
            for x in ComputerRoom.get_all(ldap_user_read, school, pattern)
        ]
        result = sorted(result, key=lambda x: x["name"])  # TODO: still necessary?

        self.finished(request.id, result)

    @sanitize(DNSanitizer(required=True))
    @LDAP_Connection()
    def get(self, request, ldap_user_read=None):
        # open the specified room
        room = ComputerRoom.from_dn(request.options[0], None, ldap_user_read)
        result = room.to_dict()
        result["computers"] = result.get("hosts")
        result["teacher_computers"] = []
        for host_dn in result.get("hosts"):
            host = SchoolComputer.from_dn(host_dn, None, ldap_user_read)  # Please remove with Bug #49611
            host = SchoolComputer.from_dn(host_dn, None, ldap_user_read)
            if host.teacher_computer:
                result["teacher_computers"].append(host_dn)
        self.finished(request.id, [result])

    @sanitize(DictSanitizer({"object": DictSanitizer({}, required=True)}))
    @LDAP_Connection(USER_READ, USER_WRITE)
    def add(self, request, ldap_user_write=None, ldap_user_read=None):
        """Adds a new room"""
        group_props = request.options[0].get("object", {})
        group_props["hosts"] = group_props.get("computers")
        room = ComputerRoom(**group_props)
        if room.get_relative_name() == room.name:
            room.name = "%(school)s-%(name)s" % group_props
            room.set_dn(room.dn)
        success = room.create(ldap_user_write)
        self._set_teacher_computers(
            group_props.get("computers", []),
            group_props.get("teacher_computers", []),
            ldap_user_read,
            ldap_user_write,
        )
        self.finished(request.id, [success])

    @sanitize(DictSanitizer({"object": DictSanitizer({}, required=True)}))
    @LDAP_Connection(USER_READ, USER_WRITE)
    def put(self, request, ldap_user_write=None, ldap_user_read=None):
        """Modify an existing room"""
        group_props = request.options[0].get("object", {})
        group_props["hosts"] = group_props.get("computers")

        room = ComputerRoom(**group_props)
        # Since we do not have any option on UCS@school 5.0 in the frontend,
        # we need to retrieve the role from ldap.
        room.veyon_backend = ComputerRoom.from_dn(
            lo=ldap_user_read, dn=group_props["$dn$"], school=group_props["school"]
        ).veyon_backend
        if room.get_relative_name() == room.name:
            room.name = "%(school)s-%(name)s" % group_props
        room.set_dn(group_props["$dn$"])
        room.modify(ldap_user_write)
        self._set_teacher_computers(
            group_props.get("computers", []),
            group_props.get("teacher_computers", []),
            ldap_user_read,
            ldap_user_write,
        )
        self.finished(request.id, [True])

    @sanitize(DictSanitizer({"object": ListSanitizer(DNSanitizer(required=True), min_elements=1)}))
    @LDAP_Connection(USER_READ, USER_WRITE)
    def remove(self, request, ldap_user_write=None, ldap_user_read=None):
        """Deletes a room"""
        try:
            room_dn = request.options[0]["object"][0]
            room = ComputerRoom.from_dn(room_dn, None, ldap_user_write)
            room.remove(ldap_user_write)
        except udm_exceptions.base as e:
            self.finished(request.id, [{"success": False, "message": str(e)}])
            return

        self.finished(request.id, [{"success": True}])

    @staticmethod
    def _set_teacher_computers(
        all_computers,  # type: List[str]
        teacher_computers,  # type: List[str]
        ldap_user_read,  # type: univention.admin.uldap.access
        ldap_user_write,  # type: univention.admin.uldap.access
    ):  # type (...) -> None
        """
        All computers in teacher_computers become teacher computers.
        All computers that are in all_computers, but not in teacher_computers become non teacher
        computers.

        :param all_computers: All computers present in a room
        :param teacher_computers: All computers in the room designated to become teacher computers
        :param ldap_user_read: ldap bind with read access
        :param ldap_user_write: ldap bind with write access
        """
        # Make teacher computers
        for computer_dn in teacher_computers:
            try:
                # Please remove one call with Bug #49611:
                computer = SchoolComputer.from_dn(computer_dn, None, ldap_user_write)
                computer = SchoolComputer.from_dn(computer_dn, None, ldap_user_write)
                computer.teacher_computer = True
                computer.modify(ldap_user_write)
            except udm_exceptions.noObject:
                pass
        # Remove teacher computer on deselected
        non_teacher_computer = set(all_computers).difference(teacher_computers)
        for computer_dn in non_teacher_computer:
            try:
                # Please remove one call with Bug #49611:
                computer = SchoolComputer.from_dn(computer_dn, None, ldap_user_write)
                computer = SchoolComputer.from_dn(computer_dn, None, ldap_user_write)
                computer.teacher_computer = False
                computer.modify(ldap_user_write)
            except udm_exceptions.noObject:
                pass
