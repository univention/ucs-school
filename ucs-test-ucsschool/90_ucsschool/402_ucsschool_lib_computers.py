#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check computer model in ucsschool lib
## tags: [apptest,ucsschool]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

import univention.testing.strings as uts
from ucsschool.lib.models.computer import IPComputer, MacComputer, SchoolComputer, WindowsComputer
from univention.admin.uldap import getAdminConnection


def test_lookup(schoolenv):
    """
    This tests checks that no non-client computers are returned for the lookup function of the
    SchoolComputer
    """
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
    lo = schoolenv.lo
    for _ in range(3):
        WindowsComputer(
            **{
                "school": ou_name,
                "name": uts.random_name(),
                "ip_address": [uts.random_ip()],
                "mac_address": [uts.random_mac()],
            }
        ).create(lo)
        MacComputer(
            **{
                "school": ou_name,
                "name": uts.random_name(),
                "ip_address": [uts.random_ip()],
                "mac_address": [uts.random_mac()],
            }
        ).create(lo)
        IPComputer(
            **{
                "school": ou_name,
                "name": uts.random_name(),
                "ip_address": [uts.random_ip()],
                "mac_address": [uts.random_mac()],
            }
        ).create(lo)
    lo, po = getAdminConnection()
    computers = SchoolComputer.lookup(lo, ou_name)
    assert len(computers) == 9, computers
