#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib
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

import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple  # noqa: F401

from ldap.filter import escape_filter_chars, filter_format

import univention.admin.modules as udm_modules
from univention.admin.filter import conjunction, parse
from univention.admin.uexceptions import noObject
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import Base, UMC_Error
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import StringSanitizer

from .school_umc_ldap_connection import LDAP_Connection, set_bind_function

if TYPE_CHECKING:
    from univention.admin.handlers import simpleLdap as UdmObject  # noqa: F401
    from univention.admin.uldap import access as LoType  # noqa: F401

# load UDM modules
udm_modules.update()

__bind_callback = None

_ = Translation("python-ucs-school").translate


class SchoolSanitizer(StringSanitizer):
    def _sanitize(self, value, name, further_args):
        value = super(SchoolSanitizer, self)._sanitize(value, name, further_args)

        if not value and self.required:
            raise UMC_Error(
                _(
                    "The request did not specify any school. You have to create a school before "
                    'continuing. Use the "Schools" UMC module to create one.'
                ),
                status=503,
                result={"no_school_found": True},
            )
        return value


class SchoolBaseModule(Base):
    """
    This class serves as base class for UCS@school UMC modules that need
    LDAP access. It initiates the list of available OUs (self.availableSchools) and
    initiates the search bases (self.searchBase). set_bind_function() is called
    automatically to allow LDAP connections. In order to integrate this class
    into a module, use the following paradigm:

    class Instance(SchoolBaseModule):
        def __init__(self):
            # initiate list of internal variables
            SchoolBaseModule.__init__(self)
            # ... custom code

        def init(self):
            SchoolBaseModule.init(self)
            # ... custom code
    """

    def prepare(self, request):
        def bind_user_connection(lo):  # type: (LoType) -> None
            if not request.user_dn:  # ... backwards compatibility
                # the DN is None if we have a local user (e.g., root)
                # FIXME: above statement is not completely true, user_dn is also None if the UMC server +
                # could not detect it (for whatever reason) therefore this workaround is a security hole
                # which allows to execute ldap operations as machine account
                try:  # to get machine account password
                    MODULE.warn("Using machine account for local user: %s" % request.username)
                    with open("/etc/machine.secret") as fd:
                        password = fd.read().strip()
                    user_dn = ucr.get("ldap/hostdn")
                except IOError as exc:
                    password = None
                    user_dn = None
                    MODULE.warn("Cannot read /etc/machine.secret: %s" % (exc,))
                lo.lo.bind(user_dn, password)
                return
            request.bind_user_connection(lo)

        set_bind_function(bind_user_connection)
        super(SchoolBaseModule, self).prepare(request)

    @LDAP_Connection()
    def schools(self, request, ldap_user_read=None):
        """Returns a list of all available school"""
        from ucsschool.lib.models.school import School

        schools = School.from_binddn(ldap_user_read)
        if not schools:
            raise UMC_Error(
                _(
                    "Could not find any school. You have to create a school before continuing. Use the "
                    '"Schools" UMC module to create one.'
                ),
                status=503,
                result={"no_school_found": True},
            )
        self.finished(
            request.id, [{"id": school.name, "label": school.display_name} for school in schools]
        )

    def _groups(self, ldap_connection, school, ldap_base, pattern=None, scope="sub"):
        # type: (LoType, str, str, Optional[str], Optional[str]) -> List[Dict[str, str]]
        """Returns a list of all groups of the given school"""
        # get list of all users matching the given pattern
        ldapFilter = None
        if pattern:
            ldapFilter = LDAP_Filter.forGroups(pattern)
        groupresult = udm_modules.lookup(
            "groups/group", None, ldap_connection, scope=scope, base=ldap_base, filter=ldapFilter
        )
        name_pattern = re.compile(r"^%s-" % (re.escape(school)), flags=re.I)
        return [{"id": grp.dn, "label": name_pattern.sub("", grp["name"])} for grp in groupresult]

    @sanitize(school=SchoolSanitizer(required=True), pattern=StringSanitizer(default=""))
    @LDAP_Connection()
    def classes(self, request, ldap_user_read=None):
        """Returns a list of all classes of the given school"""
        school = request.options["school"]
        from ucsschool.lib.models.group import SchoolClass

        self.finished(
            request.id,
            self._groups(
                ldap_user_read, school, SchoolClass.get_container(school), request.options["pattern"]
            ),
        )

    @sanitize(school=SchoolSanitizer(required=True), pattern=StringSanitizer(default=""))
    @LDAP_Connection()
    def workgroups(self, request, ldap_user_read=None):
        """Returns a list of all working groups of the given school"""
        school = request.options["school"]
        from ucsschool.lib.models.group import WorkGroup

        self.finished(
            request.id,
            self._groups(
                ldap_user_read,
                school,
                WorkGroup.get_container(school),
                request.options["pattern"],
                "one",
            ),
        )

    @sanitize(school=SchoolSanitizer(required=True), pattern=StringSanitizer(default=""))
    @LDAP_Connection()
    def groups(self, request, ldap_user_read=None):
        """Returns a list of all groups (classes and workgroups) of the given school"""
        # use as base the path for 'workgroups', as it incorporates workgroups and classes
        # when searching with scope 'sub'
        school = request.options["school"]
        from ucsschool.lib.models.group import WorkGroup

        self.finished(
            request.id,
            self._groups(
                ldap_user_read, school, WorkGroup.get_container(school), request.options["pattern"]
            ),
        )

    @sanitize(school=SchoolSanitizer(required=True), pattern=StringSanitizer(default=""))
    @LDAP_Connection()
    def rooms(self, request, ldap_user_read=None):
        """Returns a list of all available school"""
        school = request.options["school"]
        from ucsschool.lib.models.group import ComputerRoom

        self.finished(
            request.id,
            self._groups(
                ldap_user_read, school, ComputerRoom.get_container(school), request.options["pattern"]
            ),
        )

    def _users(self, ldap_connection, school, group=None, user_type=None, pattern=""):
        # type: (LoType, str, Optional[str], Optional[str], Optional[str]) -> List[ucsschool.lib.models.User]  # noqa: E501
        """Returns a list of all users given 'pattern', 'school' (search base) and 'group'"""
        import ucsschool.lib.models

        if not user_type:
            classes = [ucsschool.lib.models.User]
        elif user_type.lower() in ("teachers", "teacher"):
            classes = [ucsschool.lib.models.Teacher, ucsschool.lib.models.TeachersAndStaff]
        elif user_type.lower() in ("student", "students", "pupil", "pupils"):
            classes = [ucsschool.lib.models.Student]
        else:
            raise TypeError("user_type %r unknown." % (user_type,))

        # open the group
        groupObj = None
        if group not in (None, "None"):
            groupModule = udm_modules.get("groups/group")
            groupObj = groupModule.object(None, ldap_connection, None, group)
            groupObj.open()

            # lazy loading of exception classes to prevent import loop
            from ucsschool.lib.models.base import UnknownModel, WrongModel

            # The following code block prevents a massive performance loss if the group
            # contains far less users than all available users. The else-block opens
            # all available users ==> high LDAP load! (Bug #42167)
            users = []
            for userdn in set(groupObj["users"]):
                search_filter_list = [LDAP_Filter.forSchool(school)]
                if pattern:
                    search_filter_list.append(LDAP_Filter.forUsers(pattern))
                # concatenate LDAP filters
                search_filter = u"{}".format(
                    conjunction("&", [parse(subfilter) for subfilter in search_filter_list])
                )
                for cls in classes:
                    try:
                        udm_obj = cls.get_only_udm_obj(ldap_connection, search_filter, base=userdn)
                    except noObject:
                        MODULE.error(
                            "Possible group inconsistency detected: %r contains member %r but member "
                            "was not found in LDAP" % (group, userdn)
                        )
                        udm_obj = None

                    if udm_obj is not None:
                        # make sure that the found UDM object is of requested user type
                        try:
                            cls.from_udm_obj(udm_obj, school, ldap_connection)
                        except (UnknownModel, WrongModel):
                            continue

                        users.append(udm_obj)
        else:
            # be aware that this search opens all user objects of specified type and may take some time!
            users = []
            for cls in classes:
                _users = cls.get_all(ldap_connection, school, LDAP_Filter.forUsers(pattern))
                users.extend(user.get_udm_object(ldap_connection) for user in _users)
        return users

    def _users_ldap(self, ldap_connection, school, group=None, user_type=None, pattern="", attr=None):
        # type: (LoType, str, Optional[str], Optional[str], Optional[str], Optional[str]) -> List[Tuple[str, Dict[str, Any]]]  # noqa: E501
        """
        Returns a list of LDAP query result tuples (dn, attr) of all users
        given  `pattern`, `school` (search base) and `group`.
        """
        users = []
        # Bug #50231 prevent crashing
        # Restore original behavior
        for entry in self._users_ldap_no_exc(ldap_connection, school, group, user_type, pattern, attr):
            userdn = entry["dn"]
            attrs = entry["attrs"]
            if isinstance(attrs, noObject):
                raise noObject(
                    "User with DN: {} was not found in the group {}."
                    " Please make sure it is a valid UCS@school user and is member of all "
                    "necessary groups. For more information visit https://help.univention.com"
                    "/t/how-an-ucs-school-user-should-look-like/15630".format(userdn, group)
                )
            else:
                users.append((userdn, attrs))
        return users

    def _users_ldap_no_exc(
        self, ldap_connection, school, group=None, user_type=None, pattern="", attr=None
    ):
        # type: (LoType, str, Optional[str], Optional[str], Optional[str], Optional[str]) -> List[Dict[str,any]|any]  # noqa: E501
        """
        Returns a list of LDAP query result tuples (dn, attr) of all users
        given  `pattern`, `school` (search base) and `group`.
        """
        import ucsschool.lib.models

        if not user_type:
            classes = [ucsschool.lib.models.User]
        elif user_type.lower() in ("teachers", "teacher"):
            classes = [ucsschool.lib.models.Teacher, ucsschool.lib.models.TeachersAndStaff]
        elif user_type.lower() in ("student", "students", "pupil", "pupils"):
            classes = [ucsschool.lib.models.Student]
        elif user_type.lower() in ("staff",):
            classes = [ucsschool.lib.models.Staff, ucsschool.lib.models.TeachersAndStaff]
        else:
            raise TypeError("user_type %r unknown." % (user_type,))

        attr = attr or []
        users = []
        user_module = udm_modules.get("users/user")
        if group not in (None, "None"):
            # The following code block prevents a massive performance loss if the group
            # contains far less users than all available users. The else-block opens
            # all available users ==> high LDAP load! (Bug #42167)

            user_dns = [
                member.decode("utf-8") for member in ldap_connection.get(group).get("uniqueMember", [])
            ]

            for userdn in set(user_dns):
                search_filter_list = [LDAP_Filter.forSchool(school)]
                if pattern:
                    search_filter_list.append(LDAP_Filter.forUsers(pattern, False))
                for cls in classes:
                    search_filter_list.append(cls.type_filter)
                    # concatenate LDAP filters
                    search_filter = u"{}".format(
                        user_module.lookup_filter(
                            conjunction("&", [parse(subfilter) for subfilter in search_filter_list])
                        )
                    )

                    try:
                        ldap_objs = ldap_connection.search(search_filter, base=userdn, attr=attr)
                    except noObject:
                        # Bug #50231 prevent crashing
                        ldap_objs = [
                            (
                                userdn,
                                noObject(
                                    "User with DN: {} was not found in the group {}."
                                    " Please make sure it is a valid UCS@school user"
                                    " and is member of all "
                                    "necessary groups. For more information visit https://help.univention.com"
                                    "/t/how-an-ucs-school-user-should-look-like/15630".format(
                                        userdn, group
                                    )
                                ),
                            )
                        ]
                    if len(ldap_objs) == 1:
                        users.append({"dn": ldap_objs[0][0], "attrs": ldap_objs[0][1]})
                    # else:
                    # either: 'Possible group inconsistency detected: %r contains member %r but member
                    # was not found in LDAP' % (group, userdn))
                    # or: DN does not belong to teacher/student (WrongModel)
                    # in both cases: ignore user
        else:
            for cls in classes:
                filter_s = u"{}".format(
                    user_module.lookup_filter(
                        conjunction(
                            "&",
                            [
                                parse(LDAP_Filter.forSchool(school)),
                                parse(LDAP_Filter.forUsers(pattern, False)),
                                parse(cls.type_filter),
                            ],
                        )
                    )
                )
                # Bug #50231 prevent crashing
                # previous list extend needs to be reformatted
                for dn, _attr in ldap_connection.search(filter=filter_s, attr=attr):
                    users.append({"dn": dn, "attrs": _attr})
        return users


