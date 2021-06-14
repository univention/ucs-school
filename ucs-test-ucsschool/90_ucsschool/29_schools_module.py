#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: Schools module
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-wizards]

from __future__ import print_function

import time

from univention.lib.umc import BadRequest
from univention.testing.ucsschool.school import School, create_dc_slave


def test_schools_module(udm_session):
        udm = udm_session
        schools = []
        try:
            for i in range(2):
                school = School()
                school.create()
                school.verify_ldap(True)
                schools.append(school)

            dc_slave1, dc_slave1_dn = create_dc_slave(udm, schools[0].name)
            dc_slave2, dc_slave2_dn = create_dc_slave(udm, schools[0].name)
            dc_slave3, dc_slave3_dn = create_dc_slave(udm, schools[1].name)
            dc_slave4, dc_slave4_dn = create_dc_slave(udm, schools[1].name)

            schools[0].check_query([schools[0].name, schools[1].name])

            new_attrs = {
                "display_name": "S2",
                "home_share_file_server": dc_slave1,
                "class_share_file_server": dc_slave2,
            }
            schools[0].edit(new_attrs)
            expected_attrs = {
                "display_name": "S2",
                "home_share_file_server": dc_slave1_dn,
                "class_share_file_server": dc_slave2_dn,
            }
            schools[0].check_get(expected_attrs)

            new_attrs = {
                "display_name": "S3",
                "home_share_file_server": dc_slave3,
                "class_share_file_server": dc_slave4,
            }
            schools[1].edit(new_attrs)
            expected_attrs = {
                "display_name": "S3",
                "home_share_file_server": dc_slave3_dn,
                "class_share_file_server": dc_slave4_dn,
            }
            schools[1].check_get(expected_attrs)

            while schools:
                school = schools[0]
                school.verify_ldap(True)
                school.remove()

                for wait in range(30):
                    try:
                        school.verify_ldap(False)
                    except Exception as e:
                        if school.dn() in str(e):
                            print(":::::::%r::::::" % wait)
                            print(str(e))
                            time.sleep(1)
                        else:
                            raise
                    else:
                        break
                schools.pop(0)

        finally:
            for school in schools:
                try:
                    print("Clean up remaining school %s after failed test." % school.name)
                    school.remove()
                except BadRequest:
                    print("Failed to remove remaining school %s after failed test." % school.name)
