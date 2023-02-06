#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Computers(schools) module
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-radius-802.1x]

from univention.testing import ucs_samba, utils
from univention.testing.ucsschool.internetrule import InternetRule
from univention.testing.ucsschool.radius import test_peap_auth as _test_peap_auth
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client


def test_radius_internetrules_priority(schoolenv, ucr):
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    umc_connection = Client.get_test_connection()

    groups = []
    users = []
    rules = []

    rules_attrs = [
        (False, 2),
        (True, 6),
        (True, 1),
        (False, 9),
        (True, 0),
        (False, 4),
        (True, 5),
        (False, 10),
    ]

    for (wlan, priority) in rules_attrs:
        rule = InternetRule(wlan=wlan, priority=priority, connection=umc_connection)
        rule.define()
        rules.append(rule)

    for _i in range(2):
        tea, tea_dn = schoolenv.create_user(school, is_teacher=True)
        stu, stu_dn = schoolenv.create_user(school)
        users.append([tea, stu])
        for _j in range(2):
            group = Workgroup(school, members=[tea_dn, stu_dn], connection=umc_connection)
            group.create()
            groups.append(group)

    tea, tea_dn = schoolenv.create_user(school, is_teacher=True)
    stu, stu_dn = schoolenv.create_user(school)
    users.append([tea, stu])
    for _j in range(4):
        group = Workgroup(school, members=[tea_dn, stu_dn], connection=umc_connection)
        group.create()
        groups.append(group)

    utils.wait_for_replication_and_postrun()
    ucs_samba.wait_for_s4connector()

    for (rule, group) in zip(rules, groups):
        rule.assign(school, group.name, "workgroup")

    utils.wait_for_replication_and_postrun()
    ucs_samba.wait_for_s4connector()

    radius_secret = "testing123"  # parameter set in /etc/freeradius/clients.conf
    password = "univention"
    allow_radius_access = [True, False, False]
    test_couples = zip(users, allow_radius_access)

    # Testing loop
    for (user_list, should_succeed) in test_couples:
        for username in user_list:
            _test_peap_auth(username, password, radius_secret, should_succeed=should_succeed)
