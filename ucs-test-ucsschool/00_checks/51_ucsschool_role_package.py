#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: Check for correct school role package
## tags: [apptest, ucsschool]
## exposure: safe

import univention.testing.utils as utils

role_packages = {
    "dc_multi_master": "ucs-school-master",
    "dc_single_master": "ucs-school-singlemaster",
    "dc_slave_edu": "ucs-school-slave",
    "dc_slave": "ucs-school-central-slave",
    "dc_backup": "ucs-school-master",
    "single_master": "ucs-school-singlemaster",
}


def test_ucsschool_role_package(ucr):
    # get my role and check role package
    ucr.load()
    lo = utils.get_ldap_connection()
    role = lo.get(ucr["ldap/hostdn"])["ucsschoolRole"][0].decode("utf-8")
    role = role.split(":", 1)[0]
    if role == "dc_master":
        role = "dc_single_master" if ucr.is_true("ucsschool/singlemaster") else "dc_multi_master"
    package = role_packages[role]
    assert utils.package_installed(package), "{} is not installed for role {}!".format(package, role)
