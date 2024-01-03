#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# Copyright 2020-2024 Univention GmbH
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
"""This module check the constistency of USC@school users, shares and groups"""
import re
import sys
from typing import Dict, List, Optional, Tuple  # noqa: F401

from ldap import INVALID_DN_SYNTAX
from ldap.dn import escape_dn_chars
from ldap.filter import escape_filter_chars, filter_format

from univention.admin.uexceptions import noObject, permissionDenied
from univention.admin.uldap import getMachineConnection
from univention.config_registry import ConfigRegistry

from .models.base import WrongObjectType
from .models.school import School
from .models.user import User
from .roles import (
    create_ucsschool_role_string,
    role_dc_slave_admin,
    role_dc_slave_edu,
    role_exam_user,
    role_memberserver_admin,
    role_memberserver_edu,
    role_school_admin,
    role_school_class,
    role_school_class_share,
    role_staff,
    role_student,
    role_teacher,
    role_workgroup,
    role_workgroup_share,
)
from .schoolldap import SchoolSearchBase


class UserCheck(object):
    def __init__(self):
        ucr = ConfigRegistry()
        ucr.load()
        ldap_base = ucr.get("ldap/base")
        self.lo, _ = getMachineConnection()

        admins_prefix = ucr.get("ucsschool/ldap/default/groupprefix/admins", "admins-")
        teachers_prefix = ucr.get("ucsschool/ldap/default/groupprefix/teachers", "lehrer-")
        staff_prefix = ucr.get("ucsschool/ldap/default/groupprefix/staff", "mitarbeiter-")
        students_prefix = ucr.get("ucsschool/ldap/default/groupprefix/pupils", "schueler-")

        self.teachers_regex = re.compile(
            r"cn={}(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(teachers_prefix, ldap_base),
            flags=re.IGNORECASE,
        )
        self.staff_regex = re.compile(
            r"cn={}(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(staff_prefix, ldap_base),
            flags=re.IGNORECASE,
        )
        self.students_regex = re.compile(
            r"cn={}(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(students_prefix, ldap_base),
            flags=re.IGNORECASE,
        )

        self.ucsschool_obj_classes = {
            "ucsschoolTeacher": role_teacher,
            "ucsschoolStaff": role_staff,
            "ucsschoolStudent": role_student,
            "ucsschoolAdministrator": role_school_admin,
            "ucsschoolExam": role_exam_user,
        }

        self.domain_users_ou = {}
        self.students_ou = {}
        self.teachers_ou = {}
        self.staff_ou = {}
        self.admins_ou = {}

        self.all_schools = [ou.name for ou in School.get_all(self.lo)]
        for ou in self.all_schools:
            self.domain_users_ou[ou] = "cn=Domain Users {0},cn=groups,ou={0},{1}".format(ou, ldap_base)
            self.students_ou[ou] = "cn={}{},cn=groups,ou={},{}".format(
                students_prefix, ou.lower(), ou, ldap_base
            )
            self.teachers_ou[ou] = "cn={}{},cn=groups,ou={},{}".format(
                teachers_prefix, ou.lower(), ou, ldap_base
            )
            self.staff_ou[ou] = "cn={}{},cn=groups,ou={},{}".format(
                staff_prefix, ou.lower(), ou, ldap_base
            )
            self.admins_ou[ou] = "cn={}{},cn=ouadmins,cn=groups,{}".format(
                admins_prefix, ou.lower(), ldap_base
            )

    def check_allowed_membership(self, group_dn, students=False, teachers=False, staff=False):
        # type: (str, Optional[bool], Optional[bool], Optional[bool]) -> List[str]
        """
        This function is used to check if a group of a user matches the users UCS@school role(s).
        The caller specifies the group dn and the user roles which are allowed by setting them to 'True'.
        Example:
        'group_dn' is expected to be a teachers group, i.e. 'teachers' is set to True by the caller.
        If the group turns out to be a students group (where teachers are disallowed) and
        'students' is False, it is an error. A warning will be appended to a list which will be returned.
        """
        errors = []
        if self.students_regex.match(group_dn) and not students:
            errors.append("Disallowed member of students group {}.".format(group_dn))
        if self.teachers_regex.match(group_dn) and not teachers:
            errors.append("Disallowed member of teachers group {}.".format(group_dn))
        if self.staff_regex.match(group_dn) and not staff:
            errors.append("Disallowed member of staff group {}.".format(group_dn))

        return errors

    def get_users_from_ldap(
        self, school, users
    ):  # type: (str, List[str]) -> Tuple[str, Dict[str, List[bytes]]]
        ldap_user_list = []
        if users:
            for user_dn in users:
                try:
                    ldap_user_list.append(self.lo.search(base=user_dn)[0])
                except noObject:
                    print("User with DN {} does not exist.".format(user_dn))
                    sys.exit()
                except INVALID_DN_SYNTAX:
                    print("DN {} has invalid syntax.".format(user_dn))
                    sys.exit(1)

        if school:
            users_from_school_list = self.lo.search(
                filter=filter_format(
                    "(&(univentionObjectType=users/user)(ucsschoolSchool=%s))", (school,)
                )
            )
            # all users from this school gets added to the list (no duplicates)
            for user in users_from_school_list:
                if user not in ldap_user_list:
                    ldap_user_list.append(user)

        if not users and not school:
            ldap_user_list = self.lo.search(
                filter="(&(univentionObjectType=users/user)(objectClass=ucsschoolType))"
            )

        return ldap_user_list

    def check_user(self, dn, attrs):  # type: (str, Dict[str, List[bytes]]) -> List[str]
        issues = []

        try:
            user_obj = User.from_dn(dn, None, self.lo)
        except WrongObjectType as exc:
            issues.append("Expected a user object, but is not: {}".format(exc))
            return issues
        except permissionDenied as exc:
            issues.append("Could not access this user  {}".format(exc))
            return issues

        # check if objectClass is correctly set
        user_obj_classes = [x.decode("UTF-8") for x in attrs.get("objectClass", [])]
        if not any(cls in user_obj_classes for cls in self.ucsschool_obj_classes):
            issues.append("User has no UCS@school Object Class set.")

        # check if UCS@school role is correctly set for each school dependent of the objectClass
        user_roles = []

        for cls in user_obj_classes:
            try:
                user_roles.append(self.ucsschool_obj_classes[cls])
            except KeyError:
                continue

        # exam users are an exception. They are objectClass 'ucsschoolStudent',
        # but only require to have the role 'exam_user:school:<userschool>'
        if self.ucsschool_obj_classes["ucsschoolExam"] in user_roles:
            try:
                user_roles.remove(self.ucsschool_obj_classes["ucsschoolStudent"])
            except ValueError:
                pass

        # ucsschool_roles are validated case-insensitive
        ucsschool_roles = {r.lower() for r in user_obj.ucsschool_roles}
        for role in user_roles:
            for school in user_obj.schools:
                ucsschool_role_string = create_ucsschool_role_string(role, school)
                if ucsschool_role_string.lower() not in ucsschool_roles:
                    issues.append("User does not have UCS@school Role {}".format(ucsschool_role_string))

        # check appropriate group memberships (case-insensitive)
        users_group_dns = [_dn.lower() for _dn in self.lo.searchDn(filter="uniqueMember={}".format(dn))]

        # further checks require all of user_obj.schools to exist
        for school in user_obj.schools:
            if school not in self.all_schools:
                issues.append(
                    "User is member of school {}, which does not exist anymore. "
                    "Further tests on this user cannot be performed.".format(school)
                )
                # abort further user checks here
                return issues

        for school in user_obj.schools:
            if self.domain_users_ou[school].lower() not in users_group_dns:
                issues.append("Not member of group {}".format(self.domain_users_ou[school]))
        # check students
        if user_obj.is_student(self.lo):
            for school in user_obj.schools:
                if self.students_ou[school].lower() not in users_group_dns:
                    issues.append("Not member of group {}".format(self.students_ou[school]))
            for group_dn in users_group_dns:
                issues += self.check_allowed_membership(group_dn, students=True)

        # check admins
        if user_obj.is_administrator(self.lo):
            for ou in user_obj.schools:
                if self.admins_ou[ou].lower() not in users_group_dns:
                    issues.append("Not member of group {}".format(self.admins_ou[ou]))
            for group_dn in users_group_dns:
                if self.students_regex.match(group_dn):
                    issues.append("Admin should not be in a students group {}".format(group_dn))

        # check teachers and staff
        if user_obj.is_teacher(self.lo) and user_obj.is_staff(self.lo):
            for ou in user_obj.schools:
                if self.teachers_ou[ou].lower() not in users_group_dns:
                    issues.append("Not member of group {}".format(self.teachers_ou[ou]))
                if self.staff_ou[ou].lower() not in users_group_dns:
                    issues.append("Not member of group {}".format(self.staff_ou[ou]))
            for group_dn in users_group_dns:
                issues += self.check_allowed_membership(group_dn, teachers=True, staff=True)

        # check teachers
        elif user_obj.is_teacher(self.lo):
            for ou in user_obj.schools:
                if self.teachers_ou[ou].lower() not in users_group_dns:
                    issues.append("Not member of group {}".format(self.teachers_ou[ou]))
            for group_dn in users_group_dns:
                issues += self.check_allowed_membership(group_dn, teachers=True)

        # check staff
        elif user_obj.is_staff(self.lo):
            for ou in user_obj.schools:
                if self.staff_ou[ou].lower() not in users_group_dns:
                    issues.append("Not member of group {}".format(self.staff_ou[ou]))
            for group_dn in users_group_dns:
                issues += self.check_allowed_membership(group_dn, staff=True)

        # Check if student is in a class group.
        if not user_obj.school_classes and user_obj.is_student(self.lo):
            issues.append("Is not a member of any school class.")

        # Users should also be member of the corresponding school
        for ou in user_obj.school_classes:
            if ou.encode("UTF-8") not in attrs["ucsschoolSchool"]:
                issues.append(
                    "Is member of class {} but school property is not correspondingly set.".format(
                        user_obj.school_classes[ou][0]
                    )
                )

        return issues


