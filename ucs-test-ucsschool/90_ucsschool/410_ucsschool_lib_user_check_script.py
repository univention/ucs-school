#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test /usr/share/ucs-school-lib/scripts/ucs-school-validate-usernames
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1,ucs-school-lib]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib
import subprocess

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models import Student
from univention.admin.uldap import getAdminConnection
from univention.testing import utils

WINDOWS_COMPLIANCE_SCRIPT_PATH = "/usr/share/ucs-school-lib/scripts/ucs-school-validate-usernames"


def test_windows_compliance_username_script(ucr_hostname):
    with utu.UCSTestSchool() as schoolenv:
        lo, _ = getAdminConnection()

        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)

        n_invalid_usernames = 3

        for _ in range(n_invalid_usernames):
            username = "com1.{}".format(uts.random_username())
            invalid_user = Student(
                name=username, school=ou_name, firstname="firstname", lastname="lastname"
            )
            invalid_user.create(lo, validate=False)
            utils.verify_ldap_object(invalid_user.dn, should_exist=True, retry_count=3, delay=5)

        detected_number_of_invalid_usernames = subprocess.check_output(
            [WINDOWS_COMPLIANCE_SCRIPT_PATH, "--silent"]
        )
        assert detected_number_of_invalid_usernames.decode() == str(n_invalid_usernames)
