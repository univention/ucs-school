#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: selective-udm
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

import base64

import ldap.filter

import univention.admin.handlers.computers.windows
import univention.admin.modules
import univention.admin.uexceptions
from ucsschool.lib.school_umc_base import SchoolBaseModule
from ucsschool.lib.school_umc_ldap_connection import ADMIN_WRITE, USER_READ, LDAP_Connection
from univention.lib.i18n import Translation
from univention.management.console.base import UMC_Error
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import StringSanitizer

_ = Translation("univention-management-console-selective-udm").translate


class Instance(SchoolBaseModule):
    def init(self):
        super(Instance, self).init()
        univention.admin.modules.update()

        # update choices-lists which are defined in LDAP
        univention.admin.syntax.update_choices()

    def _check_usersid_join_permissions(self, lo, usersid):
        allowed_groups = ucr.get("ucsschool/windows/join/groups", "Domain Admins").split(",")

        result = lo.searchDn(ldap.filter.filter_format("sambaSID=%s", [usersid]))
        if not result:
            raise UMC_Error("SID %s was not found." % (usersid,))

        user_dn = result[0]
        MODULE.info("Found user with DN %s" % (user_dn,))

        result = lo.search(ldap.filter.filter_format("uniqueMember=%s", [user_dn]), attr=["cn"])
        if not result:
            raise UMC_Error("No group memberships for SID %s found." % (usersid,))

        for _dn, attr in result:
            if attr["cn"][0].decode("UTF-8") in allowed_groups:
                return

        raise UMC_Error(
            "SID %s is not member of one of the following groups: %s. The allowed groups can be "
            "modified by setting the UCR variable ucsschool/windows/join/groups."
            % (usersid, allowed_groups)
        )

    @sanitize(name=StringSanitizer(required=True))
    @LDAP_Connection(USER_READ, ADMIN_WRITE)
    def create_windows_computer(
        self, request, ldap_user_read=None, ldap_admin_write=None, ldap_position=None, search_base=None
    ):
        if not search_base.school:
            raise UMC_Error(_("Could not determine schoolOU."))

        # Set new position
        ldap_position.setDn(search_base.computers)

        self._check_usersid_join_permissions(ldap_user_read, request.options.get("usersid"))

        # TODO: univention.admin.modules.init()
        # Create the computer account
        windows = univention.admin.modules.get("computers/windows")
        computer = windows.object(None, ldap_admin_write, position=ldap_position, superordinate=None)
        computer.open()
        name = request.options.get("name")
        if name.endswith("$"):
            # Samba 3 calls the name in this way
            name = name[:-1]

        # In Samba 3 the samba attributes must be set by Samba itself
        samba3_mode = request.options.get("samba3_mode")
        if samba3_mode and samba3_mode.lower() in ["true", "yes"]:
            computer.options.remove("samba")
            computer.options.remove("kerberos")

        computer["name"] = name

        password = request.options.get("password")
        if password:
            decode_password = request.options.get("decode_password")
            if decode_password and decode_password.lower() in ["true", "yes"]:
                # the password is base64 encoded
                password = base64.b64decode(password.encode("ASCII"))
                # decode from utf-16le
                password = password.decode("utf-16le")
                # and remove the quotes
                password = password.strip('"')
            computer["password"] = password

        computer["description"] = request.options.get("description")
        try:
            computer_dn = computer.create()
            already_exists = False
        except univention.admin.uexceptions.objectExists as exc:
            already_exists = True
            computer_dn = exc.args[0]
        self.finished(request.id, {"dn": computer_dn, "already_exists": already_exists})