def check_mandatory_groups_exist(school=None):  # type: (str) -> Dict[str, List[str]]
    ucr = ConfigRegistry()
    ucr.load()
    ldap_base = ucr.get("ldap/base")

    problematic_objects = {}

    lo, _ = getMachineConnection()

    mandatory_global_groups = [
        "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ldap_base),
        "cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ldap_base),
        "cn=Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ldap_base),
        "cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ldap_base),
    ]

    global_groups_issues = []
    for mandatory_global_group in mandatory_global_groups:
        try:
            lo.searchDn(base=mandatory_global_group)
        except noObject:
            global_groups_issues.append(
                "Mandatory group {} does not exist.".format(mandatory_global_group)
            )

    if global_groups_issues:
        problematic_objects["Global Groups"] = global_groups_issues

    if school:
        all_schools = [school]
    else:
        all_schools = [ou.name for ou in School.get_all(lo)]
    for ou in all_schools:
        search_base = SchoolSearchBase([ou])
        issues = []
        mandatory_groups = [
            "cn=Domain Users {0},cn=groups,ou={0},{1}".format(escape_dn_chars(ou), ldap_base),
            "cn=OU{}-DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(escape_dn_chars(ou), ldap_base),
            "cn=OU{}-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(
                escape_dn_chars(ou), ldap_base
            ),
            "cn=OU{}-Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(
                escape_dn_chars(ou), ldap_base
            ),
            "cn=OU{}-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(
                escape_dn_chars(ou), ldap_base
            ),
            "cn=OU{}-Klassenarbeit,cn=ucsschool,cn=groups,{}".format(escape_dn_chars(ou), ldap_base),
            "cn=admins-{},cn=ouadmins,cn=groups,{}".format(escape_dn_chars(ou), ldap_base),
        ]
        for mandatory_group in mandatory_groups:
            try:
                lo.searchDn(base=mandatory_group)
            except noObject:
                issues.append("Mandatory group {} does not exist.".format(mandatory_group))

        if issues:
            problematic_objects[search_base.schoolDN] = issues
    return problematic_objects


