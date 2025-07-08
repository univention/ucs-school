#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2019-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
# This module checks the counter objects of the UCS@school import.
# - ucsschoolUsernameNextNumber is a integer
# - ucsschoolUsernameNextNumber is 2 or higher
# - ucsschoolUsernameNextNumber is higher than highest suffix number of user with same prefix

from __future__ import absolute_import

from typing import Dict, List  # noqa: F401

from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school Import Counter Consistency")
description = "\n".join(
    [
        _("UCS@school stores internal counters for the next free username or mail address."),
        _("Inconsistencies in these counters can trigger erratic behaviour of the UCS@school import."),
    ]
)


def run(_umc_instance):
    if ucr.get("server/role") != "domaincontroller_master":
        return

    problematic_objects = {}  # type: Dict[str, List[str]]

    lo = getAdminConnection()

    email_prefix2counter = {}  # type: Dict[str, int]
    user_prefix2counter = {}  # type: Dict[str, int]
    obj_list = lo.search(
        filter="(&(univentionObjectType=users/user)(ucsschoolRole=*))",
        attr=["uid", "mailPrimaryAddress"],
    )
    for _obj_dn, obj_attrs in obj_list:
        uid = obj_attrs.get("uid")[0].decode("UTF-8")
        prefix = uid.rstrip("0123456789")
        suffix = uid[len(prefix) :]
        if suffix == "":
            suffix = 0
        else:
            suffix = int(suffix)
        if prefix in user_prefix2counter:
            if user_prefix2counter[prefix] < suffix:  # noqa: PLR1730
                user_prefix2counter[prefix] = suffix
        else:
            user_prefix2counter[prefix] = suffix

        mPA = obj_attrs.get("mailPrimaryAddress", [b""])[0].decode("UTF-8")
        if not mPA:
            continue
        localpart = mPA.rsplit("@", 1)[0]
        prefix = localpart.rstrip("0123456789")
        suffix = localpart[len(prefix) :]
        if suffix == "":
            suffix = 0
        else:
            suffix = int(suffix)
        if prefix in email_prefix2counter:
            if email_prefix2counter[prefix] < suffix:  # noqa: PLR1730
                email_prefix2counter[prefix] = suffix
        else:
            email_prefix2counter[prefix] = suffix

    for counter_type in ("usernames", "email"):
        obj_list = lo.search(
            base="cn=unique-{},cn=ucsschool,cn=univention,{}".format(counter_type, ucr.get("ldap/base")),
            scope="one",
        )
        for obj_dn, obj_attrs in obj_list:
            value = obj_attrs.get("ucsschoolUsernameNextNumber", [b""])[0].decode("UTF-8")
            try:
                prefix_counter = int(value)
            except ValueError:
                problematic_objects.setdefault(obj_dn, []).append(
                    _("{0}: counter={1!r} which is not an integer").format(obj_dn, value)
                )
                continue

            # Check: ucsschoolUsernameNextNumber should be 2 or higher
            if prefix_counter <= 1:
                problematic_objects.setdefault(obj_dn, []).append(
                    _("{0}: counter={1!r} but the value should be 2 or higher").format(obj_dn, value)
                )

            # Check: counter should be higher than existing users
            prefix = obj_attrs.get("cn", [b""])[0].decode("UTF-8")
            if counter_type == "usernames":
                user_prefix_counter = user_prefix2counter.get(prefix)
            else:
                user_prefix_counter = email_prefix2counter.get(prefix)
            if user_prefix_counter is not None and user_prefix_counter >= prefix_counter:
                problematic_objects.setdefault(obj_dn, []).append(
                    _("{0}: {1} counter={2!r} but found user with uid {3}{4}").format(
                        obj_dn, counter_type, value, prefix, user_prefix_counter
                    )
                )

    if problematic_objects:
        details = "\n\n" + _("The following objects have faulty counter values:")
        for dn, problems in problematic_objects.items():
            details += "\n  {}".format(dn)
            for problem in problems:
                details += "\n    - {}".format(problem)
        raise Warning(description + details)


if __name__ == "__main__":
    run(None)
