#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: Unittests for veyon display names
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest, ucsschool, ucsschool_base1, unit-test]
## exposure: safe
## bugs: []
## packages: [ucs-school-umc-computerroom]
#
# Univention Management Console
#  module: Internet Rules Module
#
# SPDX-FileCopyrightText: 2012-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import pytest

import univention.testing.strings as uts
from univention.management.console.modules.computerroom.room_management import VEYON_USER_REGEX, UserMap

user_map_veyon = UserMap(VEYON_USER_REGEX)


def veyon_random_user_str(n):  # type (int) -> str
    for _i in range(n):
        domain_name = "{}-{}.{}".format(uts.random_string(), uts.random_string(), uts.random_string())
        yield "{}\\{}".format(domain_name, uts.random_username())


@pytest.mark.parametrize("user_str", veyon_random_user_str(100))
def test_usermap_regex_veyon(user_str):
    user_map_veyon.validate_userstr(user_str)


def test_missing_username_veyon():
    with pytest.raises(AttributeError):
        user_map_veyon.validate_userstr("")
