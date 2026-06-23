#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
## -*- coding: utf-8 -*-
## desc: Regression test - include:by_role must not override school/user_role CLI args (bug #59487)
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import2,ucs-school-import-lusd]
## exposure: safe
## packages:
##   - ucs-school-import-lusd

import json
import pathlib
from collections.abc import Generator

import pytest

import ucsschool.importer.utils.import_pyhook as import_pyhook_module
from ucsschool.importer.configuration import Configuration, ReadOnlyDict, setup_configuration
from ucsschool.importer.frontend.user_import_cmdline import UserImportCommandLine

STUDENT_CONFIG_PATH = pathlib.Path(
    "/usr/share/ucs-school-import-lusd/import-config/user_import_lusd_student.json"
)
PYHOOKS_AVAILABLE = pathlib.Path("/usr/share/ucs-school-import/pyhooks-available")
SCHOOL = "test-school"


@pytest.fixture(autouse=True)
def clean_config() -> Generator[None, None, None]:
    Configuration._instance = None  # pyright: ignore[reportPrivateUsage]
    import_pyhook_module.__import_pyhook_loader_instance = None  # pyright: ignore[reportPrivateUsage]
    yield
    Configuration._instance = None  # pyright: ignore[reportPrivateUsage]
    import_pyhook_module.__import_pyhook_loader_instance = None  # pyright: ignore[reportPrivateUsage]


@pytest.fixture
def include_by_role_config(tmp_path: pathlib.Path) -> pathlib.Path:
    config_file = tmp_path / "include_by_role.json"
    _ = config_file.write_text(
        json.dumps(
            {
                "hooks_dir_pyhook": str(PYHOOKS_AVAILABLE),
                "include": {"by_role": {"student": str(STUDENT_CONFIG_PATH)}},
            }
        )
    )
    return config_file


@pytest.fixture
def student_config(include_by_role_config: pathlib.Path) -> ReadOnlyDict:
    ui = UserImportCommandLine()
    return setup_configuration(
        ui.configuration_files + [str(include_by_role_config)],
        school=SCHOOL,
        user_role="student",
    )


def test_include_by_role_does_not_override_school(student_config: ReadOnlyDict) -> None:
    # Regression for bug #59487: user_import_lusd_student.json must not contain
    # "school": "" — if it does, the include:by_role hook overwrites the --school
    # CLI argument with an empty string.
    assert student_config["school"] == SCHOOL


def test_include_by_role_does_not_override_user_role(student_config: ReadOnlyDict) -> None:
    assert student_config["user_role"] == "student"
