#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2020-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""This module checks the consistency of UCS@school users, shares and groups"""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

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
    role_legal_guardian,
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

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType


# Each entry: (role_constant, school_group_cn_template, global_group_cn).
# The school template receives the OU-escaped name via .format().
_SCHOOL_SERVER_CONFIGS = (
    (role_dc_slave_edu, "OU{}-DC-Edukativnetz", "DC-Edukativnetz"),
    (role_dc_slave_admin, "OU{}-DC-Verwaltungsnetz", "DC-Verwaltungsnetz"),
    (role_memberserver_edu, "OU{}-Member-Edukativnetz", "Member-Edukativnetz"),
    (role_memberserver_admin, "OU{}-Member-Verwaltungsnetz", "Member-Verwaltungsnetz"),
)
UCR_LDAP_BASE = "ldap/base"


class UserCheck(object):
    def __init__(self):
        ucr = ConfigRegistry()
        ucr.load()
        ldap_base = ucr.get(UCR_LDAP_BASE)
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
            "ucsschoolLegalGuardian": role_legal_guardian,
        }

        self.domain_users_ou: dict[str, str] = {}
        self.students_ou: dict[str, str] = {}
        self.teachers_ou: dict[str, str] = {}
        self.staff_ou: dict[str, str] = {}
        self.admins_ou: dict[str, str] = {}

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

    def check_allowed_membership(
        self, group_dn: str, students: bool = False, teachers: bool = False, staff: bool = False
    ) -> list[str]:
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
        self, school: str | None, users: list[str] | None
    ) -> list[tuple[str, dict[str, list[bytes]]]]:
        if not users and not school:
            return self._fetch_all_ucsschool_users()

        ldap_user_list = self._fetch_users_by_dns(users)

        if school:
            school_users = self._fetch_users_by_school(school)
            ldap_user_list.extend(u for u in school_users if u not in ldap_user_list)

        return ldap_user_list

    def _fetch_users_by_dns(
        self, user_dns: list[str] | None
    ) -> list[tuple[str, dict[str, list[bytes]]]]:
        if not user_dns:
            return []
        result = []
        for dn in user_dns:
            try:
                result.append(self.lo.search(base=dn)[0])
            except noObject:
                print("User with DN {} does not exist.".format(dn))
                sys.exit()
            except INVALID_DN_SYNTAX:
                print("DN {} has invalid syntax.".format(dn))
                sys.exit(1)
        return result

    def _fetch_users_by_school(self, school: str) -> list[tuple[str, dict[str, list[bytes]]]]:
        return self.lo.search(
            filter=filter_format("(&(univentionObjectType=users/user)(ucsschoolSchool=%s))", (school,))
        )

    def _fetch_all_ucsschool_users(
        self,
    ) -> list[tuple[str, dict[str, list[bytes]]]]:
        return self.lo.search(filter="(&(univentionObjectType=users/user)(objectClass=ucsschoolType))")

    def check_user(self, dn: str, attrs: dict[str, list[bytes]]) -> list[str]:
        issues: list[str] = []

        try:
            user_obj = User.from_dn(dn, None, self.lo)
        except WrongObjectType as exc:
            issues.append("Expected a user object, but is not: {}".format(exc))
            return issues
        except permissionDenied as exc:
            issues.append("Could not access this user  {}".format(exc))
            return issues

        user_obj_classes = [x.decode("UTF-8") for x in attrs.get("objectClass", [])]
        user_roles = self._roles_for_object_classes(user_obj_classes, issues)
        self._check_ucsschool_roles(user_obj, user_roles, issues)

        users_group_dns = self._user_group_dns(dn)
        if not self._schools_exist(user_obj, issues):
            return issues

        is_student = user_obj.is_student(self.lo)
        is_admin = user_obj.is_administrator(self.lo)
        is_teacher = user_obj.is_teacher(self.lo)
        is_staff = user_obj.is_staff(self.lo)

        self._check_domain_users_membership(user_obj, users_group_dns, issues)
        self._check_student_membership(user_obj, users_group_dns, is_student, issues)
        self._check_admin_membership(user_obj, users_group_dns, is_admin, issues)
        self._check_teacher_staff_membership(user_obj, users_group_dns, is_teacher, is_staff, issues)
        self._check_school_classes_membership(user_obj, is_student, issues)
        self._check_ucsschool_school_attribute(user_obj, attrs, issues)

        return issues

    def _roles_for_object_classes(self, user_obj_classes: list[str], issues: list[str]) -> list[str]:
        if not any(cls in user_obj_classes for cls in self.ucsschool_obj_classes):
            issues.append("User has no UCS@school Object Class set.")

        user_roles = [
            self.ucsschool_obj_classes[cls]
            for cls in user_obj_classes
            if cls in self.ucsschool_obj_classes
        ]

        # Exam users have objectClass ucsschoolStudent but only require exam_user role.
        if self.ucsschool_obj_classes["ucsschoolExam"] in user_roles:
            try:
                user_roles.remove(self.ucsschool_obj_classes["ucsschoolStudent"])
            except ValueError:
                pass

        return user_roles

    def _check_ucsschool_roles(self, user_obj: User, user_roles: list[str], issues: list[str]) -> None:
        ucsschool_roles = {r.lower() for r in user_obj.ucsschool_roles}
        for role in user_roles:
            for school in user_obj.schools:
                ucsschool_role_string = create_ucsschool_role_string(role, school)
                if ucsschool_role_string.lower() not in ucsschool_roles:
                    issues.append("User does not have UCS@school Role {}".format(ucsschool_role_string))

    def _user_group_dns(self, dn: str) -> list[str]:
        return [_dn.lower() for _dn in self.lo.searchDn(filter="uniqueMember={}".format(dn))]

    def _schools_exist(self, user_obj: User, issues: list[str]) -> bool:
        for school in user_obj.schools:
            if school not in self.all_schools:
                issues.append(
                    "User is member of school {}, which does not exist anymore. "
                    "Further tests on this user cannot be performed.".format(school)
                )
                return False
        return True

    def _check_domain_users_membership(
        self, user_obj: User, users_group_dns: list[str], issues: list[str]
    ) -> None:
        for school in user_obj.schools:
            if self.domain_users_ou[school].lower() not in users_group_dns:
                issues.append("Not member of group {}".format(self.domain_users_ou[school]))

    def _check_student_membership(
        self, user_obj: User, users_group_dns: list[str], is_student: bool, issues: list[str]
    ) -> None:
        if not is_student:
            return

        for school in user_obj.schools:
            if self.students_ou[school].lower() not in users_group_dns:
                issues.append("Not member of group {}".format(self.students_ou[school]))
        for group_dn in users_group_dns:
            issues += self.check_allowed_membership(group_dn, students=True)

    def _check_admin_membership(
        self, user_obj: User, users_group_dns: list[str], is_admin: bool, issues: list[str]
    ) -> None:
        if not is_admin:
            return

        for ou in user_obj.schools:
            if self.admins_ou[ou].lower() not in users_group_dns:
                issues.append("Not member of group {}".format(self.admins_ou[ou]))
        for group_dn in users_group_dns:
            if self.students_regex.match(group_dn):
                issues.append("Admin should not be in a students group {}".format(group_dn))

    def _check_teacher_staff_membership(
        self,
        user_obj: User,
        users_group_dns: list[str],
        is_teacher: bool,
        is_staff: bool,
        issues: list[str],
    ) -> None:
        if not is_teacher and not is_staff:
            return

        for ou in user_obj.schools:
            if is_teacher and self.teachers_ou[ou].lower() not in users_group_dns:
                issues.append("Not member of group {}".format(self.teachers_ou[ou]))
            if is_staff and self.staff_ou[ou].lower() not in users_group_dns:
                issues.append("Not member of group {}".format(self.staff_ou[ou]))

        for group_dn in users_group_dns:
            issues += self.check_allowed_membership(group_dn, teachers=is_teacher, staff=is_staff)

    def _check_school_classes_membership(
        self, user_obj: User, is_student: bool, issues: list[str]
    ) -> None:
        if not user_obj.school_classes and is_student:
            issues.append("Is not a member of any school class.")

    def _check_ucsschool_school_attribute(
        self, user_obj: User, attrs: dict[str, list[bytes]], issues: list[str]
    ) -> None:
        if "ucsschoolSchool" not in attrs:
            issues.append(
                "User object is an inconsistent UCS@school user. "
                "Missing LDAP attribute: ucsschoolSchool."
            )
            return

        for ou in user_obj.school_classes:
            if ou.encode("UTF-8") not in attrs["ucsschoolSchool"]:
                issues.append(
                    "Is member of class {} but LDAP attribute ucsschoolSchool "
                    "is not correspondingly set.".format(user_obj.school_classes[ou][0])
                )


