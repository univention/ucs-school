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
## desc: Test import_lusd cli
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import2]
## exposure: dangerous
## packages:
##   - ucs-school-import


import copy
import json
import os
import pathlib
import shutil
import subprocess
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import time
from typing import Any, Generator, List

import jwt
import pytest
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from ldap.filter import filter_format

import univention.testing.ucsschool.ucs_test_school as testing_ucsschool
from ucsschool.import_lusd.cli import CONFIG_PATH, Configuration
from univention.admin.uldap import getMachineConnection

TEACHER_CONFIG_PATH = pathlib.Path(
    "/usr/share/ucs-school-import-lusd/import-config/user_import_lusd_teacher.json"
)
STUDENT_CONFIG_PATH = pathlib.Path(
    "/usr/share/ucs-school-import-lusd/import-config/user_import_lusd_student.json"
)

TEST_DATA_STUDENT_PATH = pathlib.Path("/usr/share/ucs-school-import-lusd/example_data/student.json")
TEST_DATA_TEACHER_PATH = pathlib.Path("/usr/share/ucs-school-import-lusd/example_data/teacher.json")

TEST_SOURCE_UID = "UCS_TEST_LUSD"


def get_test_data(dienststellennummern: List[str], lusd_role: str) -> Any:
    lusd_test_data = {"lernende": TEST_DATA_STUDENT_PATH, "personal": TEST_DATA_TEACHER_PATH}
    lusd_uid = {"lernende": "schuelerUID", "personal": "personalUID"}
    test_data: Any = [{"antwort": {lusd_role: []}}]
    with open(lusd_test_data[lusd_role]) as fp:
        prepared_data = json.load(fp)
    for dienststellennummer in dienststellennummern:
        for person in prepared_data[0]["antwort"][lusd_role]:
            new_person = copy.deepcopy(person)
            new_person[lusd_uid[lusd_role]] = str(uuid.uuid4())
            new_person["dienststellennummer"] = dienststellennummer
            test_data[0]["antwort"][lusd_role].append(new_person)
        for person in prepared_data[0]["antwort"][lusd_role]:
            new_person = copy.deepcopy(person)
            new_person[
                lusd_uid[lusd_role]
            ] = f"{person[lusd_uid[lusd_role]]}-{dienststellennummer}-multi"
            new_person["dienststellennummer"] = dienststellennummer
            test_data[0]["antwort"][lusd_role].append(new_person)
    return test_data


class ServerTestHandler(BaseHTTPRequestHandler):
    def _set_response(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_POST(self) -> None:
        with open(Configuration.authentication_key_file_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                backend=crypto_default_backend(),
                password=None,
            )
        pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        assert "Authorization" in self.headers
        assert self.headers["Authorization"].startswith("Bearer ")
        assert jwt.decode(
            self.headers["Authorization"][len("Bearer ") :],
            pem,
            algorithms=["RS512"],
            audience="LUSD externer Datenaustausch",
        )
        assert self.path == "/anfrage?format=JSON"
        content_length = int(self.headers["Content-Length"])
        post_data = json.loads(self.rfile.read(content_length).decode("utf-8"))
        print(f"POST request,\nPath: {self.path}\nHeaders:\n{self.headers}\n\nBody:\n{post_data}\n")
        self._set_response()
        if "Lernende" in post_data[0]["bezeichnung"]:
            assert post_data == [
                {
                    "bezeichnung": "Administrationsdaten Lernende lesen",
                    "version": 1,
                    "parameter": {
                        "schulDienststellennummern": post_data[0]["parameter"][
                            "schulDienststellennummern"
                        ]
                    },
                }
            ]
            response = json.dumps(
                get_test_data(
                    dienststellennummern=post_data[0]["parameter"]["schulDienststellennummern"],
                    lusd_role="lernende",
                )
            ).encode()
        else:
            assert post_data == [
                {
                    "bezeichnung": "Administrationsdaten Personal lesen",
                    "version": 1,
                    "parameter": {
                        "schulDienststellennummern": post_data[0]["parameter"][
                            "schulDienststellennummern"
                        ]
                    },
                }
            ]
            response = json.dumps(
                get_test_data(
                    dienststellennummern=post_data[0]["parameter"]["schulDienststellennummern"],
                    lusd_role="personal",
                )
            ).encode()
        self.wfile.write(response)


@pytest.fixture()
def private_rsa_key(backup_files: None) -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=crypto_default_backend()
    )
    Configuration.authentication_key_file_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


