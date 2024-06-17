#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test student data validation by endpoint groups2students
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [57319]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

import pytest

import univention.testing.strings as uts
from ucsschool.lib.models.user import Student
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.lib.umc import HTTPError
from univention.testing.umc import Client


def test_groups2students_validation(udm_session, schoolenv, ucr):
    if ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = ucr.get("hostname")

    ldap_connection = schoolenv.open_ldap_connection()

    if ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = ucr.get("hostname")
    school, oudn = schoolenv.create_ou(name_edudc=edudc)
    search_base = SchoolSearchBase([school])

    school, oudn = schoolenv.create_ou(name_edudc=edudc)
    class_name, class_dn = schoolenv.create_school_class(school)
    tea, teadn = schoolenv.create_user(school, is_teacher=True, classes=class_name)
    stu0, studn0 = schoolenv.create_user(school, classes=class_name)
    stu1, studn1 = schoolenv.create_user(school, classes=class_name)

    stu2 = Student(
        name=uts.random_username(),
        school=school,
        lastname=uts.random_name(),
        school_classes={school: [class_name]},
    )
    stu2.position = search_base.students

    stu2.create(ldap_connection, validate=False)

    client = Client.get_test_connection(language="en-US")
    params = {
        "groups": [
            class_dn,
        ]
    }

    with pytest.raises(HTTPError) as err:
        client.umc_command("schoolexam/groups2students", params)

    expected_string = "The following students have validation errors:\n\nuid={}".format(stu2.name)
    assert expected_string in err.value.message

    stu2.firstname = "Testname"
    stu2.modify(ldap_connection)
    client.umc_command("schoolexam/groups2students", params)
