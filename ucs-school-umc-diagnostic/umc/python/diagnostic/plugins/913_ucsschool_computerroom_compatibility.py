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
# This module checks if the UCS@school computer rooms in UCS@school 5.0 are configured to Veyon

import univention.admin.uldap
from ucsschool.lib.models.group import ComputerRoom
from ucsschool.lib.models.school import School
from ucsschool.lib.models.utils import ucr
from univention.lib.i18n import Translation
from univention.management.console.modules.diagnostic import Warning

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school computer rooms without Veyon backend.")
description = "\n".join(
    [
        _("UCS@school computer rooms in UCS@school 5.0 must be configured to have the Veyon backend."),
        _(
            "Using them in the UMC-Module Computer room and the UMC-Module Exams is not possible in "
            "UCS@school 5.0."
        ),
    ]
)


def run(_umc_instance):
    lo, po = univention.admin.uldap.getMachineConnection()
    ucs5_replica_dns = lo.searchDn(
        filter="(&(univentionServerRole=slave)(univentionOperatingSystemVersion=5.*))"
    )

    problematic_objects = []
    for school in School.get_all(lo):
        is_ucs_5_school_replica = any(
            replica_dn in ucs5_replica_dns for replica_dn in school.educational_servers
        )
        if is_ucs_5_school_replica or ucr.is_true("ucsschool/singlemaster", False):
            rooms = ComputerRoom.get_all(lo, school.name)
            italc_room_dns = [room.dn for room in rooms if not room.veyon_backend]
            problematic_objects.extend(italc_room_dns)

    if problematic_objects:
        details = "\n\n" + _(
            "The following computer rooms are still configured to use the iTALC backend:\n"
        )
        for dn in problematic_objects:
            details += "\n"
            details += "  {}".format(dn)
        details += "\n" + _("\nPlease visit https://help.univention.com/t/16937 for more information.")
        raise Warning(description + details)


if __name__ == "__main__":
    run(None)
