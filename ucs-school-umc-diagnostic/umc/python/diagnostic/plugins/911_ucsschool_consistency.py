#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2019-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
# This module checks the consistency of all users, shares, groups and containers

from __future__ import absolute_import

from typing import Dict, List  # noqa: F401

from ucsschool.lib.consistency import check_all
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
    res = check_all()  # type: Dict[str, Dict[str, List[str]]]
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
    if any(res.values()):
        raise Warning(description + details)


if __name__ == "__main__":
    run(None)
