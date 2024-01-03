#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-reset-password-non-school-member
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## bugs: [50231, 56938]
## exposure: dangerous
## packages: [ucs-school-umc-users]

from __future__ import print_function

from collections import namedtuple

import pytest

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
from univention.lib.umc import HTTPError
from univention.testing import utils
from univention.testing.umc import Client

PASSWORD = "univention"


def auth(username, password):
    try:
        client = Client(username=username, password=password)
    except HTTPError as exc:
        return exc.response

    return client


@pytest.fixture(scope="module")
def get_hostname():
    ucr = ucr_test.UCSTestConfigRegistry()
    ucr.load()
    return ucr.get("hostname")


@pytest.fixture(scope="module")
def school_environment(get_hostname):
    """
    School environment for this test module

    Two Schools:
        - School1
            - Student1
            - Teacher1
            - TeacherAndStaff1
            - Class1 which contains Student1 _and_ Student2 (for Bug #50231)
        - School2
            - Student2

        - One school admin for both schools
    """
    with utu.UCSTestSchool() as schoolenv:
        host = get_hostname

        school_name_1, oudn1 = schoolenv.create_ou(name_edudc=host, use_cache=False)
        school_name_2, oudn2 = schoolenv.create_ou(name_edudc=host, use_cache=False)
        assert school_name_1 != school_name_2

        teacher = None
        teacher_dn = None

        students = []
        students_dns = []

        school_names = [school_name_1, school_name_2]
        school_dns = [oudn1, oudn2]

        teacher, teacher_dn = schoolenv.create_user(school_name_1, is_teacher=True, password=PASSWORD)

        school_admin, school_admin_dn = schoolenv.create_school_admin(
            school_name_1, is_teacher=True, is_staff=False, password="univention", schools=school_names
        )

        teacher_and_staff, teacher_and_staff_dn = schoolenv.create_teacher_and_staff(
            school_name_1, password=PASSWORD
        )

        stu1, studn1 = schoolenv.create_user(school_name_1)
        stu2, studn2 = schoolenv.create_user(school_name_2)

        students.append(stu1)
        students.append(stu2)

        students_dns.append(studn1)
        students_dns.append(studn2)

        class_name, class_dn = schoolenv.create_school_class(
            ou_name=school_name_1, users=[studn1, studn2], wait_for_replication=True
        )

        utils.wait_for_replication_and_postrun()

        SchoolEnvironment = namedtuple(
            "SchoolEnvironment",
            [
                "teacher",
                "teacher_dn",
                "students",
                "students_dns",
                "class_name",
                "class_dn",
                "school_names",
                "school_dns",
                "school_admin",
                "school_admin_dn",
                "teacher_and_staff",
                "teacher_and_staff_dn",
            ],
        )

        yield SchoolEnvironment(
            teacher,
            teacher_dn,
            students,
            students_dns,
            class_name,
            class_dn,
            school_names,
            school_dns,
            school_admin,
            school_admin_dn,
            teacher_and_staff,
            teacher_and_staff_dn,
        )


def test_no_fail_on_non_school_members(school_environment, get_hostname):
    """
    When a teacher tries to list users of a class which has members that are
    members of other schools (Bug #50231).
    """
    client = auth(school_environment.teacher, "univention")

    options = {
        "class": school_environment.class_dn,
        "pattern": "",
        "school": school_environment.school_names[0],
    }

    response = client.umc_command("schoolusers/query", options, "student")
    result = response.result

    # len(result) represents the number of students returned
    # expecting it to be equal to 1
    assert len(result) == 1
    assert result[0]["id"] == school_environment.students_dns[0]
    assert result[0]["passwordexpiry"] == -1


@pytest.mark.parametrize("usertype", ["teacher", "teacher_and_staff", "school_admin", "admin"])
@pytest.mark.parametrize("flavor", ["student", "teacher", "staff"])
def test_search_query(school_environment, get_hostname, usertype, flavor):
    """
    Tests the first search query of the different flavors which the UMC password module sends
    to the backend when opened.

    Bug #56938
    """
    if usertype == "admin":
        client = Client.get_test_connection(get_hostname)
    else:
        username = getattr(school_environment, usertype)
        client = auth(username, PASSWORD)

    options = {
        "class": "None",
        "pattern": "",
        "school": school_environment.school_names[0],
    }

    if flavor == "student":
        response = client.umc_command("schoolusers/query", options, flavor)
        assert response.status == 200

        result = response.result

        # There is only 1 student in the first school
        assert len(result) == 1

        assert result[0]["id"] == school_environment.students_dns[0]
        assert result[0]["passwordexpiry"] == -1

    elif flavor == "teacher":
        if usertype in ["school_admin", "admin"]:
            response = client.umc_command("schoolusers/query", options, flavor)
            assert response.status == 200, response.response
            result = response.result

            # teacher, teacher/staff and the school_admin which is himself a teacher
            assert {e["id"] for e in result} == {
                school_environment.teacher_dn,
                school_environment.teacher_and_staff_dn,
                school_environment.school_admin_dn,
            }

        else:
            with pytest.raises(HTTPError) as excinfo:
                response = client.umc_command("schoolusers/query", options, flavor)

            assert excinfo.value.response.status == 403

    elif flavor == "staff":
        if usertype in ["school_admin", "admin"]:
            response = client.umc_command("schoolusers/query", options, flavor)
            assert response.status == 200
            result = response.result

            assert len(result) == 1
            assert result[0]["id"] == school_environment.teacher_and_staff_dn
            assert result[0]["passwordexpiry"] == -1
        else:
            with pytest.raises(HTTPError) as excinfo:
                response = client.umc_command("schoolusers/query", options, flavor)

            assert excinfo.value.response.status == 403