@pytest.fixture()
def backup_files() -> Generator[None, None, None]:
    backup_suffix = f".backup_{int(time())}"
    backup_auth_key = Configuration.authentication_key_file_path.with_suffix(backup_suffix)
    try:
        Configuration.authentication_key_file_path.rename(backup_auth_key)
    except FileNotFoundError:
        pass
    backup_downloads = Configuration.lusd_data_save_path.with_suffix(backup_suffix)
    try:
        Configuration.lusd_data_save_path.rename(backup_downloads)
    except FileNotFoundError:
        pass
    Configuration.lusd_data_save_path.mkdir(parents=True)
    backup_config = CONFIG_PATH.with_suffix(backup_suffix)
    try:
        CONFIG_PATH.replace(backup_config)
    except FileNotFoundError:
        pass
    yield
    try:
        backup_auth_key.replace(Configuration.authentication_key_file_path)
    except FileNotFoundError:
        pass
    try:
        shutil.rmtree(Configuration.lusd_data_save_path)
    except FileNotFoundError:
        pass
    try:
        backup_downloads.replace(Configuration.lusd_data_save_path)
    except FileNotFoundError:
        pass
    try:
        backup_config.replace(CONFIG_PATH)
    except FileNotFoundError:
        pass


@pytest.fixture()
def schools() -> Generator[List[str], None, None]:
    with testing_ucsschool.UCSTestSchool() as schoolenv:
        schools = schoolenv.create_multiple_ous(2)
        yield [school[0] for school in schools]


@pytest.fixture()
def config(
    tmp_path: pathlib.Path, backup_files: None, private_rsa_key: None, schools: List[str]
) -> None:
    with open(TEACHER_CONFIG_PATH) as fd:
        teacher_import_conf = json.load(fd)
    teacher_import_conf["source_uid"] = TEST_SOURCE_UID
    with open(tmp_path / "user_import_lusd_teacher.json", "w") as fd:
        json.dump(teacher_import_conf, fd)
    with open(STUDENT_CONFIG_PATH) as fd:
        student_import_conf = json.load(fd)
    student_import_conf["source_uid"] = TEST_SOURCE_UID
    with open(tmp_path / "user_import_lusd_student.json", "w") as fd:
        json.dump(student_import_conf, fd)
    test_config = f"""
[Settings]
log_level = INFO
student_import_config_path = {tmp_path / "user_import_lusd_student.json"}
teacher_import_config_path = {tmp_path / "user_import_lusd_teacher.json"}

[SchoolMappings]
{schools[0]} = 1111111
{schools[1]} = 2222222
"""
    with open(CONFIG_PATH, "w") as fd:
        fd.write(test_config)


@pytest.fixture()
def server(private_rsa_key: None) -> Generator[threading.Thread, None, None]:
    server_address = ("", 32327)
    httpd = HTTPServer(server_address, ServerTestHandler)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    yield server_thread
    httpd.shutdown()


@pytest.fixture()
def existing_data(schools: List[str]) -> Generator[None, None, None]:
    (Configuration.lusd_data_save_path / schools[0]).mkdir()
    shutil.copy(TEST_DATA_STUDENT_PATH, Configuration.lusd_data_save_path / schools[0])
    shutil.copy(TEST_DATA_TEACHER_PATH, Configuration.lusd_data_save_path / schools[0])
    (Configuration.lusd_data_save_path / schools[1]).mkdir()
    shutil.copy(TEST_DATA_STUDENT_PATH, Configuration.lusd_data_save_path / schools[1])
    shutil.copy(TEST_DATA_TEACHER_PATH, Configuration.lusd_data_save_path / schools[1])
    yield
    shutil.rmtree(Configuration.lusd_data_save_path / schools[0])
    shutil.rmtree(Configuration.lusd_data_save_path / schools[1])


