#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
#
# Univention UCS@school
#
# Copyright 2024 Univention GmbH
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
#
## -*- coding: utf-8 -*-
## desc: Test import_lusd class level hook
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import2]
## exposure: safe
## packages:
##   - ucs-school-import-lusd

import sys

import pytest

from ucsschool.importer.models.import_user import ImportStudent


@pytest.fixture()
def class_level_hook_instance():  # type: ignore[no-untyped-def]
    sys.path.append("/usr/share/ucs-school-import-lusd/hooks/")
    from lusd_class_level_hook import LUSDClassLevel

    return LUSDClassLevel()


@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("", None),
        ("FOO", None),
        ("1", None),
        (1, None),
        (True, None),
        ("09/1", "9"),
        ("09/2", "9"),
        ("09/3", None),
        ("12/1", None),
        ("10/1", "10"),
        ("10/2", "10"),
        ("10/3", None),
        ("E1", "11"),
        ("E2", "11"),
        ("E3", None),
        ("Q1", "12"),
        ("Q2", "12"),
        ("Q3", "13"),
        ("Q4", "13"),
        ("Q5", None),
        ("-/1", ""),
        ("-/2", ""),
        ("-/3", None),
    ],
)
def test_calculate_class_level(input_value, expected, class_level_hook_instance, mocker):  # type: ignore[no-untyped-def]
    user = mocker.MagicMock()
    user.input_data = {"stufeSemester": input_value}
    class_level = class_level_hook_instance.calculate_class_level(user)
    assert class_level == expected


@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("", None),
        ("FOO", None),
        ("1", None),
        (1, None),
        (True, None),
        ("09/1", "9"),
        ("09/2", "9"),
        ("09/3", None),
        ("12/1", None),
        ("10/1", "10"),
        ("10/2", "10"),
        ("10/3", None),
        ("E1", "11"),
        ("E2", "11"),
        ("E3", None),
        ("Q1", "12"),
        ("Q2", "12"),
        ("Q3", "13"),
        ("Q4", "13"),
        ("Q5", None),
        ("-/1", ""),
        ("-/2", ""),
        ("-/3", None),
    ],
)
def test_pre_create_udm_property_value(input_value, expected, class_level_hook_instance, mocker):  # type: ignore[no-untyped-def]
    user = mocker.MagicMock(spec=ImportStudent)
    user.udm_properties = {}
    user.input_data = {"stufeSemester": input_value}
    class_level_hook_instance.pre_create(user)
    if expected is None:
        assert "class_level" not in user.udm_properties, user.udm_properties
    else:
        assert user.udm_properties["class_level"] == expected, user.udm_properties