class LDAP_Filter:
    @staticmethod
    def forSchool(school):  # type: (str) -> str
        return filter_format("(ucsschoolSchool=%s)", [school])

    @staticmethod
    def forUsers(pattern, _escape_filter_chars=True):  # type: (str, Optional[bool]) -> str
        return LDAP_Filter.forAll(
            pattern, ["lastname", "username", "firstname"], _escape_filter_chars=_escape_filter_chars
        )

    @staticmethod
    def forGroups(
        pattern, school=None, _escape_filter_chars=True, school_prefix=""
    ):  # type: (str, Optional[str], Optional[bool], Optional[str]) -> str
        # school parameter is deprecated
        return LDAP_Filter.forAll(
            pattern,
            ["name", "description"],
            _escape_filter_chars=_escape_filter_chars,
            school_prefix=school_prefix,
        )

    @staticmethod
    def forComputers(pattern):  # type: (str) -> str
        return LDAP_Filter.forAll(pattern, ["name", "description"], ["mac", "ip"])

    regWhiteSpaces = re.compile(r"\s+")

    @staticmethod
    def forAll(
        pattern,  # type: str
        subMatch=[],  # type: Optional[List[str]]
        fullMatch=[],  # type: Optional[List[str]]
        prefixes={},  # type: Optional[Dict[str, Any]]
        _escape_filter_chars=True,  # type: Optional[bool]
        school_suffix="",  # type: Optional[str]
        school_prefix="",  # type: Optional[str]
        seperator="-",  # type: Optional[str]
    ):
        # type: (...) -> str
        expressions = []
        for iword in LDAP_Filter.regWhiteSpaces.split(pattern or ""):
            # evaluate the subexpression (search word over different attributes)

            subexpr = []
            if _escape_filter_chars:
                # all expressions for a full string match
                iword = escape_filter_chars(iword)
            if iword:
                subexpr += ["(%s=%s)" % (jattr, iword) for jattr in fullMatch]

            # all expressions for a substring match
            if not iword:
                iword = "*"
            elif iword.find("*") < 0:
                iword = "*%s*" % iword

            if school_prefix:
                iword = school_prefix + seperator + iword
            if school_suffix:
                iword = iword + seperator + school_suffix

            subexpr += ["(%s=%s%s)" % (jattr, prefixes.get(jattr, ""), iword) for jattr in subMatch]
            # append to list of all search expressions
            expressions.append("(|%s)" % "".join(subexpr))

        if not expressions:
            return ""
        return "(&%s)" % "".join(expressions)


class Display:
    @staticmethod
    def user(udm_object):  # type: (UdmObject) -> str
        fullname = udm_object["lastname"]
        if "firstname" in udm_object and udm_object["firstname"]:  # noqa: RUF019
            fullname += ", %(firstname)s" % udm_object

        return fullname + " (%(username)s)" % udm_object

    @staticmethod
    def user_ldap(ldap_object):  # type: (Dict[str, Any]) -> str
        fullname = ldap_object.get("sn", [b""])[0].decode("utf-8")
        if ldap_object.get("givenName", [b""])[0]:
            fullname += ", %s" % ldap_object["givenName"][0].decode("utf-8")

        return fullname + " (%s)" % ldap_object["uid"][0].decode("utf-8")