def test_download(server: threading.Thread, config: None) -> None:
    test_env = {**os.environ, "LUSD_URL": "http://localhost:32327"}
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import"], env=test_env
    )
    assert server.is_alive()
    lo, _ = getMachineConnection()
    assert lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))
    # TBD: how much verification do we need?


def test_skip_fetch(config: None, existing_data: None) -> None:
    test_env = {**os.environ, "LUSD_URL": "http://univention.de"}
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--skip-fetch"], env=test_env
    )
    lo, _ = getMachineConnection()
    assert lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))


def test_dry_run(config: None, server: threading.Thread) -> None:
    test_env = {**os.environ, "LUSD_URL": "http://localhost:32327"}
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--dry-run"], env=test_env
    )
    assert server.is_alive()
    lo, _ = getMachineConnection()
    assert not lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))


def test_skip_fetch_and_dry_run(config: None, existing_data: None) -> None:
    test_env = {**os.environ, "LUSD_URL": "http://univention.de"}
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--skip-fetch", "--dry-run"],
        env=test_env,
    )
    lo, _ = getMachineConnection()
    assert not lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))


def test_help() -> None:
    output = subprocess.check_output(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--help"],
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert output.startswith("usage: /usr/share/ucs-school-import-lusd/scripts/lusd_import")


def test_config_path(server: threading.Thread, config: None) -> None:
    alternative_test_config = CONFIG_PATH.with_suffix(".alternative_test_config.ini")
    shutil.copy(CONFIG_PATH, alternative_test_config)
    try:
        CONFIG_PATH.unlink()
        test_env = {**os.environ, "LUSD_URL": "http://localhost:32327"}
        subprocess.check_call(  # nosec
            [
                "/usr/share/ucs-school-import-lusd/scripts/lusd_import",
                "--configuration-filepath",
                alternative_test_config,
            ],
            env=test_env,
        )
        assert server.is_alive()
        lo, _ = getMachineConnection()
        assert lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))
    finally:
        alternative_test_config.replace(CONFIG_PATH)


@pytest.mark.parametrize(
    "test_data_path,lusd_role",
    [(TEST_DATA_STUDENT_PATH, "lernende"), (TEST_DATA_TEACHER_PATH, "personal")],
)
def test_school_move(
    test_data_path: str, lusd_role: str, schools: List[str], config: None, existing_data: None
) -> None:
    lusd_filenames = {"lernende": "student.json", "personal": "teacher.json"}
    lusd_uid = {"lernende": "schuelerUID", "personal": "personalUID"}
    test_env = {**os.environ, "LUSD_URL": "http://univention.de"}
    lo, _ = getMachineConnection()
    with open(test_data_path) as fp:
        test_data = json.load(fp)

    # First import with two persons in school1
    test_data_school1 = copy.deepcopy(test_data)
    test_data_school1[0]["antwort"][lusd_role] = test_data_school1[0]["antwort"][lusd_role][0:2]
    print(test_data_school1)
    test_data_school2 = copy.deepcopy(test_data)
    test_data_school2[0]["antwort"][lusd_role] = test_data_school2[0]["antwort"][lusd_role][2:]
    print(test_data_school2)
    with open((Configuration.lusd_data_save_path / schools[0]) / lusd_filenames[lusd_role], "w") as fp:
        json.dump(test_data_school1, fp)
    with open((Configuration.lusd_data_save_path / schools[1]) / lusd_filenames[lusd_role], "w") as fp:
        json.dump(test_data_school2, fp)
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--skip-fetch"], env=test_env
    )
    assert lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))
    assert f"ou={schools[0]}" in lo.searchDn(
        filter_format(
            "(&(ucsschoolSourceUID=%s)(ucsschoolRecordUID=%s))",
            (TEST_SOURCE_UID, test_data[0]["antwort"][lusd_role][1][lusd_uid[lusd_role]]),
        )
    )[0]

    # Now move one person to school2
    test_data_school1 = copy.deepcopy(test_data)
    test_data_school1[0]["antwort"][lusd_role] = test_data_school1[0]["antwort"][lusd_role][0:1]
    test_data_school2 = copy.deepcopy(test_data)
    test_data_school2[0]["antwort"][lusd_role] = test_data_school2[0]["antwort"][lusd_role][1:]
    with open((Configuration.lusd_data_save_path / schools[0]) / lusd_filenames[lusd_role], "w") as fp:
        json.dump(test_data_school1, fp)
    with open((Configuration.lusd_data_save_path / schools[1]) / lusd_filenames[lusd_role], "w") as fp:
        json.dump(test_data_school2, fp)
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--skip-fetch"], env=test_env
    )
    assert lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))
    assert f"ou={schools[1]}" in lo.searchDn(
        filter_format(
            "(&(ucsschoolSourceUID=%s)(ucsschoolRecordUID=%s))",
            (TEST_SOURCE_UID, test_data[0]["antwort"][lusd_role][1][lusd_uid[lusd_role]]),
        )
    )[0]


