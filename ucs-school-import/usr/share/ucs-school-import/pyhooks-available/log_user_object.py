# Copyright 2020-2021 Univention GmbH
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

try:
    from typing import Any, List, Tuple

    from ucsschool.importer.models.import_user import ImportUser
except ImportError:
    pass
from ucsschool.importer.utils.user_pyhook import UserPyHook

#
# Define the user attributes and UDM properties that shuold be logged (and
# their order) here. The user type and the DN (and old_dn if different from dn)
# is always logged.
#
PROPS = (
    "name",
    "school",
    "schools",
    "record_uid",
    "source_uid",
    # "firstname",
    # "lastname",
    # "disabled",
    "school_classes",
    "ucsschool_roles",
    # "birthday",
    "udm_properties",
    "primaryGroup",
    "groups",
    # "ucsschoolPurgeTimestamp",
    # "uidNumber",
    # "unixhome",
)

# The loglevel at which to write the message. Must be one of "DEBUG", "INFO",
# "WARNING", "ERROR" or "CRITICAL".
# This is only relevant for the command line, as the logfile always logs
# at DEBUG level.
LOG_LEVEL = "DEBUG"


class LogUserObject(UserPyHook):
    priority = {
        "pre_create": None,
        "post_create": -1000,  # -1000: last hook to run
        "pre_modify": 1000,  # +1000: first hook to run
        "post_modify": -1000,
        "pre_move": 1000,
        "post_move": -1000,
        "pre_remove": 1000,
        "post_remove": None,
    }

    def __init__(self, *args, **kwargs):
        super(LogUserObject, self).__init__(*args, **kwargs)
        try:
            self._log = getattr(self.logger, LOG_LEVEL.lower())
        except AttributeError:
            raise ValueError("Unkown log level {!r}.".format(LOG_LEVEL))

    def log_user_attrs(self, user, prefix):  # type: (ImportUser, str) -> None
        props_and_values = self.get_props_and_values(user)
        attrs = ["{}: {!r}".format(prop, value) for prop, value in props_and_values]
        old_dn_str = ", old_dn={!r}".format(user.old_dn) if user.old_dn != user.dn else ""
        self._log(
            "%s%s(dn=%r%s):\n    %s",
            prefix,
            user.__class__.__name__,
            user.dn,
            old_dn_str,
            "\n    ".join(attrs),
        )

    def get_props_and_values(self, user):  # type: (ImportUser) -> List[Tuple[str, Any]]
        udm_obj = None
        res = []
        for prop in PROPS:
            if prop in user._attributes or prop == "udm_properties":
                res.append((prop, getattr(user, prop)))
                if prop == "schools" and user.old_dn != user.dn:
                    try:
                        ldap_schools = self.lo.get(user.old_dn, attr=["ucsschoolSchool"])[
                            "ucsschoolSchool"
                        ]
                        res.append(("schools (LDAP)", ldap_schools))
                    except KeyError:
                        self.logger.error(
                            "User with DN %r does not exist or has empty 'ucsschoolSchool' attribute!",
                            user.old_dn,
                        )
                        filter_s = self.lo.explodeDn(user.old_dn)[0]
                        dns = self.lo.searchDn(filter_s)
                        self.logger.error("Searching LDAP with filter %r got: %r", filter_s, dns)
            else:
                if not udm_obj:
                    udm_obj = user.get_udm_object(self.lo)
                res.append((prop, udm_obj[prop]))
        return res

    def pre_create(self, user):
        self.log_user_attrs(user, "PRE_CREATE: ")

    def post_create(self, user):
        self.log_user_attrs(user, "POST_CREATE: ")

    def pre_modify(self, user):
        self.log_user_attrs(user, "PRE_MODIFY: ")

    def post_modify(self, user):
        self.log_user_attrs(user, "POST_MODIFY: ")

    def pre_move(self, user):
        self.log_user_attrs(user, "PRE_MOVE: ")

    def post_move(self, user):
        self.log_user_attrs(user, "POST_MOVE: ")

    def pre_remove(self, user):
        self.log_user_attrs(user, "PRE_REMOVE: ")

    def post_remove(self, user):
        self.log_user_attrs(user, "POST_REMOVE: ")