def check_containers(school=None):  # type: (Optional[str]) -> Dict[str, List[str]]
    problematic_objects = {}

    lo, _ = getMachineConnection()

    if school:
        all_schools = [school]
    else:
        all_schools = [ou.name for ou in School.get_all(lo)]

    for ou in all_schools:
        search_base = SchoolSearchBase([ou])
        issues = []
        mandatory_containers = [
            search_base.computers,
            search_base.examUsers,
            search_base.groups,
            search_base.rooms,
            search_base.students,
            search_base.classes,
            search_base.shares,
            search_base.classShares,
            search_base.users,
            search_base.dhcp,
            search_base.networks,
            search_base.policies,
            search_base.printers,
        ]
        for mandatory_container in mandatory_containers:
            try:
                lo.searchDn(base=mandatory_container)
            except noObject:
                issues.append("Mandatory container {} does not exist.".format(mandatory_container))

        if issues:
            problematic_objects[search_base.schoolDN] = issues
    return problematic_objects


def check_shares(school=None):  # type: (Optional[str]) -> Dict[str, List[str]]
    ucr = ConfigRegistry()
    ucr.load()

    problematic_objects = {}

    lo, _ = getMachineConnection()

    if school:
        all_schools = [school]
        school_filter = school
        allow_wildcards = False
    else:
        all_schools = [ou.name for ou in School.get_all(lo)]
        school_filter = "*"
        allow_wildcards = True

    if ucr.is_true("ucsschool/import/generate/share/marktplatz", True):
        for ou in all_schools:
            search_base = SchoolSearchBase([ou])
            marktplatz_share = "cn=Marktplatz,cn=shares,{}".format(search_base.schoolDN)
            try:
                lo.search(base=marktplatz_share)
            except noObject:
                problematic_objects.setdefault(marktplatz_share, []).append(
                    "The 'Marktplatz' share of school %r does not exist." % (ou,)
                )

    def maybe_allow_wildcards(filter_string):
        if allow_wildcards:
            filter_string = filter_string.replace(escape_filter_chars("*"), "*")
        return filter_string

    # check if there is a school class for each class share
    classes = []
    role_classes_string = create_ucsschool_role_string(role_school_class, school_filter)
    for _dn, attrs in lo.search(
        filter=maybe_allow_wildcards(filter_format("(ucsschoolRole=%s)", [role_classes_string]))
    ):
        classes.append(attrs["cn"][0].decode("UTF-8"))

    role_class_share_string = create_ucsschool_role_string(role_school_class_share, school_filter)
    cls_shares = lo.search(
        filter=maybe_allow_wildcards(filter_format("(ucsschoolRole=%s)", [role_class_share_string]))
    )
    for dn, attrs in cls_shares:
        if attrs["cn"][0].decode("UTF-8") not in classes:
            problematic_objects.setdefault(dn, []).append(
                "Corresponding class {} is missing.".format(attrs["cn"][0].decode("UTF-8"))
            )

    # check if there is a work group for each work group share
    work_groups = []
    role_workgroup_string = create_ucsschool_role_string(role_workgroup, school_filter)
    for dn, attrs in lo.search(
        filter=maybe_allow_wildcards(filter_format("(ucsschoolRole=%s)", [role_workgroup_string]))
    ):
        work_groups.append(attrs["cn"][0].decode("UTF-8"))

    role_workgroup_share_string = create_ucsschool_role_string(role_workgroup_share, school_filter)
    wg_share = lo.search(
        filter=maybe_allow_wildcards(filter_format("(ucsschoolRole=%s)", [role_workgroup_share_string]))
    )
    for dn, attrs in wg_share:
        if attrs["cn"][0].decode("UTF-8") not in work_groups:
            problematic_objects.setdefault(dn, []).append(
                "Corresponding work group {} is missing.".format(attrs["cn"][0].decode("UTF-8"))
            )

    return problematic_objects


