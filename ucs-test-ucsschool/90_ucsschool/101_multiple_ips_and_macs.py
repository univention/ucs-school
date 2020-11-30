#!/usr/share/ucs-test/runner python
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

import pytest

import univention.testing.strings as uts
from ucsschool.italc_integration import italc2 as italc_module
from ucsschool.italc_integration.italc2 import ITALC_Computer, ITALC_Error
from univention.config_registry import handler_set, handler_unset
from univention.management.console.config import ucr


class MockComputer:
    def __init__(self, ips=None, macs=None):
        self.dn = ""
        self.info = {
            "ip": ips or [uts.random_ip()],
            "mac": macs or [uts.random_mac()],
        }
        self.module = "computers/windows"


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_first_valid(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(2)]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_subprocess.call.return_value = 0
    active_ip = ITALC_Computer.get_active_ip(ips)
    assert active_ip == ips[0]
    assert (mocked_subprocess.call.call_count == 1) is ucr_value_set
    if ucr_value_set:
        args, _ = mocked_subprocess.call.call_args_list[0]
        assert args[0] == ["timeout", "1", "ping", "-c", "1", ips[0]]


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_second_valid(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(2)]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
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
            assert args[0] == ["timeout", "1", "ping", "-c", "1", ip]


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_multiple_ips_last_valid(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(10)]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
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
            assert args[0] == ["timeout", "1", "ping", "-c", "1", ip]


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_no_valid_ip(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = ["11.146.186.100", "12.173.49.218"]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_logger = mocker.patch.object(italc_module, "MODULE")
    mocked_subprocess.call.return_value = 2
    active_ip = ITALC_Computer.get_active_ip(ips)
    # this is the default behaviour.
    assert active_ip == ips[0]
    assert (mocked_subprocess.call.call_count == 2) is ucr_value_set
    assert (mocked_logger.warn.call_count == 1) is ucr_value_set
    if ucr_value_set:
        for i, ip in enumerate(ips):
            args, _ = mocked_subprocess.call.call_args_list[i]
            assert args[0] == ["timeout", "1", "ping", "-c", "1", ip]
        args, kwargs = mocked_logger.warn.call_args_list[0]
        assert (
            args[0] == "Non of the ips is pingable: ['11.146.186.100', '12.173.49.218']"
        ) is ucr_value_set


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_ip_not_in_cache(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_logger = mocker.patch.object(italc_module, "MODULE")
    ip = uts.random_ip()
    mac = uts.random_mac()
    out = b"""Address                  HWtype  HWaddress           Flags Mask            Iface
        """.format(
        ip, mac
    )
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
def test_valid_mac(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    ip = uts.random_ip()
    mac = uts.random_mac()
    out = b"""Address                  HWtype  HWaddress           Flags Mask            Iface
{}             ether   {}   C                     ens3
    """.format(
        ip, mac
    )
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    mac_from_ip = ITALC_Computer.mac_from_ip(ip)
    # this is empty, if ucr is not set.
    assert (mac == mac_from_ip) is ucr_value_set


def test_no_ips():
    with pytest.raises(ITALC_Error) as exc:
        computer = MockComputer()
        computer.info = {
            "ip": [],
            "mac": [],
        }
        ITALC_Computer(computer=computer)
        assert exc == "Unknown IP address"


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_access_mac_before_ip(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ips = [uts.random_ip() for _ in range(2)]
    macs = [uts.random_mac() for _ in range(2)]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_subprocess.call.return_value = 0
    out = b"""Address                  HWtype  HWaddress           Flags Mask            Iface
    {}             ether   {}   C                     ens3
        """.format(
        ips[0], macs[0]
    )
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    computer = ITALC_Computer(computer=MockComputer(ips, macs))
    # reset _active_mac to recalculate it in computer.macAddress
    # this should be the same before and after ucr.
    computer._active_mac = None
    assert computer.macAddress == macs[0]
    assert computer.ipAddress == ips[0]


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_mac_not_in_udm_computer(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(2)]
    macs = [uts.random_mac() for _ in range(2)]
    mocked_logger = mocker.patch.object(italc_module, "MODULE")
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    wrong_mac = uts.random_mac()
    mocked_subprocess.call.return_value = 0
    out = b"""Address                  HWtype  HWaddress           Flags Mask            Iface
    {}             ether   {}   C                     ens3
        """.format(
        ips[0], wrong_mac
    )
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    computer = ITALC_Computer(computer=MockComputer(ips, macs))
    computer._active_mac = None
    # reset _active_mac to recalculate it in computer.macAddress
    assert computer.macAddress == macs[0]
    if ucr_value_set:
        args, kwargs = mocked_logger.warn.call_args_list[0]
        assert args[0] == "Active mac {} is not in udm computer object.".format(wrong_mac)


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_multiple_macs_last_valid(mocker, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/umc/computerroom/ping-client-ip-addresses"])
    else:
        handler_set(["ucsschool/umc/computerroom/ping-client-ip-addresses={}".format(ucr_value)])
    ucr.load()
    ucr_value_set = ucr_value == "yes"
    ips = [uts.random_ip() for _ in range(10)]
    macs = [uts.random_mac() for _ in range(10)]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_subprocess.call.side_effect = [2] * 9 + [0]
    out = b"""Address                  HWtype  HWaddress           Flags Mask            Iface
    {}             ether   {}   C                     ens3
        """.format(
        ips[-1], macs[-1]
    )
    popen_mock = mocker.Mock(**{"communicate.return_value": (out, "")})
    mocked_subprocess.PIPE = -1
    mocked_subprocess.STDOUT = 1
    mocked_subprocess.Popen.return_value = popen_mock
    computer = ITALC_Computer(computer=MockComputer(ips, macs))
    # reset _active_mac to recalculate it in computer.macAddress
    computer._active_mac = None
    if ucr_value_set:
        assert computer.macAddress == macs[-1]
        assert computer.ipAddress == ips[-1]
    else:
        assert computer.macAddress == macs[0]
        assert computer.ipAddress == ips[0]


if __name__ == "__main__":
    assert pytest.main(["-l", "-v", __file__]) == 0
