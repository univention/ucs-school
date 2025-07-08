#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2019-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
# This module reads the sourceUID and recordUID of all users and verifies that their combinations are
# different

from __future__ import absolute_import

from typing import Dict, Set  # noqa: F401

from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school UID Uniqueness")
description = "\n".join(
    [
        _(
            "In a UCS@school domain that uses the UCS@school import, all users that should be "
            "considered for imports must have a unique recordUID-sourceUID combination."
        ),
        _(
            "If multiple users have the same combination of those UID's, users may not be found or "
            "wrong user objects could get modified."
        ),
    ]
)


UCSSCHOOLSOURCEUID = "ucsschoolSourceUID"
UCSSCHOOLRECORDUID = "ucsschoolRecordUID"
DC_MASTER = "domaincontroller_master"
DC_BACKUP = "domaincontroller_backup"


def run(_umc_instance):
    server_role = ucr.get("server/role")
    if server_role not in (DC_MASTER, DC_BACKUP):
        return

    problematic_objects = {}  # type: Dict[str, Set[str]]
    lo = getAdminConnection()
    all_ids = {}  # Structure: {sourceUID: {recordUID: dn}}
    search_filter = "(&(ucsschoolSourceUID=*)(ucsschoolRecordUID=*))"
    for dn, attrs in lo.search(filter=search_filter, attr=[UCSSCHOOLSOURCEUID, UCSSCHOOLRECORDUID]):
        try:
            source_uid = attrs[UCSSCHOOLSOURCEUID][0].decode("UTF-8")
            record_uid = attrs[UCSSCHOOLRECORDUID][0].decode("UTF-8")
            other_dn = all_ids[source_uid][record_uid]
            # if this line is reached, a suid-ruid duplicate was found
            problematic_objects.setdefault(dn, []).append(
                _(
                    "has same ucsschoolSourceUID and ucsschoolRecordUID as {!r}: {!r}{!r}".format(  # noqa: INT002
                        other_dn, source_uid, record_uid
                    )
                )
            )
        except KeyError:
            all_ids.setdefault(source_uid, {})[record_uid] = dn

    if problematic_objects:
        details = "\n\n" + _("The following problems were found: ")
        for dn, problems in problematic_objects.items():
            details += "\n\n  {}".format(dn)
            for problem in problems:
                details += "\n&nbsp;&nbsp;&nbsp;- {}".format(problem)
        raise Warning(description + details)


if __name__ == "__main__":
    run(None)
