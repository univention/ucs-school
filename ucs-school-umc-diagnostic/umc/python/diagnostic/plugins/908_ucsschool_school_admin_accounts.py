#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# Copyright 2019-2023 Univention GmbH
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
#
# This module checks if the UCS@school admin accounts are correctly configured:
# - get all user objects with an objectclass ucsschoolAdministrator
# - check if this user is member of admins-school group for each school it is registered as an
#   ucsschoolAdministrator
# - check that each member of an admins-school group is a ucsschoolAdministrator

from __future__ import absolute_import

from typing import Dict, List, Tuple, Union  # noqa: F401

from ucsschool.lib.roles import get_role_info, role_school_admin
from univention.lib.i18n import Translation
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import access, getAdminConnection  # noqa: F401

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school Check admin accounts")
description = "\n".join(
    [
        _("UCS@school Administrators are configured with an objectclass 'ucsschoolAdministrator'."),
        _("An administrator of a school should be a member of the respective admins-school group."),
    ]
)

USER_FILTER = "(&(univentionObjectType=users/user)(objectClass=ucsschoolAdministrator))"
GROUP_FILTER = "(&(univentionObjectType=groups/group)(cn=admins-*))"

NON_ADMIN_GROUP_MEMBER_WARN_STR = "non-admin group member"
MISSING_GROUP_WARN_STR = "missing group"
FORBIDDEN_GROUPS_WARN_STR = "forbidden group"


def is_forbidden_group(grp_school, admin_schools, admin_dn, grp_unique_mems):
    # type: (str, List[str], str, List[str]) -> bool
    """
    If the admin is listed in the admin group of a school the
    corresponding school must be part of its schools.
    """
    return grp_school not in admin_schools and admin_dn in grp_unique_mems


def get_forbidden_group_dns(admin, groups):
    # type: (Dict[str, Union[str, List[str]]], List[Tuple[str, Dict[str, List[bytes]]]]) -> List[str]
    forbidden = []
    for dn, attrs in groups:
        if is_forbidden_group(
            attrs["ucsschoolSchool"][0].decode("UTF-8"),
            admin["schools"],
            admin["dn"].encode("UTF-8"),
            attrs.get("uniqueMember", []),
        ):
            forbidden.append(dn)
    return forbidden


def make_warning_message(problem_dict, problem_desc):
    # type: (Dict[str, List[str]], str) -> str
    details = "\n\n" + _("The following {} problems were detected:".format(problem_desc))  # noqa: INT002
    for dn, problems in problem_dict.items():
        details += "\n\n  {}".format(dn)
        for problem in problems:
            details += "\n&nbsp;&nbsp;&nbsp;- {}".format(problem)
    return description + details


def search_admin_objects(lo, user_filter):
    # type: (access, str) -> Tuple[List[Dict[str, Union[str, List[str]]]], List[str]]
    """Searches for admin objects with object class ucsschoolAdministrator"""
    admins = []  # type: List[Dict[str, Union[str, List[str]]]]
    admin_dns = []  # type: List[str]
    for dn, attr in lo.search(filter=user_filter, attr=["ucsschoolSchool", "ucsschoolRole"]):
        admin_dns.append(dn)
        try:
            admin = {
                "dn": dn,
                "schools": [x.decode("UTF-8") for x in attr["ucsschoolSchool"]],
                "roles": [x.decode("UTF-8") for x in attr["ucsschoolRole"]],
            }
            admins.append(admin)
        except KeyError:
            continue
    return admins, admin_dns


def get_admin_schools(admin):
    # type: (Dict[str, List[str]]) -> List[str]
    """Retrieves the school names of the admin from its role property."""
    return [get_role_info(role)[2] for role in admin["roles"] if role_school_admin in role]


def is_missing_group(group_attrs, admin_dn, school):
    # type: (Dict[str, List[bytes]], str, str) -> bool
    """
    Returns true if the group's ucsschoolSchool property is the school of admin,
    but admin is not registered in the group.
    """
    return group_attrs["ucsschoolSchool"][0].decode("UTF-8") == school and admin_dn.encode(
        "UTF-8"
    ) not in group_attrs.get("uniqueMember", [])


def get_missing_group_dns(admin, groups):
    # type: (Dict[str, Union[str, List[str]]], List[str]) -> List[str]
    missing = []
    for school in get_admin_schools(admin):
        for dn, attrs in groups:
            if is_missing_group(attrs, admin["dn"], school):
                missing.append(dn)
    return missing


def record_non_admin_group_members(admin_dns, groups):
    # type: (List[str], List[str]) -> Dict[str, List[str]]
    """
    Checks whether each group member is a ucsschoolAdministrator and
    records and returns a problem description correspondingly.
    """
    detected_non_admin_group_members = {}  # type: Dict[str, List[str]]
    for dn, attr in groups:
        for member in attr.get("uniqueMember", []):
            member = member.decode("UTF-8")
            if member not in admin_dns:
                detected_non_admin_group_members.setdefault(member, []).append(
                    _(
                        "is member of group {} but is not registered as a "  # noqa: INT002
                        "ucsschoolAdministrator.".format(dn)
                    )
                )
    return detected_non_admin_group_members


def run(_umc_instance):
    detected_missing_group_dns = {}  # type: Dict[str, List[str]]
    detected_forbidden_group_dns = {}  # type: Dict[str, List[str]]
    lo = getAdminConnection()
    admins, admin_dns = search_admin_objects(lo, USER_FILTER)
    groups = lo.search(filter=GROUP_FILTER, attr=["uniqueMember", "ucsschoolSchool"])
    detected_non_admin_group_members = record_non_admin_group_members(admin_dns, groups)
    # check if found admins are member in corresponding admins-ou group
    for admin in admins:
        missing_group_dns = get_missing_group_dns(admin, groups)
        forbidden_group_dns = get_forbidden_group_dns(admin, groups)
        if missing_group_dns:
            detected_missing_group_dns.setdefault(admin["dn"], []).append(
                _(
                    "is registered as admin but no member of the following groups: {}".format(  # noqa: INT002
                        missing_group_dns
                    )
                )
            )
        if forbidden_group_dns:
            detected_forbidden_group_dns.setdefault(admin["dn"], []).append(
                _(
                    "should not be member of the following groups "  # noqa: INT002
                    "(missing {} role): {}".format(role_school_admin, forbidden_group_dns)
                )
            )
    warn_msg = ""
    if detected_non_admin_group_members:
        warn_msg += make_warning_message(
            detected_non_admin_group_members, NON_ADMIN_GROUP_MEMBER_WARN_STR
        )
    if detected_missing_group_dns:
        warn_msg += make_warning_message(detected_missing_group_dns, MISSING_GROUP_WARN_STR)
    if detected_forbidden_group_dns:
        warn_msg += make_warning_message(detected_forbidden_group_dns, FORBIDDEN_GROUPS_WARN_STR)
    if warn_msg:
        raise Warning(warn_msg)


if __name__ == "__main__":
    run(None)
