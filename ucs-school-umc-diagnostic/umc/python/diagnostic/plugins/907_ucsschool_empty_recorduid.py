#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2019-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
# This module searches users listed on the LDAP which have a sourceUID but no recordUID set.

from __future__ import absolute_import

from typing import Dict, Set  # noqa: F401

from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school Empty RecordUIDs")
description = "\n".join(
    [
        _(
            "In a UCS@school domain that uses the UCS@school import, all users that should be "
            "considered for imports must have a unique recordUID-sourceUID combination."
        ),
        _(
            "Having an empty recordUID is theoretically OK, but will most likely lead to problems in "
            "the future and the user may not be found by the import."
        ),
    ]
)


UCSSCHOOLSOURCEUID = "ucsschoolSourceUID"
DC_MASTER = "domaincontroller_master"
DC_BACKUP = "domaincontroller_backup"


def run(_umc_instance):
    server_role = ucr.get("server/role")
    if server_role not in (DC_MASTER, DC_BACKUP):
        return

    problematic_objects = {}  # type: Dict[str, Set[str]]
    lo = getAdminConnection()
    search_filter = "(&(ucsschoolSourceUID=*)(!(ucsschoolRecordUID=*)))"
    for dn in lo.searchDn(filter=search_filter):
        problematic_objects.setdefault(dn, []).append(
            _("has ucsschoolSourceUID but no ucsschoolRecordUID set.")
        )

    if problematic_objects:
        details = "\n\n" + _("The following problems were found: ")
        for dn, problems in problematic_objects.items():
            details += "\n\n  {}".format(dn)
            for problem in problems:
                details += "\n&nbsp;&nbsp;&nbsp;- {}".format(problem)
        raise Warning(description + details)


if __name__ == "__main__":
    run(None)
