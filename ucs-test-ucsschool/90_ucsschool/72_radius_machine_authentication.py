#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: Computers(schools) module
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-radius-802.1x]

from __future__ import print_function

import random

from ldap.filter import filter_format

import univention.testing.utils as utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.computerroom import Computers, set_windows_pc_password
from univention.testing.ucsschool.internetrule import InternetRule
from univention.testing.ucsschool.radius import test_peap_auth as _test_peap_auth
from univention.testing.ucsschool.workgroup import Workgroup


def random_case(txt):  # type: (str) -> str
    """
    Try up to 1000 times to randomize given string by using upper/lowercase variants of its characters.
    """
    assert txt, "Given string should not be empty!"
    result = []
    for i in range(1000):
        for c in txt:
            if random.randint(0, 1):
                result.append(c.upper())
            else:
                result.append(c.lower())
        if "".join(result) != txt:
            break
        result = []
    return "".join(result)


def test_radius_machine_authentication(schoolenv, ucr):
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    open_ldap_co = schoolenv.open_ldap_connection()

    radius_secret = "testing123"  # parameter set in  /etc/freeradius/clients.conf
    password = "univention"

    # importing random 2 computers
    computers = Computers(open_ldap_co, school, 2, 0, 0)
    created_computers = computers.create()
    for computer in created_computers:
        set_windows_pc_password(computer.dn, password)
    dns = computers.get_dns(created_computers)
    hostnames = computers.get_hostnames(created_computers)

    group = Workgroup(school, members=[dns[0]])
    group.create()
    rule = InternetRule(wlan=True)
    rule.define()

    group2 = Workgroup(school, members=[dns[1]])
    group2.create()
    rule2 = InternetRule(wlan=False)
    rule2.define()

    utils.wait_for_replication_and_postrun()

    rule.assign(school, group.name, "workgroup")
    rule2.assign(school, group2.name, "workgroup")

    utils.wait_for_replication_and_postrun()
    print("Wait until computers are replicated into S4...")
    for name in [x.name for x in created_computers]:
        wait_for_drs_replication(filter_format("cn=%s", (name,)))

    test_couples = []

    def add_test_couples(hostname, expected_success):
        test_couples.extend(
            [
                (hostname, expected_success),  # original case
                (hostname.lower(), expected_success),  # all lowercase
                (hostname.upper(), expected_success),  # all uppercase
                (random_case(hostname), expected_success),  # all random case
            ]
        )

    add_test_couples(hostnames[0], True)
    add_test_couples(hostnames[1], False)

    # Testing loop
    for username, should_succeed in test_couples:
        _test_peap_auth(username, password, radius_secret, should_succeed=should_succeed)