def check_mandatory_groups_exist(school: str | None = None) -> dict[str, list[str]]:
    ucr = ConfigRegistry()
    ucr.load()
    ldap_base = ucr.get(UCR_LDAP_BASE)

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
            search_base.admins_group,
        ]
        for mandatory_group in mandatory_groups:
            try:
                lo.searchDn(base=mandatory_group)
            except noObject:
                issues.append("Mandatory group {} does not exist.".format(mandatory_group))

        if issues:
            problematic_objects[search_base.schoolDN] = issues
    return problematic_objects


def check_containers(school: str | None = None) -> dict[str, list[str]]:
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


def _ucsschool_role_filter(role_string: str, allow_wildcards: bool) -> str:
    f = filter_format("(ucsschoolRole=%s)", [role_string])
    if allow_wildcards:
        f = f.replace(escape_filter_chars("*"), "*")
    return f


def _check_orphan_shares(
    lo: LoType,
    role_group: str,
    role_share: str,
    school_filter: str,
    allow_wildcards: bool,
    missing_msg: str,
) -> dict[str, list[str]]:
    """Return shares whose corresponding group (class or work group) no longer exists."""
    group_role = create_ucsschool_role_string(role_group, school_filter)
    groups = {
        attrs["cn"][0].decode("UTF-8")
        for _dn, attrs in lo.search(filter=_ucsschool_role_filter(group_role, allow_wildcards))
    }
    share_role = create_ucsschool_role_string(role_share, school_filter)
    result: dict[str, list[str]] = {}
    for dn, attrs in lo.search(filter=_ucsschool_role_filter(share_role, allow_wildcards)):
        cn = attrs["cn"][0].decode("UTF-8")
        if cn not in groups:
            result[dn] = [missing_msg.format(cn)]
    return result


