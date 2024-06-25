#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: computerroom user map tests
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-computerroom]
## bugs: [56937]

from ucsschool.lib.school_umc_ldap_connection import set_credentials
from univention.management.console.modules.computerroom.room_management import VEYON_USER_REGEX, UserMap


def test_username_validation(ucr, schoolenv):
    """
    Add test to verify validation of the userstring which is sent from Veyon to the
    school exam module.

    Bug #56937
    """
    set_credentials("uid=Administrator,cn=users,{}".format(ucr.get("ldap/base")), "univention")
    user_map = UserMap(VEYON_USER_REGEX)

    if schoolenv.ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = schoolenv.ucr.get("hostname")

    school, oudn = schoolenv.create_ou(name_edudc=edudc)

    stu, studn = schoolenv.create_user(school)
    stu2, studn2 = schoolenv.create_user(school)

    userstrings = [
        "nonexistingtestuser1",
        "DOMAIN1\\nonexistingtestuser2",
        "DOMAIN1\\Administrator",
        stu,
        "DOMAIN1\\{}".format(stu2),
    ]

    for s in userstrings:
        user_map[s]

    usernames = [n.username for n in user_map.values()]

    assert "LOCAL\\nonexistingtestuser1" in usernames
    assert "LOCAL\\nonexistingtestuser2" in usernames
    assert "Administrator" in usernames
    assert stu in usernames
    assert stu2 in usernames
