#!/usr/bin/python3
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
# This module reads the sourceUID and recordUID of all users and verifies that their combinations are
# different

from __future__ import absolute_import

from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

try:
    from typing import Dict, Set  # noqa: F401
except ImportError:
    pass

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
    if server_role != DC_MASTER and server_role != DC_BACKUP:
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
                    "has same ucsschoolSourceUID and ucsschoolRecordUID as {!r}: {!r}{!r}".format(
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
