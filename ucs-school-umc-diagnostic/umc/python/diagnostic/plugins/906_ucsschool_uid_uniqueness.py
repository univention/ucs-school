#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# Copyright 2019-2020 Univention GmbH
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
# This module reads the sourceUID and recordUID of all users and verifies that their combinations are different

from __future__ import absolute_import

from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Critical
from univention.uldap import getAdminConnection

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school UID Uniqueness")
description = "\n".join(
    [
        _(
            "Each user registered on the LDAP must be clearly identifiable by a unique combination of a sourceUID and recordUID."
        ),
        _(
            "If multiple users have the same combination of those UID's, users may not be found or wrond user objects could get modified."
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
    lo = getAdminConnection()
    all_ids = {}  # Structure: {sourceUID: {recordUID: dn}}
    for dn, attrs in lo.search(
        filter="ucsschoolSourceUID=*", attr=[UCSSCHOOLSOURCEUID, UCSSCHOOLRECORDUID]
    ):
        try:
            other_dn = all_ids[attrs[UCSSCHOOLSOURCEUID][0]][attrs[UCSSCHOOLRECORDUID][0]]
            raise Critical("User with DN={!r} has same suid+ruid as {!r}".format(dn, other_dn))
        except KeyError:
            all_ids.setdefault(attrs[UCSSCHOOLSOURCEUID][0], {})[attrs[UCSSCHOOLRECORDUID][0]] = dn


if __name__ == "__main__":
    run(None)
