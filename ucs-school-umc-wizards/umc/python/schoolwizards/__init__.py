#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  Wizards
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

import functools
import re
from enum import Enum

import six

import univention.admin.modules as udm_modules
from ucsschool.lib.models import (
    IPComputer,
    MacComputer,
    School,
    SchoolAdmin,
    SchoolClass,
    SchoolComputer,
    Staff,
    Student,
    Teacher,
    TeachersAndStaff,
    UCCComputer,
    User,
    WindowsComputer,
    WrongModel,
)
from ucsschool.lib.models.utils import add_module_logger_to_schoollib
from ucsschool.lib.school_umc_base import SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import ADMIN_WRITE, USER_READ, USER_WRITE, LDAP_Connection
from univention.admin.uexceptions import base as uldapBaseException, noObject
from univention.lib.i18n import Translation
from univention.management.console.base import UMC_Error
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import sanitize, simple_response
from univention.management.console.modules.sanitizers import (
    ChoicesSanitizer,
    DictSanitizer,
    DNSanitizer,
    StringSanitizer,
)
from univention.management.console.modules.schoolwizards.SchoolImport import SchoolImport
from univention.udm import UDM

try:
    from typing import Any, Iterator, Optional, Set, Union

    from univention.admin.uldap import access as LoType
except ImportError:
    pass

_ = Translation("ucs-school-umc-wizards").translate


# TODO: remove once this is implemented in uexceptions, see Bug #30088
def get_exception_msg(e):
    msg = getattr(e, "message", "")
    if getattr(e, "args", False):
        if e.args[0] != msg or len(e.args) != 1:
            for arg in e.args:
                msg += " " + arg
    return msg


USER_TYPES = {
    "student": Student,
    "teacher": Teacher,
    "staff": Staff,
    "teachersAndStaff": TeachersAndStaff,
    "schoolAdmin": SchoolAdmin,
}


COMPUTER_TYPES = {
    "windows": WindowsComputer,
    "macos": MacComputer,
    "ucc": UCCComputer,
    "ipmanagedclient": IPComputer,
}


class OperationType(Enum):
    CREATE = 0
    MODIFY = 1
    DELETE = 2
    GET = 3


def check_workaround_constraints(
    subject_schools, old_object_schools, new_object_schools, operation_type
):  # type: (Set[str], Set[str], Set[str], int) -> bool
    """
    This function checks the constraints for the admin workaround as described in Bug #52757.
    Returns whether the constraints are fulfilled or not.

    Attention! This function does only check the general constrain for DELETE. User deletions are not checked
    correctly due to their special handling.

    :param subject_schools: The set of schools the subject is in
    :param old_object_schools: The set of schools the object is in before any modification
    :param new_object_schools: The set of schools the object is in after the modification
    :param operation_type: The type of operation to check the constraints for
    :return: True if the operation should be allowed, False otherwise
    """
    if subject_schools == set() or (
        old_object_schools == set() and operation_type != OperationType.CREATE
    ):
        # Prevent editing by global users; prevent editing of global users
        return False
    if operation_type == OperationType.CREATE:
        return new_object_schools <= subject_schools and new_object_schools != set()
    elif operation_type == OperationType.MODIFY:
        return subject_schools & old_object_schools != set() and old_object_schools == new_object_schools
    elif operation_type == OperationType.DELETE:
        return old_object_schools <= subject_schools
    elif operation_type == OperationType.GET:
        return subject_schools & old_object_schools != set()
    else:  # Operations with undefined constraints just return False
        return False


