#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2019-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
# This module checks the UCS@school OU objects:
# - only OUs with correct objectclass ("ucsschoolOrganizationalUnit") are checked
# - is ucsschoolRole set?
# - is ucsschoolRole set to "school:school:$OU"?
# - is a displayName set?
# - is a HomeShareFileServer and a ClassShareFileServer set?
# - is a HomeShareFileServer and a ClassShareFileServer (not) set to the Primary Node in multi/single
#   server environment?
from __future__ import absolute_import

from typing import Dict, List  # noqa: F401

from ldap import NO_SUCH_OBJECT

from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school OU Consistency")
description = "\n".join(
    [
        _(
            "UCS@school stores information about schools within the LDAP objects. One of these objects "
            "is the school OU object."
        ),
        _("Inconsistencies in these OU object can trigger erratic behaviour of the UCS@school import."),
    ]
)


def run(_umc_instance):
    if ucr.get("server/role") != "domaincontroller_master":
        return

    problematic_objects = {}  # type: Dict[str, List[str]]

    lo = getAdminConnection()

    ou_list = lo.search(filter="ou=*", base=ucr.get("ldap/base"), scope="one")
    for ou_dn, ou_attrs in ou_list:
        if b"ucsschoolOrganizationalUnit" not in ou_attrs.get("objectClass", []):
            continue

        ucsschoolRoles = ou_attrs.get("ucsschoolRole", [])
        if not ucsschoolRoles:
            problematic_objects.setdefault(ou_dn, []).append(_("ucsschoolRole is not set"))
        if ucsschoolRoles and not any(
            x.decode("UTF-8") == "school:school:{}".format(ou_attrs.get("ou")[0].decode("UTF-8"))
            for x in ucsschoolRoles
        ):
            problematic_objects.setdefault(ou_dn, []).append(
                _('ucsschoolRole "school:school:{0}" not found').format(
                    ou_attrs.get("ou")[0].decode("UTF-8")
                )
            )

        if not ou_attrs.get("displayName", [b""])[0]:
            problematic_objects.setdefault(ou_dn, []).append(_("displayName is not set"))

        for attr_name in ("ucsschoolHomeShareFileServer", "ucsschoolClassShareFileServer"):
            value = ou_attrs.get(attr_name, [b""])[0].decode("UTF-8")
            if not value:
                problematic_objects.setdefault(ou_dn, []).append(_("{0} is not set").format(attr_name))
            try:
                lo.searchDn(base=value, scope="base")
            except NO_SUCH_OBJECT:
                problematic_objects.setdefault(ou_dn, []).append(
                    _("{0} contains invalid value: {1!r}").format(attr_name, value)
                )
            if ucr.is_true("ucsschool/singlemaster", False) and value != ucr.get(
                "ldap/hostdn"
            ):  # WARNING: this line expects that the check is performed on the Primary Directory Node!
                problematic_objects.setdefault(ou_dn, []).append(
                    _(
                        "{0} is not set to Primary Directory Node in a UCS@school single server "
                        "environment"
                    ).format(attr_name)
                )
            if not ucr.is_true("ucsschool/singlemaster", False) and value == ucr.get(
                "ldap/hostdn"
            ):  # WARNING: this line expects that the check is performed on the Primary Directory Node!
                problematic_objects.setdefault(ou_dn, []).append(
                    _(
                        "{0} is set to Primary Directory Node in a UCS@school multi server environment"
                    ).format(attr_name)
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
