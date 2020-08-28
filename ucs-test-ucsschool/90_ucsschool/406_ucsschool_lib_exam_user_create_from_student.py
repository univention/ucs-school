#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.share.MarketplaceShare
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python-ucs-school

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./406_ucsschool_lib_exam_user_create_from_student.py
#

try:
    from typing import Dict, List, Optional
    from univention.admin.uldap import access as LoType
except ImportError:
    pass

import pytest
from ldap.filter import filter_format

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models.group import ComputerRoom
from ucsschool.lib.models.user import ExamStudent, Student
from ucsschool.lib.roles import (
    context_type_exam,
    create_ucsschool_role_string,
    role_exam_user,
    role_student,
)


@pytest.fixture(scope="session")
def share_host(ucr_is_singlemaster, ucr_hostname):
    def _func(ou_name):  # type: (str) -> str
        if ucr_is_singlemaster:
            return ucr_hostname
        else:
            return "dc{}-01".format(ou_name)

    return _func


@pytest.fixture(scope="session")
def exp_ldap_attr_regular_student(share_host):
    def _func(ou_name, username):  # type: (str, str) -> Dict[str, List[str]]
        return {
            "objectClass": ["ucsschoolStudent"],
            "uid": [username],
            "sambaProfilePath": [r"%LOGONSERVER%\%USERNAME%\windows-profiles\default"],
            "sambaAcctFlags": ["[U          ]"],
            "krb5MaxLife": ["86400"],
            "sambaHomePath": [r"\\{}\{}".format(share_host(ou_name), username)],
            "departmentNumber": [ou_name],
            "ucsschoolSchool": [ou_name],
            "homeDirectory": ["/home/{}/schueler/{}".format(ou_name, username)],
            "ucsschoolRole": [create_ucsschool_role_string(role_student, ou_name)],
        }

    return _func


@pytest.fixture(scope="session")
def exp_ldap_attr_examuser(exp_ldap_attr_regular_student, share_host, ucr):
    def _func(lo, ou_name, username, exam=None, room=None):
        # type: (LoType, str, str, Optional[str], Optional[str]) -> Dict[str, List[str]]
        exam_prefix = ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-")
        regular_attrs = exp_ldap_attr_regular_student(ou_name, username)
        exam_username = "{}{}".format(exam_prefix, username)[:15]
        regular_attrs.update(
            {
                "objectClass": regular_attrs["objectClass"] + ["ucsschoolExam"],
                "uid": [exam_username],
                "sambaHomePath": [r"\\{}\{}".format(share_host(ou_name), exam_username)],
                "homeDirectory": ["/home/{}/schueler/exam-homes/{}".format(ou_name, exam_username)],
                "ucsschoolRole": [create_ucsschool_role_string(role_exam_user, ou_name)],
            }
        )
        if exam:
            regular_attrs["ucsschoolRole"].append(
                create_ucsschool_role_string(
                    role_exam_user, "{}-{}".format(exam, ou_name), context_type_exam
                )
            )
        if room:
            crs = ComputerRoom.get_all(
                lo, ou_name, filter_str=filter_format("cn=%s-%s", (ou_name, room))
            )
            assert len(crs) == 1
            computers = [c.name for c in crs[0].get_computers(lo)]
            regular_attrs["sambaUserWorkstations"] = computers
        return regular_attrs

    return _func


def test_create_from_student_no_exam(
    exp_ldap_attr_regular_student, exp_ldap_attr_examuser, ucr_hostname
):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
        stu_name, stu_dn = schoolenv.create_student(ou_name)
        utils.verify_ldap_object(
            stu_dn, expected_attr=exp_ldap_attr_regular_student(ou_name, stu_name), strict=False,
        )
        student = Student.from_dn(stu_dn, ou_name, schoolenv.lo)
        exam_user = ExamStudent.create_from_student(
            schoolenv.lo, student, exam=None, school=ou_name, room=None
        )
        assert isinstance(exam_user, ExamStudent)
        assert exam_user.original_user_udm.dn == stu_dn
        utils.verify_ldap_object(
            exam_user.dn,
            expected_attr=exp_ldap_attr_examuser(schoolenv.lo, ou_name, stu_name),
            strict=False,
        )
        password_student = schoolenv.lo.get(stu_dn, attr=["userPassword"])["userPassword"]
        password_exam_user = schoolenv.lo.get(exam_user.dn, attr=["userPassword"])["userPassword"]
        assert set(password_student) == set(password_exam_user)


def test_create_from_student_with_exam_and_room(
    exp_ldap_attr_regular_student, exp_ldap_attr_examuser, ucr_hostname
):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
        stu_name, stu_dn = schoolenv.create_student(ou_name)
        utils.verify_ldap_object(
            stu_dn, expected_attr=exp_ldap_attr_regular_student(ou_name, stu_name), strict=False,
        )
        student = Student.from_dn(stu_dn, ou_name, schoolenv.lo)
        exam_name = uts.random_username()
        room_name = uts.random_username()
        ComputerRoom(name="{}-{}".format(ou_name, room_name), school=ou_name).create(schoolenv.lo)
        exam_user = ExamStudent.create_from_student(
            schoolenv.lo, student, exam=exam_name, school=ou_name, room=room_name
        )
        assert isinstance(exam_user, ExamStudent)
        assert exam_user.original_user_udm.dn == stu_dn
        utils.verify_ldap_object(
            exam_user.dn,
            expected_attr=exp_ldap_attr_examuser(schoolenv.lo, ou_name, stu_name, exam_name, room_name),
            strict=False,
        )
        password_student = schoolenv.lo.get(stu_dn, attr=["userPassword"])["userPassword"]
        password_exam_user = schoolenv.lo.get(exam_user.dn, attr=["userPassword"])["userPassword"]
        assert set(password_student) == set(password_exam_user)
