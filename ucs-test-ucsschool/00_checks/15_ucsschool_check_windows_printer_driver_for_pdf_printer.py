#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: Check windows printer driver default for PDF printer in UCS@school
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool]
## exposure: safe
## packages: [ucs-school-umc-printermoderation]

from __future__ import print_function

import subprocess


def check_value(path, key, value):
    cmd = ["net", "registry", "getvalue", path, key]
    out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    found = False
    print(path + " " + key)
    for i in out.decode("UTF-8").split("\n"):
        print(i)
        if i.startswith("Value "):
            v = i.split("=")[1].strip().strip('"')
            if v == value:
                found = True
    assert found, "value in '%s' is '%s' not!" % (path + "\\" + key, value)


def test_ucsschool_check_windows_printer_driver_for_pdf_printer(ucr):
    driver_name = ucr.get("ucsschool/printermoderation/windows/driver/name")
    printer_name = "PDFDrucker"
    registry_path = r"HKLM\Software\Microsoft\Windows NT\CurrentVersion\Print\Printers\%s" % printer_name
    check_value(registry_path, "Printer Driver", driver_name)
    check_value(registry_path + r"\DsSpooler", "driverName", driver_name)
