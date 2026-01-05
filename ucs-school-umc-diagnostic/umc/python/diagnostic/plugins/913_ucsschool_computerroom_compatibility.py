#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2019-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
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
