#!/usr/bin/python3
#
# Univention Management Console
#  module: school accounts Module
#
# Copyright 2007-2024 Univention GmbH
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

from calendar import timegm
from functools import lru_cache
from math import ceil
from time import strptime, time

import univention.admin.uexceptions as udm_exceptions
from ucsschool.lib.models.user import User
from ucsschool.lib.school_umc_base import Display, SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import USER_WRITE, LDAP_Connection
from univention.admin.handlers.users.user import unmapPasswordExpiry
from univention.config_registry import ucr
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import (
    BooleanSanitizer,
    LDAPSearchSanitizer,
    StringSanitizer,
)
from univention.udm import UDM

_ = Translation("ucs-school-umc-schoolusers").translate


@lru_cache(maxsize=1)
def get_udm_user_mod():
    return UDM.admin().version(2).get("users/user")


def get_user_from_request(user_dn, access, as_udm_object=False):
    user = User.from_dn(user_dn, None, access)
    return user.get_udm_object(access) if as_udm_object else user


@lru_cache(maxsize=None)
def get_extended_attributes():
    EXT_ATTR_MOD = UDM.admin().version(2).get("settings/extended_attribute")
    return [
        (attribute.props.CLIName, attribute.props.default)
        for attribute in EXT_ATTR_MOD.search(
            filter_s="(univentionUDMPropertyModule=users/user)",
            base="cn=custom attributes,cn=univention,%s" % ucr.get("ldap/base"),
        )
    ]


def get_exception_msg(exc):  # TODO: str(exc) would be nicer, Bug #27940, 30089, 30088
    msg = getattr(exc, "message", "")
    for arg in exc.args:
        if str(arg) not in msg:
            msg = "%s %s" % (msg, arg)
    return msg


def udm_admin_save_user_with_extended_attributes(dn):
    user = get_udm_user_mod().get(dn)
    try:
        for (name, default_value) in get_extended_attributes():
            if not hasattr(user.props, name):
                setattr(user.props, name, default_value)
        user.save()
    except udm_exceptions.base as exc:
        raise UMC_Error("%s" % (get_exception_msg(exc)))


class Instance(SchoolBaseModule):
    @sanitize(
        **{
            "school": SchoolSanitizer(required=True),
            "class": StringSanitizer(required=True),  # allow_none=True
            "pattern": LDAPSearchSanitizer(
                required=True, default="", use_asterisks=True, add_asterisks=True
            ),
        }
    )
    @LDAP_Connection()
    def query(self, request, ldap_user_read=None, ldap_position=None):
        """Searches for students"""
        klass = request.options.get("class")
        if klass in (None, "None"):
            klass = None
        result = []
        # Bug 50231 prevent crashing
        for entry in self._users_ldap_no_exc(
            ldap_user_read,
            request.options["school"],
            group=klass,
            user_type=request.flavor,
            pattern=request.options.get("pattern", ""),
            attr=["givenName", "sn", "shadowLastChange", "shadowMax", "uid"],
        ):
            dn = entry["dn"]
            attrs = entry["attrs"]
            # internally skipping the passed exception
            if not isinstance(attrs, udm_exceptions.noObject):
                result.append(
                    {
                        "id": dn,
                        "name": Display.user_ldap(attrs),
                        "passwordexpiry": self.passwordexpiry_to_days(unmapPasswordExpiry(attrs)),
                    }
                )

        self.finished(request.id, result)

    @sanitize(
        userDN=StringSanitizer(required=True),
        newPassword=StringSanitizer(required=True, minimum=1),
        nextLogin=BooleanSanitizer(default=True),
    )
    @LDAP_Connection(USER_WRITE)
    def password_reset(self, request, ldap_user_write=None):
        """Reset the password of the user"""

        def _password_reset(request, ldap_user_write=None):
            userdn = request.options["userDN"]
            pwdChangeNextLogin = request.options["nextLogin"]
            newPassword = request.options["newPassword"]

            user = get_user_from_request(userdn, ldap_user_write, as_udm_object=True)
            user["password"] = newPassword
            user["overridePWHistory"] = "1"
            # Bug #46175: reset locked state, do not set disabled=0 since this would enable the whole
            # user account:
            user["locked"] = "0"
            # workaround bug #46067 (start)
            user.modify()
            user = get_user_from_request(userdn, ldap_user_write, as_udm_object=True)
            # workaround bug #46067 (end)
            user["pwdChangeNextLogin"] = "1" if pwdChangeNextLogin else "0"
            user.modify()

        try:
            _password_reset(request, ldap_user_write)
            self.finished(request.id, True)
            #  This is needed here to properly finish the request without continuation if everyting
            #  worked well.
            return
        except:  # noqa: F841, E722
            udm_admin_save_user_with_extended_attributes(request.options["userDN"])

        try:
            _password_reset(request, ldap_user_write)
            self.finished(request.id, True)
        except udm_exceptions.permissionDenied as exc:
            MODULE.process("dn=%r" % (request.options["userDN"],))
            MODULE.process("exception=%s" % (type(exc),))
            raise UMC_Error(_("permission denied"))
        except udm_exceptions.base as exc:
            MODULE.process("dn=%r" % (request.options["userDN"],))
            MODULE.process("exception=%s" % (exc,))
            raise UMC_Error("%s" % (get_exception_msg(exc)))

    def passwordexpiry_to_days(self, timestr):
        """
        Calculates the number of days from now to the password expiration date.

        The result is always rounded up to the full day.
        The time function used here are all based on Epoch(UTC). Since we are not interested in a
        specific date and only in a time difference the actual timezone is neglectable.

        :param timestr: The string representation of the expiration date, e.g. 2018-05-30 or None
        :type timestr: str
        :return: -1 if no expiration day is set, 0 if already expired, >0 otherwise
        :rtype: int
        """
        if not timestr:
            return -1
        current_timestamp = time()
        expires_timestamp = timegm(strptime(timestr, "%Y-%m-%d"))
        time_difference = expires_timestamp - current_timestamp
        if time_difference <= 0:
            return 0
        return int(ceil(time_difference / 86400))  # Bug #42212: passwordexpiry max resolution is day
        # So we always round up towards the day the password will be expired
