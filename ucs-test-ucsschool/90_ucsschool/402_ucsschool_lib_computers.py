#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Check computer model in ucsschool lib
## tags: [apptest,ucsschool]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - python-ucs-school

import univention.testing.ucsschool.ucs_test_school as utu
from univention.admin.uldap import getAdminConnection
from univention.testing.ucsschool.importcomputers import ImportFile, ComputerImport
from ucsschool.lib.models import SchoolComputer


def test_lookup(ou_name):
    """
    This tests checks that no non-client computers are returned for the lookup function of the SchoolComputer
    """
    print('********** Generate school data')
    computer_import = ComputerImport(ou_name, nr_windows=3, nr_memberserver=3, nr_macos=3, nr_ipmanagedclient=3)
    print(computer_import)
    import_file = ImportFile(False, True)

    print('********** Create computers')
    import_file.run_import(computer_import)
    lo, po = getAdminConnection()
    computers = SchoolComputer.lookup(lo, ou_name)
    assert len(computers) == 9


def main():
    with utu.UCSTestSchool() as school_env:
        ou_name, ou_dn = school_env.create_ou(name_edudc=school_env.ucr.get('hostname'))
        test_lookup(ou_name)


if __name__ == '__main__':
    main()
