#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: Unittests for veyon multiple ips and macs
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: safe
## bugs: [51976]
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

import socket

import pytest

import univention.testing.strings as uts
from ucsschool.veyon_client import client as veyon_client_module
from ucsschool.veyon_client.models import AuthenticationMethod, Dimension
from univention.config_registry import handler_set, handler_unset
from univention.management.console.config import ucr
from univention.management.console.modules.computerroom.room_management import (
    VEYON_USER_REGEX,
    UserMap,
    VeyonComputer,
)


class MockComputer:
    def __init__(self, ips=None, macs=None):
        self.dn = ""
        self.info = {
            "ip": ips or [uts.random_ip()],
            "mac": macs or [uts.random_mac()],
            "name": "test-pc",
        }
        self.module = "computers/windows"


def monkey_connect_ex(*args, **kwargs):
    ip = args[1][0]
    if ip == "invalid":
        return 1
    elif ip == "valid":
        return 0
    else:
        raise OSError()


def get_dummy_veyon_computer(ips=None, auth_method=None):
    client = veyon_client_module.VeyonClient(
        "http://localhost:11080/api/v1",
        credentials={"username": "user", "password": "secret"},
        auth_method=auth_method or AuthenticationMethod.AUTH_LOGON,
    )
    return VeyonComputer(
        computer=MockComputer(ips),
        user_map=UserMap(VEYON_USER_REGEX),
        veyon_client=client,
        screenshot_dimension=Dimension(None, None),
    )


def test_connected_veyon(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect_ex", monkey_connect_ex)
    ips = ["valid"]
    computer = get_dummy_veyon_computer(ips)
    computer._check_connection()
    assert computer.connected


def test_second_valid_veyon(monkeypatch):
    handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses=yes"])
    ucr.load()
    monkeypatch.setattr(socket.socket, "connect_ex", monkey_connect_ex)
    ips = ["invalid", "valid"]
    computer = get_dummy_veyon_computer(ips)
    computer._check_connection()
    assert computer.connected
    assert computer._veyon_client.ping(ips[0]) is False
    assert computer._veyon_client.ping(ips[1])


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_first_valid_veyon(monkeypatch, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    monkeypatch.setattr(socket.socket, "connect_ex", monkey_connect_ex)
    ips = ["valid", "invalid"]
    computer = get_dummy_veyon_computer(ips)
    computer._check_connection()
    assert computer.connected
    assert computer._veyon_client.ping(ips[0])
    assert computer._veyon_client.ping(ips[1]) is False


def test_multiple_ips_last_valid_veyon(monkeypatch):
    handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses=yes"])
    ucr.load()
    monkeypatch.setattr(socket.socket, "connect_ex", monkey_connect_ex)
    ips = ["invalid"] * 10
    ips.append("valid")
    computer = get_dummy_veyon_computer(ips)
    computer._check_connection()
    assert computer.connected
    for ip in ips[:-1]:
        assert computer._veyon_client.ping(ip) is False
    assert computer._veyon_client.ping(ips[-1])


def test_no_valid_ip_veyon(monkeypatch):
    ips = ["invalid"] * 2
    computer = get_dummy_veyon_computer(ips)
    monkeypatch.setattr(socket.socket, "connect_ex", monkey_connect_ex)
    computer._check_connection()
    assert computer.connected is False
    for ip in ips[:-1]:
        assert computer._veyon_client.ping(ip) is False


def test_no_ips_veyon(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect_ex", monkey_connect_ex)
    client = veyon_client_module.VeyonClient(
        "http://localhost:11080/api/v1",
        credentials={"username": "user", "password": "secret"},
        auth_method=AuthenticationMethod.AUTH_LOGON,
    )
    computer = MockComputer()
    computer.info = {
        "ip": [],
        "mac": [],
    }
    computer = VeyonComputer(
        computer=computer,
        user_map=UserMap(VEYON_USER_REGEX),
        veyon_client=client,
        screenshot_dimension=Dimension(None, None),
    )
    _ = computer.ipAddress
    computer._check_connection()
    assert computer.connected is False
