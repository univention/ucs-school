#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
#
# Univention UCS@school
#
# Copyright 2007-2024 Univention GmbH
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
## desc: Test import_lusd reader class
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import2]
## exposure: safe
## packages:
##   - ucs-school-import


import pathlib
from typing import Dict, Generator, List, Union

import pytest

from ucsschool.import_lusd.reader import LUSDReader
from ucsschool.importer.configuration import Configuration, setup_configuration
from ucsschool.importer.frontend.user_import_cmdline import UserImportCommandLine

TEACHER_CONFIG_PATH = pathlib.Path(
    "/usr/share/ucs-school-import-lusd/import-config/user_import_lusd_teacher.json"
)
STUDENT_CONFIG_PATH = pathlib.Path(
    "/usr/share/ucs-school-import-lusd/import-config/user_import_lusd_student.json"
)

TEST_DATA_STUDENT_PATH = pathlib.Path("/usr/share/ucs-school-import-lusd/example_data/student.json")
TEST_DATA_TEACHER_PATH = pathlib.Path("/usr/share/ucs-school-import-lusd/example_data/teacher.json")


@pytest.fixture(autouse=True)
def clean_config() -> Generator[None, None, None]:
    Configuration._instance = None
    yield
    Configuration._instance = None


def setup_config(*config_paths: pathlib.Path, user_role: str) -> None:
    ui = UserImportCommandLine()
    default_config_files = ui.configuration_files
    setup_configuration(
        default_config_files + list(config_paths), school="ucs-test", user_role=user_role
    )


def test_lusd_reader_init(
    tmp_path: pathlib.Path,
) -> None:
    tmp_input_file = tmp_path / "input.json"
    tmp_input_file.write_text("{}")
    setup_config(STUDENT_CONFIG_PATH, user_role="student")
    LUSDReader(filename=tmp_input_file)


def test_lusd_reader_read_student() -> None:
    setup_config(STUDENT_CONFIG_PATH, user_role="student")
    lusd_reader = LUSDReader(filename=TEST_DATA_STUDENT_PATH)
    lusd_data = list(lusd_reader.read())
    assert len(lusd_data) == 3
    assert lusd_data == [
        {
            "schuelerUID": "0f2c7d6a-bc35-46f5-ab93-8c33feafe096",
            "schuelerNachname": "Röhrig",
            "schuelerVorname": "York-Finley",
            "dienststellennummer": "627000",
            "usfbk": "BFSB/----/MASC",
            "stufeSemester": "12/2",
            "klassenname": "12BFTT",
            "schuelerIdEsz": "S1700217",
        },
        {
            "schuelerUID": "e1147d03-ac63-4d79-92b1-95c46363388d",
            "schuelerNachname": "Tesfalem",
            "schuelerVorname": "Lewin",
            "dienststellennummer": "627000",
            "usfbk": "BFSB/----/MASC",
            "stufeSemester": "11/2",
            "klassenname": "11BFTT",
            "schuelerIdEsz": "S0053720",
        },
        {
            "schuelerUID": "cc4c1ba8-f3f3-4f51-8cdd-48ad592aa9e2",
            "schuelerNachname": "Abel",
            "schuelerVorname": "Torsten",
            "dienststellennummer": "627000",
            "usfbk": "BSBT/SONS/----",
            "stufeSemester": "12/2",
            "klassenname": "12LM1",
            "schuelerIdEsz": "S1699322",
        },
    ]


