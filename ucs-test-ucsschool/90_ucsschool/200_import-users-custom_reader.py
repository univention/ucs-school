#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## -*- coding: utf-8 -*-
## desc: Checks that custom reader classes work.
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: safe
## packages:
##   - ucs-school-import
## bugs: [57613]
import subprocess
from pathlib import Path

import pytest

CONFIG_CONTENT = """{
        "classes": {
                "reader": "test_reader.TestReader"
        },
        "csv": {
                "mapping": {
                        "Schulen": "schools",
                        "Benutzertyp": "__role",
                        "Vorname": "firstname",
                        "Nachname": "lastname",
                        "Klassen": "school_classes",
                        "Beschreibung": "description",
                        "Telefon": "phone",
                        "EMail": "email"
                }
        },
        "scheme": {
                "record_uid": "<firstname>.<lastname>",
                "username": {
                    "default": "<:umlauts><firstname>.<lastname><:lower>[COUNTER2]"
                }
        },
        "source_uid": "TESTID",
        "verbose": false,
        "normalize": {
                "firstname": false,
                "lastname": false
        }
}
"""

CSV_CONTENT = """"Schulen","Benutzertyp","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"
"DEMOSCHOOL","student","Akshar","Könemann","DEMOSCHOOL-1a","A student.","+71-709-511386",""
"""

READER_CONTENT = """from ucsschool.importer.reader.csv_reader import CsvReader
from ucsschool.importer.configuration import Configuration

class TestReader(CsvReader):
        def __init__(self):
                self.config = Configuration()
                filename = self.config["input"]["filename"]
                header_lines = self.config["csv"]["header_lines"]
                super(TestReader, self).__init__(filename, header_lines)
"""


@pytest.fixture()
def test_config(tmp_path) -> Path:
    config_path = tmp_path / "test_config.json"
    with open(config_path, "w") as fp:
        fp.write(CONFIG_CONTENT)
    return config_path


@pytest.fixture()
def test_data(tmp_path) -> Path:
    config_path = tmp_path / "test_data.csv"
    with open(config_path, "w") as fp:
        fp.write(CSV_CONTENT)
    return config_path


@pytest.fixture()
def test_reader():
    reader_path = Path("/usr/lib/python3/dist-packages/test_reader.py")
    with open(reader_path, "w") as fp:
        fp.write(READER_CONTENT)
    yield
    reader_path.unlink()


@pytest.mark.usefixtures("test_reader")
def test_custom_reader_classes_without_kwargs_work(test_config, test_data):
    """Tests that custom reader classes, which do not expect args and kwargs, still work."""
    result = subprocess.run(
        [
            "/usr/share/ucs-school-import/scripts/ucs-school-user-import",
            "-n",
            "-c",
            test_config,
            "-i",
            test_data,
        ],
        check=False,
    )
    assert result.returncode == 0, "The import dry-run should exit successfully."
