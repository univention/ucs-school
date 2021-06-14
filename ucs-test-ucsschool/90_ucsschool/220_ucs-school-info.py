#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: simple test run of ucs-school-info
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master,domaincontroller_backup,domaincontroller_slave]
## exposure: safe
## packages:
##   - ucs-school-info

import subprocess


def test_ucs_school_info(ucr, lo):
    for dn, ou_attrs in lo.search(
        base=ucr["ldap/base"],
        filter="(objectClass=ucsschoolOrganizationalUnit)",
        scope="one",
        attr=["ou"],
    ):
        subprocess.check_call(["ucs-school-info", "-a", ou_attrs["ou"][0].decode("UTF-8")])