def test_lusd_reader_read_teacher() -> None:
    setup_config(TEACHER_CONFIG_PATH, user_role="teacher")
    lusd_reader = LUSDReader(filename=TEST_DATA_TEACHER_PATH)
    lusd_data = list(lusd_reader.read())
    assert len(lusd_data) == 2
    assert lusd_data == [
        {
            "personalUID": "20e8d2af-9863-479f-b327-51546c807099",
            "nachname": "Rosebrock",
            "vorname": "Kerime",
            "personalKuerzel": "Y276",
            "dienststellennummer": "627000",
            "klassenlehrerKlassen": "11KB1,11KB2",
            "klassenlehrerVertreterKlassen": "12KB1",
            "lehrerIdEsz": "lusd.test08@preschule.hessen.de",
            "dienststellennummerStammschule": "515400",
        },
        {
            "personalUID": "a0e8d2af-9863-479f-b327-51546c807099",
            "nachname": "Kaboom",
            "vorname": "Heloise",
            "personalKuerzel": "Y236",
            "dienststellennummer": "627000",
            "klassenlehrerKlassen": "9KB1,9KB2",
            "klassenlehrerVertreterKlassen": "9KB3",
            "lehrerIdEsz": "lusd.test09@preschule.hessen.de",
            "dienststellennummerStammschule": "515400",
        },
    ]


def test_lusd_reader_handle_input() -> None:
    setup_config(TEACHER_CONFIG_PATH, user_role="teacher")
    lusd_reader = LUSDReader(filename=TEST_DATA_TEACHER_PATH)

    class ImportUserMock:
        def __init__(self) -> None:
            self.school_classes = None

    import_user = ImportUserMock()
    lusd_reader.handle_input("klassenlehrerKlassen", "__append_school_classes", "10a,10c", import_user)
    assert import_user.school_classes == "10a,10c"
    lusd_reader.handle_input(
        "klassenlehrerVertreterKlassen", "__append_school_classes", "10g", import_user
    )
    assert import_user.school_classes == "10a,10c,10g"

    import_user = ImportUserMock()
    lusd_reader.handle_input(
        "klassenlehrerVertreterKlassen", "__append_school_classes", "10g", import_user
    )
    assert import_user.school_classes == "10g"
    lusd_reader.handle_input("klassenlehrerKlassen", "__append_school_classes", "10a,10c", import_user)
    assert import_user.school_classes == "10g,10a,10c"

    # Edge case: Empty class list
    import_user = ImportUserMock()
    lusd_reader.handle_input("klassenlehrerKlassen", "__append_school_classes", "", import_user)
    assert import_user.school_classes == ""
    lusd_reader.handle_input(
        "klassenlehrerVertreterKlassen", "__append_school_classes", "10g", import_user
    )
    assert import_user.school_classes == "10g"

    # Check that other special mapping values still work
    import_user = ImportUserMock()
    lusd_reader.handle_input("klassenlehrerKlassen", "__ignore", "5g", import_user)
    lusd_reader.handle_input(
        "klassenlehrerVertreterKlassen", "__append_school_classes", "10a", import_user
    )
    assert import_user.school_classes == "10a"


def test_lusd_reader_preprocessing() -> None:
    """Tests the preprocessing of LUSD data."""
    setup_config(TEACHER_CONFIG_PATH, user_role="teacher")
    lusd_reader = LUSDReader(filename=TEST_DATA_TEACHER_PATH)

    user_object1 = {"abc": "abc"}
    lusd_reader.lusd_preprocessing(user_object1)
    assert user_object1 == {"abc": "abc"}

    user_object2 = {
        "attr1": "value1",
        "klassenlehrerKlassen": [{"klassenname": "1a"}, {"klassenname": "2a"}, {"klassenname": "2c"}],
        "klassenlehrerVertreterKlassen": [{"klassenname": "5a"}],
    }
    lusd_reader.lusd_preprocessing(user_object2)
    assert user_object2 == {
        "klassenlehrerKlassen": "1a,2a,2c",
        "klassenlehrerVertreterKlassen": "5a",
        "attr1": "value1",
    }

    user_object3: Dict[str, Union[List[str], str]] = {
        "klassenlehrerKlassen": [],
        "klassenlehrerVertreterKlassen": [],
    }
    lusd_reader.lusd_preprocessing(user_object3)
    assert user_object3 == {"klassenlehrerKlassen": "", "klassenlehrerVertreterKlassen": ""}
