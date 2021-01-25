#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Check for correct school role package
## tags: [apptest, ucsschool]
## exposure: safe

import sys

import univention.config_registry
import univention.testing.utils as utils

ucr = univention.config_registry.ConfigRegistry()
ucr.load()

role_packages = {
    "dc_multi_master": "ucs-school-master",
    "dc_single_master": "ucs-school-singlemaster",
    "dc_slave_edu": "ucs-school-slave",
    "dc_slave": "ucs-school-central-slave",
    "dc_backup": "ucs-school-backup",
}

# get my role and check role package
lo = utils.get_ldap_connection()
role = lo.get(ucr["ldap/hostdn"]).get("ucsschoolRole")[0]
role = role.split(b":", 1)[0]
role = role.decode('utf-8')
if role == "dc_master":
    role = "dc_single_master" if ucr.is_true("ucsschool/singlemaster") else "dc_multi_master"
package = role_packages[role]
if not utils.package_installed(package):
    utils.fail("{} is not installed for role {}!".format(package, role))

sys.exit(0)
