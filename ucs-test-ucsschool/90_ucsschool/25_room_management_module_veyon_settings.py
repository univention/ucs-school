#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Schoolrooms management module
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [52422]
## packages: [ucs-school-umc-rooms]
#
# Univention Management Console
#  module: Internet Rules Module
#
# Copyright 2020 Univention GmbH
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

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
from univention.testing.ucsschool.computerroom import Computers
from univention.testing.ucsschool.schoolroom import ComputerRoom


@pytest.fixture(scope="module")
def ucr():
    with ucr_test.UCSTestConfigRegistry() as ucr:
        yield ucr


@pytest.fixture(scope="module")
def school_env():
    with utu.UCSTestSchool() as school_env:
        yield school_env


@pytest.fixture(scope="module")
def lo(school_env):
    return school_env.open_ldap_connection()


@pytest.fixture(scope="module")
def school(ucr, school_env):
    school, ou_dn = school_env.create_ou(name_edudc=ucr.get("hostname"))
    return school, ou_dn


@pytest.fixture(scope="module")
def create_win_computer(school, lo):
    def _create_win_computer():
        computers = Computers(lo, school[0], 1, 0, 0)
        created_computers = computers.create()
        return computers.get_dns(created_computers)[0]

    return _create_win_computer


@pytest.mark.parametrize("is_veyon", [False, True])
def test_veyon_setting(create_win_computer, school, is_veyon):
    computer_dn = create_win_computer()
    room = ComputerRoom(school[0], host_members=[computer_dn], teacher_computers=[], is_veyon=is_veyon)
    room.add()
    room.assert_backend_role(is_veyon)


@pytest.mark.parametrize("is_veyon", [False, True])
def test_veyon_add_setting(create_win_computer, school, is_veyon):
    computer_dn = create_win_computer()
    room = ComputerRoom(school[0], host_members=[computer_dn], teacher_computers=[], is_veyon=is_veyon)
    room.add()
    room.put({"veyon": not is_veyon})
    room.assert_backend_role(not is_veyon)


if __name__ == "__main__":
    assert pytest.main([__file__]) == 0
