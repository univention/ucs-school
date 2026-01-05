#!/usr/share/ucs-test/runner pytest-3 -s -l -v
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
# SPDX-FileCopyrightText: 2020-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import pytest

import univention.testing.ucsschool.ucs_test_school as utu
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.schoolroom import ComputerRoom


@pytest.fixture(scope="module")
def school(ucr_hostname):
    with utu.UCSTestSchool() as schoolenv:
        yield schoolenv.create_ou(name_edudc=ucr_hostname)


@pytest.fixture(scope="module")
def create_win_computer(school):
    def _create_win_computer():
        computers = Computers(utu.UCSTestSchool().lo, school[0], 1, 0, 0)
        created_computers = computers.create()
        return computers.get_dns(created_computers)[0]

    return _create_win_computer


def test_veyon_setting(create_win_computer, school):
    computer_dn = create_win_computer()
    room = ComputerRoom(school[0], host_members=[computer_dn], teacher_computers=[])
    room.add()
    room.assert_backend_role()


def test_veyon_add_setting(create_win_computer, school):
    computer_dn = create_win_computer()
    room = ComputerRoom(school[0], host_members=[computer_dn], teacher_computers=[])
    room.add()
    room.put({})
    room.assert_backend_role()
