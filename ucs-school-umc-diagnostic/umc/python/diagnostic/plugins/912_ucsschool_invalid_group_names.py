#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2019-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
# This module checks if the UCS@school groups names do not include whitespaces.

import re

from ucsschool.lib.models.school import School
from ucsschool.lib.models.share import ClassShare, WorkGroupShare
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.admin.uldap import getAdminConnection
from univention.lib.i18n import Translation
from univention.management.console.modules.diagnostic import Warning

re_name_with_multiple_whitespaces = re.compile(r"\s{2,}")

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school Check Groups without consecutive whitespaces")
description = "\n".join(
    [
        _("UCS@school groups must not contain consecutive whitespaces."),
        _("This will lead to errors when using their group shares."),
    ]
)


def run(_umc_instance):
    problematic_objects = []
    lo, _po = getAdminConnection()
    for school in School.get_all(lo):
        search_base = SchoolSearchBase([school.name])
        for cs in ClassShare.get_all(lo, school.name):
            if re_name_with_multiple_whitespaces.search(cs.name):
                group_dn = "cn={},{}".format(cs.name, search_base.classes)
                problematic_objects.append((cs.dn, group_dn))

        for ws in WorkGroupShare.get_all(lo, school.name):
            if re_name_with_multiple_whitespaces.search(ws.name):
                group_dn = "cn={},{}".format(ws.name, search_base.workgroups)
                problematic_objects.append((ws.dn, group_dn))

    if problematic_objects:
        details = "\n\n" + _("The following group shares have problematic names.")
        details += "\n" + _("Rename the corresponding groups, to solve this issue.")
        details += "\n" + _("Please visit https://help.univention.com/t/18597 before doing so.")
        for share_dn, group_dn in problematic_objects:
            details += "\n"
            details += "\n  share: {}".format(share_dn)
            details += "\n  group: {}".format(group_dn)

        raise Warning(description + details)


if __name__ == "__main__":
    run(None)
