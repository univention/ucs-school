#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Unittests for italc multiple ips and macs
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: safe
## bugs: [51976]
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

import notifier
import pytest
import requests
from requests import Response

import univention.testing.strings as uts
from ucsschool.veyon_client import client as veyon_client_module
from ucsschool.veyon_client.models import AuthenticationMethod
from univention.config_registry import handler_set, handler_unset
from univention.management.console.config import ucr
from univention.management.console.modules.computerroom import room_management as room_management_module
from univention.management.console.modules.computerroom.room_management import (
    ITALC_USER_REGEX,
    VEYON_USER_REGEX,
    ComputerRoomError,
    ITALC_Computer,
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


def monkey_get(*args, **kwargs):
    response = Response()
    url_parts = args[0].split("/")
    ip = url_parts[-1]
    if ip == "invalid":
        response.status_code = 400
    elif ip == "valid":
        response.status_code = 200
    else:
        response.status_code = 404
    return response


def get_dummy_veyon_computer(ips=None, auth_method=None):
    notifier.init(notifier.GENERIC)
    client = veyon_client_module.VeyonClient(
        "http://localhost:11080/api/v1",
        credentials={"username": "user", "password": "secret"},
        auth_method=auth_method or AuthenticationMethod.AUTH_LOGON,
    )
    return VeyonComputer(
        computer=MockComputer(ips), user_map=UserMap(VEYON_USER_REGEX), veyon_client=client
    )


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_first_valid_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(2)]
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    mocked_subprocess.call.return_value = 0
    active_ip = ITALC_Computer.get_active_ip(ips)
    assert active_ip == ips[0]
    assert (mocked_subprocess.call.call_count == 1) is ucr_value_set
    if ucr_value_set:
        args, _ = mocked_subprocess.call.call_args_list[0]
        assert args[0] == ["/usr/bin/timeout", "1", "ping", "-c", "1", ips[0]]


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_second_valid_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(2)]
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    mocked_subprocess.call.side_effect = [2, 0]
    active_ip = ITALC_Computer.get_active_ip(ips)
    if ucr_value_set:
        assert active_ip == ips[1]
    else:
        assert active_ip == ips[0]
    assert (mocked_subprocess.call.call_count == 2) is ucr_value_set
    if ucr_value_set:
        for i, ip in enumerate(ips):
            args, _ = mocked_subprocess.call.call_args_list[i]
            assert args[0] == ["/usr/bin/timeout", "1", "ping", "-c", "1", ip]


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_multiple_ips_last_valid_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(10)]
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    mocked_subprocess.call.side_effect = [2] * 9 + [0]
    active_ip = ITALC_Computer.get_active_ip(ips)
    if ucr_value_set:
        assert active_ip == ips[-1]
    else:
        assert active_ip == ips[0]
    assert (mocked_subprocess.call.call_count == 10) is ucr_value_set
    if ucr_value_set:
        for i, ip in enumerate(ips):
            args, _ = mocked_subprocess.call.call_args_list[i]
            assert args[0] == ["/usr/bin/timeout", "1", "ping", "-c", "1", ip]


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_no_valid_ip_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = ["11.146.186.100", "12.173.49.218"]
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    mocked_logger = mocker.patch.object(room_management_module, "MODULE")
    mocked_subprocess.call.return_value = 2
    active_ip = ITALC_Computer.get_active_ip(ips)
    # this is the default behaviour.
    assert active_ip == ips[0]
    assert (mocked_subprocess.call.call_count == 2) is ucr_value_set
    assert (mocked_logger.warn.call_count == 1) is ucr_value_set
    if ucr_value_set:
        for i, ip in enumerate(ips):
            args, _ = mocked_subprocess.call.call_args_list[i]
            assert args[0] == ["/usr/bin/timeout", "1", "ping", "-c", "1", ip]
        args, kwargs = mocked_logger.warn.call_args_list[0]
        assert (
            args[0] == "Non of the ips is pingable: ['11.146.186.100', '12.173.49.218']"
        ) is ucr_value_set


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_ip_not_in_cache_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    mocked_logger = mocker.patch.object(room_management_module, "MODULE")
    ip = uts.random_ip()
    mac = uts.random_mac()
    out = b"""Address                  HWtype  HWaddress           Flags Mask            Iface"""
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    mac_from_ip = ITALC_Computer.mac_from_ip(ip)
    assert mac != mac_from_ip
    if ucr_value_set:
        args, kwargs = mocked_logger.warn.call_args_list[0]
        assert args[0] == "Ip '{}' is not in arp cache.".format(ip)
    assert (mocked_logger.warn.call_count == 1) is ucr_value_set


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_valid_mac_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    ip = uts.random_ip()
    mac = uts.random_mac()
    out = (
        """Address                  HWtype  HWaddress           Flags Mask            Iface
{}             ether   {}   C                     ens3
    """.format(
            ip, mac
        )
    ).encode("utf-8")
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    mac_from_ip = ITALC_Computer.mac_from_ip(ip)
    # this is empty, if ucr is not set.
    assert (mac == mac_from_ip) is ucr_value_set


