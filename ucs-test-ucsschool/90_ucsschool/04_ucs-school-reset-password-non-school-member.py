#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-reset-password-non-school-member
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## bugs: [50231]
## exposure: dangerous
## packages: []

from __future__ import print_function

from collections import namedtuple

import pytest

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
from univention.lib.umc import HTTPError
from univention.testing import utils
from univention.testing.umc import Client


def auth(host, username, password):
    try:
        client = Client(host)
        client.authenticate(username, password)
    except HTTPError as exc:
        return exc.response

    return client


@pytest.fixture(scope="session")
def get_hostname():
    ucr = ucr_test.UCSTestConfigRegistry()
    ucr.load()
    return ucr.get("hostname")


@pytest.fixture(scope="session")
def minimal_school_environment(get_hostname):
    host = get_hostname
    with utu.UCSTestSchool() as schoolenv:
        schoolName1, oudn1 = schoolenv.create_ou(name_edudc=host, use_cache=False)
        schoolName2, oudn2 = schoolenv.create_ou(name_edudc=host, use_cache=False)
        assert schoolName1 != schoolName2
        teacher = None
        teacherDn = None
        students = []
        studentsDN = []
        schoolNames = [schoolName1, schoolName2]
        schoolDN = [oudn1, oudn2]

        teacher, teacherDn = schoolenv.create_user(schoolName1, is_teacher=True)
        schoolenv._set_password(userdn=teacherDn, password="univention")
        stu1, studn1 = schoolenv.create_user(schoolName1)
        stu2, studn2 = schoolenv.create_user(schoolName2)
        students.append(stu1)
        students.append(stu2)
        studentsDN.append(studn1)
        studentsDN.append(studn2)

        class_name, group_dn = schoolenv.create_school_class(
            ou_name=schoolName1, class_name="classOU1", users=[studn1, studn2], wait_for_replication=True
        )
        utils.wait_for_replication_and_postrun()
        Environment = namedtuple(
            "Environment",
            [
                "teacher",
                "teacherDn",
                "students",
                "studentDNs",
                "class_name",
                "groupDN",
                "schoolNames",
                "schoolDN",
            ],
        )

        yield Environment(
            teacher, teacherDn, students, studentsDN, class_name, group_dn, schoolNames, schoolDN
        )


def test_no_fail_on_non_school_members(minimal_school_environment, get_hostname):
    """
    Checks that the password-reset-module within the UMC does not crash,
    when a teacher tries to read a class with members in a class that are
    members of other schools (Bug #50231).
    """
    host = get_hostname
    client = auth(host, minimal_school_environment.teacher, "univention")

    flavor = "student"
    options = {
        "class": minimal_school_environment.groupDN,
        "pattern": "",
        "school": minimal_school_environment.schoolNames[0],
    }

    result = client.umc_command("schoolusers/query", options, flavor).result
    # len(result) represents the number of students returned
    # expecting it to be equal to 1
    assert len(result) == 1
    assert result[0]["id"] == minimal_school_environment.studentDNs[0]
    assert result[0]["passwordexpiry"] == -1
