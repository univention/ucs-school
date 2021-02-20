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
# This module checks the consistency of all users, shares, groups and containers

from __future__ import absolute_import

from ucsschool.lib.models.consistency import check_all
from univention.lib.i18n import Translation
from univention.management.console.modules.diagnostic import Warning

_ = Translation("ucs-school-umc-diagnostic").translate
title = _("UCS@school Consistency Check")
description = "\n".join(
    [
        _("UCS@school requires its LDAP objects to follow certain rules."),
        _("Inconsistencies in these objects can trigger erratic behaviour."),
    ]
)

help_groups_link = "https://help.univention.com/t/ucs-school-work-groups-and-school-classes/16925"
help_shares_link = "https://help.univention.com/t/an-overview-of-ucs-school-shares/17139"
help_users_link = "https://help.univention.com/t/how-a-ucs-school-user-should-look-like/15630"

help_links = {"groups": help_groups_link, "shares": help_shares_link, "users": help_users_link}


def run(_umc_instance):
    res = check_all()
    details = ""
    for check, issues in res.items():
        if issues:
            details += "\n\n" + "~~~ The following issues concern {} ~~~".format(check)
            for dn, problems in issues.items():
                details += "\n\n  {}".format(dn)
                for problem in problems:
                    details += "\n&nbsp;&nbsp;&nbsp;- {}".format(problem)
            try:
                details += "\n\n" + "For help please visit {}".format(help_links[check])
            except KeyError:
                pass
    raise Warning(description + details)


if __name__ == "__main__":
    run(None)
