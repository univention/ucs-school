#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Check windows printer driver default for PDF printer in UCS@school
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool]
## exposure: safe
## packages: [ucs-school-umc-printermoderation]

from __future__ import print_function

import os
import subprocess


def check_value(path: str, key: str, value: str) -> None:
    cmd = ["net", "registry", "getvalue", path, key]
    # Force English output so we can match on the "Value " prefix below;
    # the `net` tool is localized and would otherwise print a translated prefix.
    env = dict(os.environ, LANG="C", LC_ALL="C")
    out, _ = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env).communicate()
    found = None
    print(path + " " + key)
    for i in out.decode("UTF-8").split("\n"):
        print(i)
        if i.startswith("Value "):
            found = i.split("=")[1].strip().strip('"')
    assert found == value, "expected '%s\\%s' to be '%s', but got '%s'" % (
        path,
        key,
        value,
        found,
    )


def test_ucsschool_check_windows_printer_driver_for_pdf_printer(ucr):
    driver_name = ucr.get("ucsschool/printermoderation/windows/driver/name")
    printer_name = "PDFDrucker"
    registry_path = r"HKLM\Software\Microsoft\Windows NT\CurrentVersion\Print\Printers\%s" % printer_name
    check_value(registry_path, "Printer Driver", driver_name)
    check_value(registry_path + r"\DsSpooler", "driverName", driver_name)