def test_no_ips_italc():
    with pytest.raises(ComputerRoomError) as exc:
        computer = MockComputer()
        computer.info = {
            "ip": [],
            "mac": [],
        }
        ITALC_Computer(computer=computer, user_map=UserMap(ITALC_USER_REGEX))
        assert exc == "Unknown IP address"


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_access_mac_before_ip_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ips = [uts.random_ip() for _ in range(2)]
    macs = [uts.random_mac() for _ in range(2)]
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    mocked_subprocess.call.return_value = 0
    out = (
        """Address                  HWtype  HWaddress           Flags Mask            Iface
    {}             ether   {}   C                     ens3
        """.format(
            ips[0], macs[0]
        )
    ).encode("utf-8")
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    computer = ITALC_Computer(computer=MockComputer(ips, macs), user_map=UserMap(ITALC_USER_REGEX))
    # reset _active_mac to recalculate it in computer.macAddress
    # this should be the same before and after ucr.
    computer._active_mac = None
    assert computer.macAddress == macs[0]
    assert computer.ipAddress == ips[0]


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_mac_not_in_udm_computer_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(2)]
    macs = [uts.random_mac() for _ in range(2)]
    mocked_logger = mocker.patch.object(room_management_module, "MODULE")
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    wrong_mac = uts.random_mac()
    mocked_subprocess.call.return_value = 0
    out = (
        """Address                  HWtype  HWaddress           Flags Mask            Iface
    {}             ether   {}   C                     ens3
        """.format(
            ips[0], wrong_mac
        )
    ).encode("utf-8")
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    computer = ITALC_Computer(computer=MockComputer(ips, macs), user_map=UserMap(ITALC_USER_REGEX))
    computer._active_mac = None
    # reset _active_mac to recalculate it in computer.macAddress
    assert computer.macAddress == macs[0]
    if ucr_value_set:
        args, kwargs = mocked_logger.warn.call_args_list[0]
        assert args[0] == "Active mac {} is not in udm computer object.".format(wrong_mac)


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_multiple_macs_last_valid_italc(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(10)]
    macs = [uts.random_mac() for _ in range(10)]
    mocked_subprocess = mocker.patch.object(room_management_module, "subprocess")
    mocked_subprocess.call.side_effect = [2] * 9 + [0]
    out = (
        """Address                  HWtype  HWaddress           Flags Mask            Iface
    {}             ether   {}   C                     ens3
        """.format(
            ips[-1], macs[-1]
        )
    ).encode("utf-8")
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    computer = ITALC_Computer(computer=MockComputer(ips, macs), user_map=UserMap(ITALC_USER_REGEX))
    # reset _active_mac to recalculate it in computer.macAddress
    computer._active_mac = None
    if ucr_value_set:
        assert computer.macAddress == macs[-1]
        assert computer.ipAddress == ips[-1]
    else:
        assert computer.macAddress == macs[0]
        assert computer.ipAddress == ips[0]


def test_connected_veyon(monkeypatch):
    monkeypatch.setattr(requests, "get", monkey_get)
    ips = ["valid"]
    computer = get_dummy_veyon_computer(ips)
    assert computer.connected()


def test_second_valid_veyon(monkeypatch):
    handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses=yes"])
    ucr.load()
    monkeypatch.setattr(requests, "get", monkey_get)
    ips = ["invalid", "valid"]
    computer = get_dummy_veyon_computer(ips)
    assert computer.connected()
    assert computer._veyon_client.ping(ips[0]) is False
    assert computer._veyon_client.ping(ips[1])


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_first_valid_veyon(monkeypatch, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    monkeypatch.setattr(requests, "get", monkey_get)
    ips = ["valid", "invalid"]
    computer = get_dummy_veyon_computer(ips)
    assert computer.connected()
    assert computer._veyon_client.ping(ips[0])
    assert computer._veyon_client.ping(ips[1]) is False


def test_multiple_ips_last_valid_veyon(monkeypatch):
    handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses=yes"])
    ucr.load()
    monkeypatch.setattr(requests, "get", monkey_get)
    ips = ["invalid"] * 10
    ips.append("valid")
    computer = get_dummy_veyon_computer(ips)
    assert computer.connected()
    print(computer.connected())
    for ip in ips[:-1]:
        assert computer._veyon_client.ping(ip) is False
    assert computer._veyon_client.ping(ips[-1])


def test_no_valid_ip_veyon(monkeypatch):
    monkeypatch.setattr(requests, "get", monkey_get)
    ips = ["invalid"] * 2
    computer = get_dummy_veyon_computer(ips)
    assert computer.connected() is False
    for ip in ips[:-1]:
        assert computer._veyon_client.ping(ip) is False


def test_no_ips_veyon(monkeypatch):
    notifier.init(notifier.GENERIC)
    monkeypatch.setattr(requests, "get", monkey_get)
    client = veyon_client_module.VeyonClient(
        "http://localhost:11080/api/v1",
        credentials={"username": "user", "password": "secret"},
        auth_method=AuthenticationMethod.AUTH_LOGON,
    )
    with pytest.raises(ComputerRoomError) as exc:
        computer = MockComputer()
        computer.info = {
            "ip": [],
            "mac": [],
        }
        computer = VeyonComputer(
            computer=computer, user_map=UserMap(VEYON_USER_REGEX), veyon_client=client
        )
        _ = computer.ipAddress
        assert computer.connected() is False
        assert exc == "Unknown IP address"


if __name__ == "__main__":
    assert pytest.main(["-l", "-v", __file__]) == 0
