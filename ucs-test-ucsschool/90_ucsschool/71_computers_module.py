#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Computers(schools) module
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-wizards]

from __future__ import print_function

import time

from univention.testing.ucsschool.computer import random_ip, random_mac
from univention.testing.ucsschool.computerroom import UmcComputer


def test_computers_module(schoolenv, ucr):
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))

    pcs = []
    for computer_type in ["windows", "macos", "ipmanagedclient"]:
        pc = UmcComputer(school, computer_type)
        pc.create()
        pc.check_get()
        pc.verify_ldap(True)
        pcs.append(pc)

    pcs[0].check_query({x.name for x in pcs})

    new_attrs = {
        "ip_address": random_ip(),
        "mac_address": random_mac(),
        "subnet_mask": "255.255.0.0",
        "inventory_number": "5",
    }
    for pc in pcs:
        pc.edit(**new_attrs)
        pc.check_get()
        pc.verify_ldap(True)
        pc.remove()
        for wait in range(30):
            try:
                pc.verify_ldap(False)
            except Exception as e:
                if pc.dn() in str(e):
                    print(":::::::%r::::::" % wait)
                    print(str(e))
                    time.sleep(1)
                else:
                    raise
            else:
                break