def iter_objects_in_request(
    request, lo, operation_type, subject_schools=frozenset(), is_domain_admin=False
):  # type: (Any, LoType, int, Set[str], bool) -> Iterator[Union[School, User, SchoolComputer, SchoolClass]]
    """
    This function iterates over all given objects given in the request and returns the corresponding UCS@school lib
    objects already altered with the changes from the request.

    Attention: If the admin workaround is activated (see Bug #52757) certain constraints are checked. If they are not
    fulfilled this function aborts with an UMC Error.

    :param request: The request from the UMCP call containing all the objects to be iterated over.
    :param lo: A LDAP access for retrieving existing UCS@school objects.
    :param operation_type: The type of operation applied onto the returned objects. Necessary for constraint checking.
    :param subject_schools: The schools the user triggering the UMCP command is in. This is needed for constraint checking.
    :param is_domain_admin: If the user triggering the UMCP command is a domain admin or not. This is needed for constraint checking.

    :returns: An iterator to iterate over the altered or new UCS@school objects.
    :raises UMC_Error: If an object that should exist does not or if the admin workaround constraints are not met.
    """
    klass = {
        "schoolwizards/schools": School,
        "schoolwizards/users": User,
        "schoolwizards/computers": SchoolComputer,
        "schoolwizards/classes": SchoolClass,
    }[request.flavor]
    admin_workaround_active = ucr.is_true("ucsschool/wizards/schoolwizards/workaround/admin-connection")
    for obj_props in request.options:
        obj_props = obj_props["object"]
        for key, value in six.iteritems(obj_props):
            if isinstance(value, six.string_types):
                obj_props[key] = value.strip()
        if issubclass(klass, User):
            klass = USER_TYPES.get(obj_props.get("type"), User)
        elif issubclass(klass, SchoolComputer):
            klass = COMPUTER_TYPES.get(obj_props.get("type"), SchoolComputer)
        dn = obj_props.get("$dn$")
        if "name" not in obj_props:
            # important for get_school in district_mode!
            obj_props["name"] = klass.get_name_from_dn(dn)
        if issubclass(klass, SchoolClass):
            # workaround to be able to reuse this function everywhere
            obj_props["name"] = "%s-%s" % (obj_props["school"], obj_props["name"])
        object_new_schools = (set([obj_props.get("school")]) if "school" in obj_props else set()) | set(
            obj_props.get("schools", [])
        )
        if operation_type == OperationType.CREATE:
            if (
                admin_workaround_active
                and not is_domain_admin
                and not check_workaround_constraints(
                    subject_schools, set, object_new_schools, operation_type
                )
            ):
                raise UMC_Error(
                    _("You do not have the rights to create an object for the schools %s")
                    % object_new_schools
                )
            obj = klass(**obj_props)
        else:
            try:
                obj = klass.from_dn(dn, obj_props.get("school"), lo)
            except noObject:
                raise UMC_Error(
                    _("The %s %r does not exists or might have been removed in the meanwhile.")
                    % (getattr(klass, "type_name", klass.__name__), obj_props["name"])
                )
            try:
                object_old_schools = set(obj.schools)
            except AttributeError:  # there are school lib objects that do not have the schools attribute
                object_old_schools = set()
            if obj.school:
                object_old_schools.add(obj.school)
            if (
                admin_workaround_active
                and not is_domain_admin
                and not check_workaround_constraints(
                    subject_schools, object_old_schools, object_new_schools, operation_type
                )
            ):
                raise UMC_Error(
                    _(
                        "You do not have the right to modify the object with the DN %s from the schools %s."
                    )
                    % (dn, object_old_schools)
                )
            obj.set_attributes(**obj_props)
        if dn:
            obj.old_dn = dn
        yield obj


def response(func):
    @functools.wraps(func)
    def _decorated(self, request, *a, **kw):
        ret = func(self, request, *a, **kw)
        self.finished(request.id, ret)

    return _decorated


def sanitize_object(**kwargs):
    def _decorator(func):
        return sanitize(DictSanitizer(dict(object=DictSanitizer(kwargs))))(func)

    return _decorator


