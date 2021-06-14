#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: Check if all required LDAP indices for UCS@school are set up
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest,ucsschool]
## exposure: safe
## packages:
##    - ucs-school-master | ucs-school-singlemaster | ucs-school-slave

from __future__ import print_function

import univention.config_registry

EXPECTED_ATTRS = {
    "pres": ["ucsschoolSchool", "ucsschoolRecordUID", "ucsschoolSourceUID"],
    "eq": ["ucsschoolSchool", "ucsschoolRecordUID", "ucsschoolSourceUID"],
    "sub": ["ucsschoolRecordUID"],
}


def test_school_ldap_indicies():
    ucr = univention.config_registry.ConfigRegistry()
    ucr.load()

    for index in ("pres", "eq", "sub", "approx"):
        attr_list = ucr.get("ldap/index/%s" % (index,), "").split(",")
        for expected_attr in EXPECTED_ATTRS.get(index, []):
            assert expected_attr in attr_list, (
                "Expected attribute %r to be found LDAP index ldap/index/%s, but this was not the case: %s"
                % (expected_attr, index, attr_list)
            )
            print("OK: %r found in ldap/index/%s" % (expected_attr, index))
