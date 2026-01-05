#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2019-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
# This module checks the computer objects within each school:
# if OC ucsschoolComputer or attribute ucsschoolRole is missing, a critical error is shown
# Via a "fix" button, the faulty object can be corrected.

from __future__ import absolute_import

from typing import TYPE_CHECKING, Set  # noqa: F401

import ldap
from ldap.filter import filter_format

from ucsschool.lib.models.computer import AnyComputer
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_ip_computer,
    role_linux_computer,
    role_mac_computer,
    role_ubuntu_computer,
    role_win_computer,
)
from univention.admin.uexceptions import ldapError
from univention.admin.uldap import getAdminConnection
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import MODULE, Critical, ProblemFixed

if TYPE_CHECKING:
    from univention.admin.uldap import access  # noqa: F401

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school School Computer Consistency")
description = "\n".join(
    [
        _(
            "Windows/Linux/IPManagedClient/Ubuntu computer objects below a UCS@school OU should "
            "contain the objectclass <i>ucsschoolComputer</i> and the attribute <i>ucsschoolRole</i>."
        ),
    ]
)


def find_all_problematic_objects(lo):  # type: (access) -> Set[str]
    problematic_objects = set()
    for obj_type in (
        "computers/windows",
        "computers/macos",
        "computers/ipmanagedclient",
        "computers/linux",
        "computers/ubuntu",
    ):
        MODULE.process("Looking for {}...".format(obj_type))
        obj_list = lo.search(filter=filter_format("univentionObjectType=%s", (obj_type,)))
        for obj_dn, obj_attrs in obj_list:
            MODULE.process("Found {}...".format(obj_dn))
            if b"ucsschoolComputer" not in obj_attrs.get("objectClass", []):
                problematic_objects.add(obj_dn)

            if "ucsschoolRole" not in obj_attrs:
                problematic_objects.add(obj_dn)
    return problematic_objects


def run(_umc_instance):
    if ucr.get("server/role") != "domaincontroller_master":
        return

    lo, po = getAdminConnection()
    problematic_objects = find_all_problematic_objects(lo)

    if problematic_objects:
        details = "\n\n" + _(
            "The following host objects do not contain all the necessary LDAP attributes for UCS@school:"
        )
        for dn in problematic_objects:
            details += "\n  {}".format(dn)
        raise Critical(
            description + details,
            buttons=[{"action": "fix_computers", "label": _("Fix computer objects")}],
        )


def fix_computers(_umc_instance):
    lo, po = getAdminConnection()
    problematic_objects = find_all_problematic_objects(lo)
    for dn in problematic_objects:
        MODULE.process("Fixing {}".format(dn))
        attrs = lo.get(dn)
        ml = []
        old_val = attrs.get("objectClass", [])
        MODULE.process("old_val = {!r}".format(old_val))
        if b"ucsschoolComputer" not in old_val:
            ml.append(["objectClass", old_val, old_val + [b"ucsschoolComputer"]])
        MODULE.info("old_val = {!r}".format(attrs.get("ucsschoolRole")))
        if "ucsschoolRole" not in attrs:
            school = AnyComputer.get_school_from_dn(dn)
            role = {
                "computers/windows": create_ucsschool_role_string(role_win_computer, school),
                "computers/macos": create_ucsschool_role_string(role_mac_computer, school),
                "computers/ipmanagedclient": create_ucsschool_role_string(role_ip_computer, school),
                "computers/linux": create_ucsschool_role_string(role_linux_computer, school),
                "computers/ubuntu": create_ucsschool_role_string(role_ubuntu_computer, school),
            }.get(attrs.get("univentionObjectType", [b""])[0].decode("UTF-8"))
            MODULE.info("role = {!r}".format(role))
            if role is not None:
                ml.append(["ucsschoolRole", [], [role.encode("UTF-8")]])
        MODULE.info("ml={!r}".format(ml))
        if ml:
            try:
                lo.modify(dn, ml)
            except (ldap.LDAPError, ldapError) as exc:
                MODULE.error("Error modifying {}: {}\n{!r}".format(dn, exc, ml))
                raise Critical(_("Failed to modify object {!r}: {}").format(dn, exc))
    problematic_objects = set()
    raise ProblemFixed(buttons=[])


actions = {
    "fix_computers": fix_computers,
}


if __name__ == "__main__":
    run(None)
