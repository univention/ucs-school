#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2024-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
## -*- coding: utf-8 -*-
## desc: Test import_lusd class level hook
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import2,ucs-school-import-lusd]
## exposure: safe
## packages:
##   - ucs-school-import-lusd

import pathlib
import sys
from typing import Generator

import pytest

from ucsschool.importer.configuration import Configuration, setup_configuration
from ucsschool.importer.frontend.user_import_cmdline import UserImportCommandLine
from ucsschool.importer.models.import_user import ImportStudent

STUDENT_CONFIG_PATH = pathlib.Path(
    "/usr/share/ucs-school-import-lusd/import-config/user_import_lusd_student.json"
)


def setup_config() -> None:
    ui = UserImportCommandLine()
    default_config_files = ui.configuration_files
    setup_configuration(
        default_config_files + [STUDENT_CONFIG_PATH], school="ucs-test", user_role="student"
    )


@pytest.fixture(autouse=True)
def import_config() -> Generator[None, None, None]:
    Configuration._instance = None
    setup_config()
    yield
    Configuration._instance = None


@pytest.fixture
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
