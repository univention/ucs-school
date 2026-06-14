#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Check windows printer driver default for PDF printer in UCS@school
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool]
## exposure: safe
## packages: [ucs-school-umc-printermoderation]

import os
import subprocess

import pytest


def registry_value(path: str, key: str) -> str | None:
    cmd = ["net", "registry", "getvalue", path, key]
    # Force English output so we can match on the "Value " prefix below;
    # the `net` tool is localized and would otherwise print a translated prefix.
    env = dict(os.environ, LANG="C.UTF-8", LC_ALL="C.UTF-8")
    result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, env=env, text=True)

    for line in result.stdout.splitlines():
        print(line)
        if line.startswith("Value "):
            return line.split("=", 1)[1].strip().strip('"')

    return None


@pytest.mark.parametrize(
    "path_suffix,key",
    [
        ("", "Printer Driver"),
        (r"\DsSpooler", "driverName"),
    ],
)
def test_ucsschool_check_windows_printer_driver_for_pdf_printer(ucr, path_suffix: str, key: str):
    driver_name = ucr.get("ucsschool/printermoderation/windows/driver/name")
    actual = registry_value(
        rf"HKLM\Software\Microsoft\Windows NT\CurrentVersion\Print\Printers\PDFDrucker{path_suffix}", key
    )

    assert actual == driver_name
