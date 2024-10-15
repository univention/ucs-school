#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test the UMCP endpoint remove_users_from_non_primary_groups
## roles: [domaincontroller_master, domaincontroller_backup]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [56766]
## packages: [ucs-school-umc-exam-master]

from __future__ import print_function

from univention.testing import utils
from univention.testing.umc import Client


def retrieve_unique_members(school, ucr):
    ldap_connection = utils.get_ldap_connection()
    values = ldap_connection.get(
        f"cn=schueler-{school},cn=groups,ou={school},{ucr.get('ldap/base')}", attr=["uniqueMember"]
    )
    try:
        return [value.decode("utf-8") for value in values["uniqueMember"]]
    except KeyError:
        return []


def test_exam_mode_create_exam_user(udm_session, schoolenv, ucr):
    """Test the 'schoolexam-master/remove-users-from-non-primary-groups' UMCP endpoint"""
    client = Client.get_test_connection()

    if ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = ucr.get("hostname")

    school, oudn = schoolenv.create_ou(name_edudc=edudc, use_cache=False)

    print("# create test users and classes")
    student1_name, student1_dn = schoolenv.create_user(school)
    student2_name, student2_dn = schoolenv.create_user(school)
    student3_name, student3_dn = schoolenv.create_user(school)
    _, class_dn = schoolenv.create_school_class(school)

    response = client.umc_command(
        "schoolexam-master/remove-users-from-non-primary-groups", {"userdns": [student1_dn]}
    )

    assert response.status == 200
    assert student1_dn not in retrieve_unique_members(school, ucr)

    response = client.umc_command(
        "schoolexam-master/remove-users-from-non-primary-groups", {"userdns": ["", student2_dn]}
    )
    assert response.status == 200
    assert student2_dn not in retrieve_unique_members(school, ucr)

    response = client.umc_command(
        "schoolexam-master/remove-users-from-non-primary-groups", {"userdns": [class_dn, student3_dn]}
    )
    assert response.status == 200
    assert student3_dn not in retrieve_unique_members(school, ucr)
