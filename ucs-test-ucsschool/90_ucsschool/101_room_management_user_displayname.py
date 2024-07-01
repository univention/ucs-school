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
# Copyright 2012-2024 Univention GmbH
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
