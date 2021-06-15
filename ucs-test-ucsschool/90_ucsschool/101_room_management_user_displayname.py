#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v -s
## -*- coding: utf-8 -*-
## desc: Unittests for italc display names
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest, ucsschool, ucsschool_base1, unit-test]
## exposure: safe
## bugs: []
## packages: [ucs-school-umc-computerroom]
#
# Univention Management Console
#  module: Internet Rules Module
#
# Copyright 2012-2021 Univention GmbH
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

import random

import pytest

import univention.testing.strings as uts
from univention.management.console.modules.computerroom.room_management import (
    ITALC_USER_REGEX,
    VEYON_USER_REGEX,
    UserMap,
)

user_map_italc = UserMap(ITALC_USER_REGEX)
user_map_veyon = UserMap(VEYON_USER_REGEX)


def italc_random_user_str(n):  # type: (int) -> str
    enclosing = [
        ("[", "]"),
        ("{", "}"),
        ("(", ")"),
        ("$", "$"),
        ("&", "&"),
        ("/", "/"),
        ("", ""),
    ]
    for i in range(n // 2):
        a, b = random.choice(enclosing)
        yield "{0} ({1}{2}{3})".format(uts.random_username(), a, uts.random_username(), b)
    for i in range(n // 2):
        yield "{0} ({1})".format(uts.random_string(), uts.random_string())


def veyon_random_user_str(n):  # type (int) -> str
    for i in range(n):
        domain_name = "{}-{}.{}".format(uts.random_string(), uts.random_string(), uts.random_string())
        yield "{}\\{}".format(domain_name, uts.random_username())


@pytest.mark.parametrize("user_str", italc_random_user_str(100))
def test_usermap_regex_italc(user_str):
    user_map_italc.validate_userstr(user_str)


def test_username_missing_italc():
    for enclosing in [
        ("[", "]"),
        ("{", "}"),
        ("$", "$"),
        ("&", "&"),
        ("/", "/"),
        ("", ""),
    ]:
        a, b = enclosing
        user_str = "{0} {1}{2}{3}".format(uts.random_username(), a, uts.random_username(), b)
        with pytest.raises(AttributeError):
            user_map_italc.validate_userstr(user_str)


@pytest.mark.parametrize("user_str", veyon_random_user_str(100))
def test_usermap_regex_veyon(user_str):
    user_map_veyon.validate_userstr(user_str)


@pytest.mark.parametrize("user_str", veyon_random_user_str(1))
@pytest.mark.parametrize("missing_username", [True, False])
def test_username_missing_veyon(user_str, missing_username):
    user_str = user_str.split("\\")
    user_str = user_str[-1] if missing_username else user_str[0]
    with pytest.raises(AttributeError):
        user_map_veyon.validate_userstr(user_str)
