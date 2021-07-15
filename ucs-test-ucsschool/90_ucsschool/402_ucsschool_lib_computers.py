#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check computer model in ucsschool lib
## tags: [apptest,ucsschool]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

from ucsschool.lib.models.computer import SchoolComputer
from univention.admin.uldap import getAdminConnection
from univention.testing.ucsschool.importcomputers import ComputerImport, ImportFile


def test_lookup(schoolenv):
    """
    This tests checks that no non-client computers are returned for the lookup function of the
    SchoolComputer
    """
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
    print("********** Generate school data")
    computer_import = ComputerImport(
        ou_name, nr_windows=3, nr_memberserver=3, nr_macos=3, nr_ipmanagedclient=3
    )
    print(computer_import)
    import_file = ImportFile(False, True)

    print("********** Create computers")
    import_file.run_import(computer_import)
    lo, po = getAdminConnection()
    computers = SchoolComputer.lookup(lo, ou_name)
    assert len(computers) == 9, computers
