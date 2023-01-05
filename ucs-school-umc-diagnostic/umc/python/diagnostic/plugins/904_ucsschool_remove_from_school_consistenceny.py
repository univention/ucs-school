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
# This module checks for all users with attribute ucsschoolRole set:
# if the user's ucsschoolSchool a subset of it's ucsschoolRoles
# and for all groups with ucsschoolRole=school_class:school:*
# whether all uniqueMembers are present in the school-group.

from __future__ import absolute_import

from typing import Dict, Set

from ucsschool.lib.roles import role_school_class
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

_ = Translation("ucs-school-umc-diagnostic").translate
title = _("UCS@school Group Consistency")
description = "\n".join(
    [
        _(
            "UCS@school: test for inconsistencies between class/working group memberships and school "
            "memberships."
        ),
    ]
)

UCSSCHOOLROLE = "ucsschoolRole"
UCSSCHOOLSCHOOL = "ucsschoolSchool"


def run(_umc_instance):
    if ucr.get("server/role") != "domaincontroller_master":
        return
    problematic_objects = {}  # type: Dict[str, Set[str]]
    lo = getAdminConnection()

    users = {}
    obj_list = lo.search(
        filter="(&(univentionObjectType=users/user)(ucsschoolRole=*))",
        attr=[UCSSCHOOLROLE, UCSSCHOOLSCHOOL],
    )
    for (obj_dn, obj_attrs) in obj_list:
        ucsschool_roles = obj_attrs.get(UCSSCHOOLROLE, [])
        roles = {role.decode("UTF-8").split(":")[-1] for role in ucsschool_roles if b":school:" in role}
        school = set(x.decode("UTF-8") for x in obj_attrs.get(UCSSCHOOLSCHOOL, []))
        if school != roles:
            problematic_objects.setdefault(obj_dn, []).append(
                _("{0} is not part of the school but in {1}").format(obj_dn, roles)
            )
        users[obj_dn] = school

    obj_list = None

    obj_list = lo.search(
        filter="(&(univentionObjectType=groups/group)(ucsschoolRole={0}:school:*))".format(
            role_school_class
        ),
        attr=[UCSSCHOOLROLE, "uniqueMember"],
    )
    for (obj_dn, obj_attrs) in obj_list:
        ums = obj_attrs.get("uniqueMember", [])
        grp_schools = {
            role.decode("UTF-8").split(":")[-1]
            for role in obj_attrs[UCSSCHOOLROLE]
            if b":school:" in role
        }
        for um in ums:
            um = um.decode("UTF-8")
            if um not in users:
                problematic_objects.setdefault(obj_dn, []).append(
                    _("{0} has no ucsschoolRole, but is in group").format(um)
                )
                continue
            if not (users[um] & grp_schools):
                problematic_objects.setdefault(obj_dn, []).append(
                    _("{0} is not part of the school {1}").format(um, grp_schools)
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
