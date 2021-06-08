#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# Copyright 2019-2021 Univention GmbH
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

from ucsschool.lib.roles import get_role_info, role_school_admin
from univention.lib.i18n import Translation
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

try:
    from typing import Dict, List
except ImportError:
    pass

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school Check admin accounts")
description = "\n".join(
    [
        _("UCS@school Administrators are configured with an objectclass 'ucsschoolAdministrator'."),
        _("An administrator of a school should be a member of the respective admins-school group."),
    ]
)


def run(_umc_instance):
    problematic_objects = {}  # type: Dict[str, List[str]]
    lo = getAdminConnection()

    user_filter = "(&(univentionObjectType=users/user)(objectClass=ucsschoolAdministrator))"

    # search for admin objects with object class ucsschoolAdministrator
    admins = []  # type: List[Dict[str, List[str]]]
    admins_dn = []
    for dn, attr in lo.search(filter=user_filter, attr=["ucsschoolSchool", "ucsschoolRole"]):
        admins_dn.append(dn)
        try:
            admin = {"dn": dn, "schools": attr["ucsschoolSchool"], "roles": attr["ucsschoolRole"]}
            admins.append(admin)
        except KeyError:
            continue

    group_filter = "(&(univentionObjectType=groups/group)(cn=admins-*))"
    groups = lo.search(filter=group_filter, attr=["uniqueMember", "ucsschoolSchool"])

    # check if each group member is a ucsschoolAdministrator
    for dn, attr in groups:
        for member in attr.get("uniqueMember", []):
            if member not in admins_dn:
                problematic_objects.setdefault(member, []).append(
                    _(
                        "is member of group {} but is not registered as a "
                        "ucsschoolAdministrator.".format(dn)
                    )
                )

    # check if found admins are member in corresponding admins-ou group
    for admin in admins:
        missing_group_dns = []
        forbidden_groups = []
        for role in admin["roles"]:
            if role_school_admin in role:
                school = get_role_info(role)[2]  # eg. "DEMOSCHOOL" from school_admin:school:DEMOSCHOOL
                for dn, attr in groups:
                    if attr["ucsschoolSchool"][0] == school:
                        if not admin["dn"] in attr.get("uniqueMember", []):
                            missing_group_dns.append(dn)
                    else:
                        if admin["dn"] in attr.get("uniqueMember", []):
                            forbidden_groups.append(dn)

        if missing_group_dns:
            problematic_objects.setdefault(admin["dn"], []).append(
                _(
                    "is registered as admin but no member of the following groups: {}".format(
                        missing_group_dns
                    )
                )
            )
        if forbidden_groups:
            problematic_objects.setdefault(admin["dn"], []).append(
                _(
                    "should not be member of the following groups "
                    "(missing school_admin role!): {}".format(forbidden_groups)
                )
            )

    if problematic_objects:
        details = "\n\n" + _("The following problems were found:")
        for dn, problems in problematic_objects.items():
            details += "\n\n  {}".format(dn)
            for problem in problems:
                details += "\n&nbsp;&nbsp;&nbsp;- {}".format(problem)
        raise Warning(description + details)


if __name__ == "__main__":
    run(None)
