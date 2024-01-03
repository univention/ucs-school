#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# Copyright 2019-2024 Univention GmbH
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
# This module checks if the UCS@school groups names do not include whitespaces.

import re

from ucsschool.lib.models.school import School
from ucsschool.lib.models.share import ClassShare, WorkGroupShare
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.lib.i18n import Translation
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

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
    lo = getAdminConnection()
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