class Instance(SchoolBaseModule, SchoolImport):
    def __init__(self):
        super(Instance, self).__init__()
        self._own_schools = None  # type: Optional[Set[str]]
        self._user_is_domain_admin = None  # type: Optional[bool]

    @property
    def admin_workaround_active(self):
        # Bug #44641: workaround with security implications!
        return ucr.is_true("ucsschool/wizards/schoolwizards/workaround/admin-connection")

    @LDAP_Connection(ADMIN_WRITE)
    def own_schools(self, ldap_admin_write=None):  # type: (Optional[LoType]) -> Set[str]
        """
        Returns a set of all schools the current user has.
        """
        if self._own_schools is None:
            try:
                current_user = User.from_dn(self.user_dn, None, ldap_admin_write)  # type: User
                self._own_schools = ({current_user.school} if current_user.school else set()) | set(
                    current_user.schools
                )
            except (noObject, WrongModel):
                MODULE.error("The user with dn {} could not be found or associated with any schools!")
                self._own_schools = set()
        return self._own_schools

    def is_domain_admin(self):  # type: () -> bool
        """
        Returns if the currently logged in user is a domain admin or not.
        """
        if self._user_is_domain_admin is None:
            self._user_is_domain_admin = (
                "cn=Domain Admins,cn=groups,{}".format(ucr.get("ldap/base"))
                in UDM.admin().version(0).obj_by_dn(self.user_dn).props.groups
            )
        return self._user_is_domain_admin

    def init(self):
        super(Instance, self).init()
        add_module_logger_to_schoollib()

    @simple_response
    def is_singlemaster(self):
        return ucr.is_true("ucsschool/singlemaster", False)

    @sanitize(
        schooldc=StringSanitizer(
            required=True, regex_pattern=re.compile(r"^[a-zA-Z](([a-zA-Z0-9-_]*)([a-zA-Z0-9]$))?$")
        ),
        admindc=StringSanitizer(
            required=False, regex_pattern=re.compile(r"^[a-zA-Z](([a-zA-Z0-9-_]*)([a-zA-Z0-9]$))?$")
        ),
        schoolou=StringSanitizer(
            required=True, regex_pattern=re.compile(r"^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$")
        ),
    )
    @simple_response
    def move_dc(self, schooldc, schoolou):
        params = ["--dcname", schooldc, "--ou", schoolou]
        return_code, stdout = self._run_script(SchoolImport.MOVE_DC_SCRIPT, params, True)
        return {"success": return_code == 0, "message": stdout}

    @simple_response
    def computer_types(self):
        ret = []
        computer_types = [WindowsComputer, MacComputer, IPComputer]
        try:
            import univention.admin.handlers.computers.ucc as ucc

            del ucc
        except ImportError:
            pass
        else:
            computer_types.insert(1, UCCComputer)
        for computer_type in computer_types:
            ret.append({"id": computer_type._meta.udm_module_short, "label": computer_type.type_name})
        return ret

    @response
    @LDAP_Connection()
    def share_servers(self, request, ldap_user_read=None):
        # udm/syntax/choices UCSSchool_Server_DN
        ret = [{"id": "", "label": ""}]
        for module in [
            "computers/domaincontroller_master",
            "computers/domaincontroller_backup",
            "computers/domaincontroller_slave",
            "computers/memberserver",
        ]:
            for obj in udm_modules.lookup(module, None, ldap_user_read, scope="sub"):
                obj.open()
                ret.append({"id": obj.dn, "label": obj.info.get("fqdn", obj.info["name"])})
        return ret

    @sanitize_object(**{"$dn$": DNSanitizer(required=True)})
    @response
    @LDAP_Connection()
    def _get_obj(self, request, ldap_user_read=None):
        ret = []
        for obj in iter_objects_in_request(
            request, ldap_user_read, OperationType.GET, self.own_schools(), self.is_domain_admin()
        ):
            MODULE.process("Getting %r" % (obj))
            obj = obj.from_dn(obj.old_dn, obj.school, ldap_user_read)
            ret.append(obj.to_dict())
        return ret

    @response
    @LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
    def _create_obj(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
        # Bug #44641: workaround with security implications!
        if self.admin_workaround_active:
            ldap_user_write = ldap_admin_write

        ret = []
        for obj in iter_objects_in_request(
            request, ldap_user_write, OperationType.CREATE, self.own_schools(), self.is_domain_admin()
        ):
            MODULE.process("Creating %r" % (obj,))
            obj.validate(ldap_user_read)
            if obj.errors:
                ret.append({"result": {"message": obj.get_error_msg()}})
                MODULE.process("Validation failed %r" % (ret[-1],))
                continue
            try:
                if obj.create(ldap_user_write, validate=False):
                    ret.append(True)
                else:
                    ret.append({"result": {"message": _('"%s" already exists!') % obj.name}})
            except uldapBaseException as exc:
                ret.append({"result": {"message": get_exception_msg(exc)}})
                MODULE.process("Creation failed %r" % (ret[-1],))
        return ret

    @sanitize_object(**{"$dn$": DNSanitizer(required=True)})
    @response
    @LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
    def _modify_obj(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
        # Bug #44641: workaround with security implications!
        if self.admin_workaround_active:
            ldap_user_write = ldap_admin_write

        ret = []
        for obj in iter_objects_in_request(
            request, ldap_user_write, OperationType.MODIFY, self.own_schools(), self.is_domain_admin()
        ):
            MODULE.process("Modifying %r" % (obj))
            obj.validate(ldap_user_read)
            if obj.errors:
                ret.append({"result": {"message": obj.get_error_msg()}})
                continue
            try:
                obj.modify(ldap_user_write, validate=False)
            except uldapBaseException as exc:
                ret.append({"result": {"message": get_exception_msg(exc)}})
            else:
                ret.append(True)  # no changes? who cares?
        return ret

    @sanitize_object(**{"$dn$": DNSanitizer(required=True)})
    @response
    @LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
    def _delete_obj(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
        # Bug #44641: workaround with security implications!
        if self.admin_workaround_active:
            ldap_user_write = ldap_admin_write

        ret = []
        for obj in iter_objects_in_request(
            request, ldap_user_write, OperationType.DELETE, self.own_schools(), self.is_domain_admin()
        ):
            obj.name = obj.get_name_from_dn(obj.old_dn)
            MODULE.process("Deleting %r" % (obj))
            if obj.remove(ldap_user_write):
                ret.append(True)
            else:
                ret.append({"result": {"message": _('"%s" does not exist!') % obj.name}})
        return ret

    def _get_all(self, klass, school, filter_str, lo):
        if school:
            schools = [School.cache(school)]
        else:
            schools = School.from_binddn(lo)
        objs = []
        for school in schools:
            try:
                objs.extend(klass.get_all(lo, school.name, filter_str=filter_str, easy_filter=True))
            except noObject as exc:
                MODULE.error("Could not get all objects of %r: %r" % (klass.__name__, exc))
        return [obj.to_dict() for obj in objs]

    @sanitize(
        school=StringSanitizer(required=True),
        type=ChoicesSanitizer(["all"] + USER_TYPES.keys(), required=True),
        filter=StringSanitizer(default=""),
    )
    @response
    @LDAP_Connection()
    def get_users(self, request, ldap_user_read=None):
        school = request.options["school"]
        user_class = USER_TYPES.get(request.options["type"], User)
        return self._get_all(user_class, school, request.options.get("filter"), ldap_user_read)

    get_user = _get_obj
    modify_user = _modify_obj
    create_user = _create_obj

    @sanitize_object(
        **{"remove_from_school": SchoolSanitizer(required=True), "$dn$": DNSanitizer(required=True)}
    )
    @response
    @LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
    def delete_user(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
        # Bug #44641: workaround with security implications!
        if self.admin_workaround_active:
            ldap_user_write = ldap_admin_write

        ret = []
        for obj_props in request.options:
            obj_props = obj_props["object"]
            try:
                obj = User.from_dn(obj_props["$dn$"], None, ldap_user_write)  # type: User
            except noObject:
                raise UMC_Error(
                    _("The %s %r does not exists or might have been removed in the meanwhile.")
                    % (
                        getattr(User, "type_name", None) or User.__name__,
                        User.get_name_from_dn(obj_props["$dn$"]),
                    )
                )
            school = obj_props["remove_from_school"]
            user_schools = ({obj.school} if obj.school else set()) | set(obj.schools)
            if (self.admin_workaround_active and not self.is_domain_admin()) and (
                school not in self.own_schools() or school not in user_schools
            ):
                raise UMC_Error(
                    _("You do not have the right to delete the user with the dn %s from the school %s.")
                    % (obj_props["$dn$"], school)
                )
            success = obj.remove_from_school(school, ldap_user_write)
            # obj.old_dn is None when the ucsschool lib has deleted the user after the last school was
            # removed from it
            if success and obj.old_dn is not None:
                success = obj.modify(ldap_user_write)
            if not success:
                success = {"result": {"message": _("Failed to remove user from school.")}}
            ret.append(success)
        return ret

    @sanitize(
        school=StringSanitizer(required=True),
        type=ChoicesSanitizer(["all"] + COMPUTER_TYPES.keys(), required=True),
        filter=StringSanitizer(default=""),
    )
    @response
    @LDAP_Connection()
    def get_computers(self, request, ldap_user_read=None):
        school = request.options["school"]
        computer_class = COMPUTER_TYPES.get(request.options["type"], SchoolComputer)
        return self._get_all(computer_class, school, request.options.get("filter"), ldap_user_read)

    get_computer = _get_obj
    modify_computer = _modify_obj

    @response
    @LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
    def create_computer(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
        # Bug #44641: workaround with security implications!
        if self.admin_workaround_active:
            ldap_user_write = ldap_admin_write

        for option in request.options:
            MODULE.process(option)
        ignore_warnings = [
            option.get("object", {}).get("ignore_warning", False) for option in request.options
        ]
        ignore_warnings.reverse()
        ret = {}
        for obj in iter_objects_in_request(
            request, ldap_user_write, OperationType.CREATE, self.own_schools(), self.is_domain_admin()
        ):
            ignore_warning = ignore_warnings.pop()
            obj.validate(ldap_user_read)
            if obj.errors:
                ret["error"] = obj.get_error_msg()
                MODULE.process("Validation error: {}".format(ret["error"]))
                continue
            elif obj.warnings and not ignore_warning:
                ret["warning"] = obj.get_warning_msg()
                MODULE.process("Validation warning: {}".format(ret["warning"]))
                continue
            try:
                if obj.create(ldap_user_write, validate=False):
                    ret = True
                else:
                    ret["error"] = _('"%s" already exists!') % obj.name
            except uldapBaseException as exc:
                ret["error"] = get_exception_msg(exc)
                MODULE.process("Creation failed {}".format(ret["error"]))
        return [{"result": ret}]

    delete_computer = _delete_obj

    @sanitize(school=StringSanitizer(required=True), filter=StringSanitizer(default=""))
    @response
    @LDAP_Connection()
    def get_classes(self, request, ldap_user_read=None):
        school = request.options["school"]
        return self._get_all(SchoolClass, school, request.options.get("filter"), ldap_user_read)

    get_class = _get_obj
    modify_class = _modify_obj
    create_class = _create_obj
    delete_class = _delete_obj

    @response
    @LDAP_Connection()
    def get_schools(self, request, ldap_user_read=None):
        schools = School.get_all(
            ldap_user_read, filter_str=request.options.get("filter"), easy_filter=True
        )
        return [school.to_dict() for school in schools]

    get_school = _get_obj
    modify_school = _modify_obj
    create_school = _create_obj
    delete_school = _delete_obj