def test_VertreterKlassen(config: None, existing_data: None, schools: List[str]) -> None:
    test_env = {**os.environ, "LUSD_URL": "http://univention.de"}
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--skip-fetch"], env=test_env
    )
    lo, _ = getMachineConnection()
    assert lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))
    groups = lo.search(
        filter_format(
            "(&(ucsschoolSourceUID=%s)(ucsschoolRecordUID=%s))",
            (TEST_SOURCE_UID, "20e8d2af-9863-479f-b327-51546c807099"),
        ),
        attr=["memberOf"],
    )[0][1]["memberOf"]
    groups_cn = [group.decode("utf-8").split(",")[0] for group in groups]
    assert {
        f"cn={schools[0]}-11KB1",
        f"cn={schools[0]}-11KB2",
        f"cn={schools[0]}-12KB1",
        f"cn={schools[0]}-11KB1",
        f"cn={schools[1]}-11KB2",
        f"cn={schools[1]}-12KB1",
    }.issubset(set(groups_cn))


def test_n_m_mapping(config: None, server: threading.Thread, schools: List[str]) -> None:
    old_config = CONFIG_PATH.read_text()
    new_config = old_config.replace(f"{schools[0]} = 1111111", f"{schools[0]} = 1111111,2222222")
    new_config = new_config.replace(f"{schools[1]} = 2222222", f"{schools[1]} = 2222222,1111111")
    CONFIG_PATH.write_text(new_config)
    test_env = {**os.environ, "LUSD_URL": "http://localhost:32327"}
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import"], env=test_env
    )
    assert server.is_alive()
    lo, _ = getMachineConnection()
    result = lo.search(
        filter_format("(&(ucsschoolSourceUID=%s)(ucsschoolRecordUID=*-multi))", (TEST_SOURCE_UID,)),
        attr=["ucsschoolSchool"],
    )
    assert result
    for person in result:
        assert set(person[1]["ucsschoolSchool"]) == {s.encode() for s in schools}


def test_empty_data(config: None, schools: List[str], existing_data: None) -> None:
    test_env = {**os.environ, "LUSD_URL": "http://univention.de"}
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--skip-fetch"], env=test_env
    )
    lo, _ = getMachineConnection()
    assert lo.searchDn(filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)))
    for school in schools:
        ((Configuration.lusd_data_save_path / school) / "student.json").write_text(
            '[{"antwort": {"lernende": []}}]'
        )
        ((Configuration.lusd_data_save_path / school) / "teacher.json").write_text(
            '[{"antwort": {"personal": []}}]'
        )
    subprocess.check_call(  # nosec
        ["/usr/share/ucs-school-import-lusd/scripts/lusd_import", "--skip-fetch"], env=test_env
    )
    result = lo.search(
        filter_format("(ucsschoolSourceUID=%s)", (TEST_SOURCE_UID,)), attr=["ucsschoolSchool"]
    )
    for person in result:
        assert person[1]["ucsschoolSchool"] == [b"lusd-limbo"]