def _check_marktplatz_shares(lo: LoType, all_schools: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for ou in all_schools:
        search_base = SchoolSearchBase([ou])
        marktplatz_share = "cn=Marktplatz,cn=shares,{}".format(search_base.schoolDN)
        try:
            lo.search(base=marktplatz_share)
        except noObject:
            result[marktplatz_share] = ["The 'Marktplatz' share of school %r does not exist." % (ou,)]
    return result


def check_shares(school: str | None = None) -> dict[str, list[str]]:
    ucr = ConfigRegistry()
    ucr.load()
    lo, _ = getMachineConnection()

    if school:
        all_schools, school_filter, allow_wildcards = [school], school, False
    else:
        all_schools = [ou.name for ou in School.get_all(lo)]
        school_filter, allow_wildcards = "*", True

    result: dict[str, list[str]] = {}

    if ucr.is_true("ucsschool/import/generate/share/marktplatz", True):
        result.update(_check_marktplatz_shares(lo, all_schools))

    result.update(
        _check_orphan_shares(
            lo,
            role_school_class,
            role_school_class_share,
            school_filter,
            allow_wildcards,
            "Corresponding class {} is missing.",
        )
    )
    result.update(
        _check_orphan_shares(
            lo,
            role_workgroup,
            role_workgroup_share,
            school_filter,
            allow_wildcards,
            "Corresponding work group {} is missing.",
        )
    )
    return result


def _server_in_group_errors(
    lo: LoType, role: str, members: list[str], group_dn: str
) -> dict[str, list[str]]:
    problematic_objects = {}
    for dn, _attrs in lo.search(filter=filter_format("(ucsschoolRole=%s)", [role])):
        if dn not in members:
            problematic_objects.setdefault(dn, []).append("is not a member of group {}".format(group_dn))
    return problematic_objects


def _load_group_members(lo: LoType, group_dn: str) -> list[str] | None:
    """Returns list of member DNs, or None if the group does not exist."""
    try:
        return [x.decode("UTF-8") for x in lo.search(base=group_dn)[0][1]["uniqueMember"]]
    except KeyError:
        return []
    except noObject:
        return None


def _ucsschool_group_dn(cn: str, ldap_base: str) -> str:
    return f"cn={cn},cn=ucsschool,cn=groups,{ldap_base}"


def check_server_group_membership(school: str | None = None) -> dict[str, list[str]]:
    ucr = ConfigRegistry()
    ucr.load()
    ldap_base = ucr.get(UCR_LDAP_BASE)
    lo, _ = getMachineConnection()
    schools = [school] if school else [ou.name for ou in School.get_all(lo)]

    problematic_objects: dict[str, list[str]] = {}
    global_members: dict[str, list[str]] = {}

    for _, _, global_cn in _SCHOOL_SERVER_CONFIGS:
        global_dn = _ucsschool_group_dn(global_cn, ldap_base)
        result = _load_group_members(lo, global_dn)
        if result is None:
            problematic_objects.setdefault(global_dn, []).append(
                f"Memberships of group {global_dn} could not be checked. It does not exist."
            )
        else:
            global_members[global_dn] = result

    for ou in schools:
        for role_const, school_cn_template, global_cn in _SCHOOL_SERVER_CONFIGS:
            school_dn = _ucsschool_group_dn(school_cn_template.format(escape_dn_chars(ou)), ldap_base)
            global_dn = _ucsschool_group_dn(global_cn, ldap_base)
            role_str = create_ucsschool_role_string(role_const, ou)

            school_group_members = _load_group_members(lo, school_dn)
            if school_group_members is None:
                problematic_objects.setdefault(school_dn, []).append(
                    f"Memberships of group {school_dn} could not be checked. It does not exist."
                )
                continue

            problematic_objects.update(
                _server_in_group_errors(lo, role_str, school_group_members, school_dn)
            )
            if global_dn in global_members:
                problematic_objects.update(
                    _server_in_group_errors(lo, role_str, global_members[global_dn], global_dn)
                )

    return problematic_objects


def check_all(school: str | None = None, user_dn: str | None = None) -> dict[str, dict[str, list[str]]]:
    user_check = UserCheck()
    users_from_ldap = user_check.get_users_from_ldap(school, [user_dn] if user_dn else [])
    user_problematic_objects: dict[str, list[str]] = {}
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