def check_server_group_membership(school=None):  # type: (Optional[str]) -> Dict[str, List[str]]
    def server_in_group_errors(lo, role, members, group_dn):
        problematic_objects = {}
        for dn, _attrs in lo.search(filter=filter_format("(ucsschoolRole=%s)", [role])):
            if dn not in members:
                problematic_objects.setdefault(dn, []).append(
                    "is not a member of group {}".format(group_dn)
                )
        return problematic_objects

    ucr = ConfigRegistry()
    ucr.load()
    ldap_base = ucr.get("ldap/base")
    problematic_objects = {}

    lo, _ = getMachineConnection()

    if school:
        all_schools = [school]
    else:
        all_schools = [ou.name for ou in School.get_all(lo)]

    dn_dc_edu_global = "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ldap_base)
    dn_dc_admin_global = "cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ldap_base)
    dn_member_edu_global = "cn=Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ldap_base)
    dn_member_admin_global = "cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ldap_base)
    global_groups = [dn_dc_edu_global, dn_dc_admin_global, dn_member_edu_global, dn_member_admin_global]

    members = {}
    for dn in global_groups:
        try:
            members[dn] = [x.decode("UTF-8") for x in lo.search(base=dn)[0][1]["uniqueMember"]]
        except KeyError:
            members[dn] = []
            continue
        except noObject:
            problematic_objects.setdefault(dn, []).append(
                "Memberships of group {} could not be checked. It does not exist.".format(dn)
            )
            continue

    for ou in all_schools:
        dn_dc_edu = "cn=OU{}-DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(
            escape_dn_chars(ou), ldap_base
        )
        dn_dc_admin = "cn=OU{}-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(
            escape_dn_chars(ou), ldap_base
        )
        dn_member_edu = "cn=OU{}-Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(
            escape_dn_chars(ou), ldap_base
        )
        dn_member_admin = "cn=OU{}-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(
            escape_dn_chars(ou), ldap_base
        )
        role_dc_edu_str = create_ucsschool_role_string(role_dc_slave_edu, ou)
        role_dc_admin_str = create_ucsschool_role_string(role_dc_slave_admin, ou)
        role_member_edu_str = create_ucsschool_role_string(role_memberserver_edu, ou)
        role_member_admin_str = create_ucsschool_role_string(role_memberserver_admin, ou)
        checks = [
            (role_dc_edu_str, dn_dc_edu, dn_dc_edu_global),
            (role_dc_admin_str, dn_dc_admin, dn_dc_admin_global),
            (role_member_edu_str, dn_member_edu, dn_member_edu_global),
            (role_member_admin_str, dn_member_admin, dn_member_admin_global),
        ]

        for role, group_dn, global_group in checks:
            try:
                members[group_dn] = [
                    x.decode("UTF-8") for x in lo.search(base=group_dn)[0][1]["uniqueMember"]
                ]
            except KeyError:
                members[group_dn] = []
            except noObject:
                problematic_objects.setdefault(dn, []).append(
                    "Memberships of group {} could not be checked. It does not exist".format(dn)
                )
                continue
            # When a KeyError occurs here, we still want to continue checking the rest
            # A KeyError is only expected if the corresponding group does not exist
            try:
                problematic_objects.update(server_in_group_errors(lo, role, members[group_dn], group_dn))
            except KeyError:  # occurs if group_dn did not exist
                pass
            try:
                problematic_objects.update(
                    server_in_group_errors(lo, role, members[global_group], global_group)
                )
            except KeyError:  # occurs if global_group did not exist
                continue
    return problematic_objects


def check_all(school=None, user_dn=None):
    # type: (Optional[str], Optional[str]) ->  Dict[str, Dict[str, List[str]]]
    user_check = UserCheck()
    users_from_ldap = user_check.get_users_from_ldap(school, user_dn)
    user_problematic_objects = {}  # type: Dict[str, List[str]]
    for dn, attrs in users_from_ldap:
        user_issues = user_check.check_user(dn, attrs)
        if user_issues:
            user_problematic_objects[dn] = user_issues
    group_problematic_objects = check_mandatory_groups_exist(school)
    container_problematic_objects = check_containers(school)
    share_problematic_objects = check_shares(school)
    server_group_problematic_objects = check_server_group_membership(school)

    all_issues = {
        "users": user_problematic_objects,
        "groups": group_problematic_objects,
        "shares": share_problematic_objects,
        "containers": container_problematic_objects,
        "server_groups": server_group_problematic_objects,
    }

    return all_issues
