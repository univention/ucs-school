#!/usr/bin/py.test
# -*- coding: iso-8859-15 -*-
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

import os
import random
import sys

import pytest

import univention.testing.strings as uts

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "umc", "python"))

from computerroom.italc2 import UserMap  # noqa: ignore=E402

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
