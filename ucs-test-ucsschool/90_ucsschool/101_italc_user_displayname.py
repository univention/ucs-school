#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Unittests for italc display names
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: safe
## bugs: []
## packages: [ucs-school-umc-computerroom]
#
# Univention Management Console
#  module: Internet Rules Module
#
# Copyright 2012-2020 Univention GmbH
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
from ucsschool.italc_integration.italc2 import UserMap

user_map = UserMap()


def random_user_str(n):  # type: (int) -> str
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


@pytest.mark.parametrize("user_str", random_user_str(100))
def test_usermap_regex(user_str):
    user_map.validate_userstr(user_str)


def test_username_missing():
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
            user_map.validate_userstr(user_str)


if __name__ == "__main__":
    assert pytest.main(["-l", "-v", __file__]) == 0
