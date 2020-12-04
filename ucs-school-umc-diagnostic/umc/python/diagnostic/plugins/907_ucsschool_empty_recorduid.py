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
# This module searches users listed on the LDAP which have a sourceUID but no recordUID set.

from __future__ import absolute_import

from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

try:
    from typing import Dict, Set
except ImportError:
    pass

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
    if server_role != DC_MASTER and server_role != DC_BACKUP:
        return

    problematic_objects = {}  # type: Dict[str, Set[str]]
    lo = getAdminConnection()
    search_filter = "(&(ucsschoolSourceUID=*)(!(ucsschoolRecordUID=*)))"
    for dn, attrs in lo.search(filter=search_filter, attr=[UCSSCHOOLSOURCEUID]):
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
