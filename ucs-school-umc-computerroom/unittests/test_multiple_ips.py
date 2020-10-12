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


import univention.management.console.modules.computerroom.italc2 as italc_module
import univention.testing.strings as uts
from univention.management.console.modules.computerroom.italc2 import ITALC_Computer


def test_first_valid(mocker):
    ips = [uts.random_ip() for _ in range(2)]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_subprocess.call.return_value = 0
    active_ip = ITALC_Computer.get_active_ip(ips)
    assert active_ip == ips[0]
    assert mocked_subprocess.call.call_count == 1
    args, _ = mocked_subprocess.call.call_args_list[0]
    assert args[0] == ["ping", "-c", "1", ips[0]]


def test_second_valid(mocker):
    ips = [uts.random_ip() for _ in range(2)]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_subprocess.call.side_effect = [2, 0]
    active_ip = ITALC_Computer.get_active_ip(ips)
    assert active_ip == ips[1]
    assert mocked_subprocess.call.call_count == 2
    for i, ip in enumerate(ips):
        args, _ = mocked_subprocess.call.call_args_list[i]
        assert args[0] == ["ping", "-c", "1", ip]


def test_multiple_ips_last_valid(mocker):
    ips = [uts.random_ip() for _ in range(10)]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_subprocess.call.side_effect = [2] * 9 + [0]
    active_ip = ITALC_Computer.get_active_ip(ips)
    assert active_ip == ips[-1]
    assert mocked_subprocess.call.call_count == 10
    for i, ip in enumerate(ips):
        args, _ = mocked_subprocess.call.call_args_list[i]
        assert args[0] == ["ping", "-c", "1", ip]


def test_no_valid_ip(mocker):
    ips = ["11.146.186.100", "12.173.49.218"]
    mocked_subprocess = mocker.patch.object(italc_module, "subprocess")
    mocked_logger = mocker.patch.object(italc_module, "MODULE")
    mocked_subprocess.call.return_value = 2
    active_ip = ITALC_Computer.get_active_ip(ips)
    # this is the default behaviour.
    assert active_ip == ips[0]
    assert mocked_subprocess.call.call_count == 2
    for i, ip in enumerate(ips):
        args, _ = mocked_subprocess.call.call_args_list[i]
        assert args[0] == ["ping", "-c", "1", ip]
    assert mocked_logger.warn.call_count == 1
    args, kwargs = mocked_logger.warn.call_args_list[0]
    assert args[0] == "Non of the ips is pingable: ['11.146.186.100', '12.173.49.218']"
