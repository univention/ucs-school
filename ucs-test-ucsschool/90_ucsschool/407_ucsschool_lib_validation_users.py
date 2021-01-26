#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.users validation
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1,unit-test]
## exposure: dangerous
## packages:
##   - python-ucs-school

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./......py::test_create
#
import logging
import tempfile

try:
    from typing import Dict
except ImportError:
    pass

import re

import pytest

import univention.testing.strings as uts
from ucsschool.lib.models import validator as validator
from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff
from ucsschool.lib.models.utils import get_file_handler, ucr
from ucsschool.lib.models.validator import (
    LOGGER_NAME,
    container_exam_students,
    container_staff,
    container_students,
    container_teachers,
    container_teachers_and_staff,
    exam_students_group,
    get_role_container,
    staff_group_regex,
    teachers_group_regex,
    ucr_get,
    validate,
)
from ucsschool.lib.roles import role_exam_user, role_staff, role_student, role_teacher

ldap_base = ucr_get("ldap/base")


def base_user_dict(firstname, lastname):  # type(str, str) -> Dict
    return {
        "dn": "",
        "props": {
            "mobileTelephoneNumber": [],
            "postOfficeBox": [],
            "groups": [],
            "sambahome": "\\\\{}\\{}.{}".format(ucr_get("hostname"), firstname, lastname),
            "umcProperty": {},
            "overridePWLength": None,
            "uidNumber": 2021,
            "disabled": False,
            "preferredDeliveryMethod": None,
            "unlock": False,
            "homeShare": None,
            "postcode": None,
            "scriptpath": "ucs-school-logon.vbs",
            "sambaPrivileges": [],
            "primaryGroup": "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
            "ucsschoolPurgeTimestamp": None,
            "city": None,
            "mailForwardCopyToSelf": "0",
            "employeeType": None,
            "homedrive": "I:",
            "title": None,
            "mailAlternativeAddress": [],
            "serviceprovider": [],
            "organisation": None,
            "ucsschoolRecordUID": None,
            "e-mail": [],
            "userexpiry": None,
            "pwdChangeNextLogin": None,
            "unixhome": "",
            "sambaUserWorkstations": [],
            "preferredLanguage": None,
            "username": "tobias.wenzel",
            "departmentNumber": ["DEMOSCHOOL"],
            "homeTelephoneNumber": [],
            "shell": "/bin/bash",
            "homePostalAddress": [],
            "firstname": firstname,
            "lastname": lastname,
            "mailHomeServer": None,
            "mailForwardAddress": [],
            "phone": [],
            "gidNumber": 5086,
            "birthday": None,
            "employeeNumber": None,
            "objectFlag": [],
            "sambaLogonHours": None,
            "displayName": "{} {}".format(firstname, lastname),
            "ucsschoolRole": [],
            "password": None,
            "lockedTime": "0",
            "school": ["DEMOSCHOOL",],
            "overridePWHistory": None,
            "mailPrimaryAddress": None,
            "secretary": [],
            "country": None,
            "lastbind": None,
            "description": None,
            "roomNumber": [],
            "locked": False,
            "passwordexpiry": None,
            "pagerTelephoneNumber": [],
            "street": None,
            "gecos": "{} {}".format(firstname, lastname),
            "unlockTime": "",
            "sambaRID": 5042,
            "ucsschoolSourceUID": None,
            "profilepath": "%LOGONSERVER%\\%USERNAME%\\windows-profiles\\default",
            "initials": None,
            "jpegPhoto": None,
            "homeSharePath": "tobias.wenzel",
            "physicalDeliveryOfficeName": None,
        },
        "id": "{}.{}".format(firstname, lastname),
        "_links": {},
        "policies": {"policies/pwhistory": [], "policies/umc": [], "policies/desktop": []},
        "position": "",
        "options": [],
        "objectType": "users/user",
    }


def student_as_dict():  # type(None) -> Dict
    firstname = uts.random_name()
    lastname = uts.random_name()
    user = base_user_dict(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        firstname, lastname, container_students, ldap_base
    )
    user["props"]["groups"] = [
        "cn=schueler-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=DEMOSCHOOL-Democlass,cn=klassen,cn={},cn=groups,ou=DEMOSCHOOL,{}".format(
            container_students, ldap_base
        ),
    ]
    user["props"]["unihome"] = "/home/DEMOSCHOOL/schueler/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "student:school:DEMOSCHOOL",
    ]
    user["position"] = "cn={},cn=users,ou=DEMOSCHOOL,{}".format(container_students, ldap_base)
    user["options"].append("ucsschoolStudent")
    return user


def exam_student_as_dict():  # type(None) -> Dict
    firstname = uts.random_name()
    lastname = uts.random_name()
    user = base_user_dict(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},ou=DEMOSCHOOL,{}".format(
        firstname, lastname, container_exam_students, ldap_base
    )
    user["props"]["groups"] = [
        "cn=schueler-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=OUdemoschool-Klassenarbeit,cn=ucsschool,cn=groups,{}".format(ldap_base),
        "cn=DEMOSCHOOL-Democlass,cn=klassen,cn={},cn=groups,ou=DEMOSCHOOL,{}".format(
            container_students, ldap_base
        ),
    ]
    user["props"]["unixhome"] = "/home/DEMOSCHOOL/schueler/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "exam_user:school:DEMOSCHOOL",
        "exam_user:exam:{}-DEMOSCHOOL".format(uts.random_name()),
    ]
    user["position"] = "cn=examusers,ou=DEMOSCHOOL,{}".format(ldap_base)
    user["options"].append("ucsschoolStudent")
    user["options"].append("ucsschoolExam")
    return user


def teacher_as_dict():  # type(None) -> Dict
    firstname = uts.random_name()
    lastname = uts.random_name()
    user = base_user_dict(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        firstname, lastname, container_teachers, ldap_base
    )
    user["props"]["groups"] = [
        "cn=lehrer-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
    ]
    user["props"]["unixhome"] = "/home/DEMOSCHOOL/lehrer/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "staff:school:DEMOSCHOOL",
    ]
    user["position"] = "cn={},cn=users,ou=DEMOSCHOOL,{}".format(container_teachers, ldap_base)
    user["options"].append("ucsschoolTeacher")
    return user


def staff_as_dict():  # type(None) -> Dict
    firstname = uts.random_name()
    lastname = uts.random_name()
    user = base_user_dict(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        firstname, lastname, container_staff, ldap_base
    )
    user["props"]["groups"] = [
        "cn=mitarbeiter-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
    ]
    user["props"]["unixhome"] = "/home/DEMOSCHOOL/mitarbeiter/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "teacher:school:DEMOSCHOOL",
    ]
    user["position"] = "cn={},cn=users,ou=DEMOSCHOOL,{}".format(container_staff, ldap_base)
    user["options"].append("ucsschoolStaff")
    return user


def teacher_and_staff_as_dict():  # type(None) -> Dict
    firstname = uts.random_name()
    lastname = uts.random_name()
    user = base_user_dict(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        firstname, lastname, container_teachers_and_staff, ldap_base
    )
    user["props"]["groups"] = [
        "cn=lehrer-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=mitarbeiter-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
    ]
    user["props"]["unixhome"] = "/home/DEMOSCHOOL/lehrer/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "teacher:school:DEMOSCHOOL",
        "staff:school:DEMOSCHOOL",
    ]
    user["position"] = "cn={},cn=users,ou=DEMOSCHOOL,{}".format(container_teachers_and_staff, ldap_base)
    user["options"].append("ucsschoolStaff")
    user["options"].append("ucsschoolTeacher")
    return user


@pytest.fixture
def random_logger():
    def _func():
        handler = get_file_handler("DEBUG", tempfile.mkstemp()[1])
        logger = logging.getLogger(uts.random_username())
        logger.addHandler(handler)
        logger.setLevel("DEBUG")
        return logger

    return _func


@pytest.fixture(autouse=True)
def mock_logger_file(mocker):
    with tempfile.NamedTemporaryFile() as file:
        mocker.patch.object(validator, "LOG_FILE", file.name)


role_mapping = {
    Student: role_student,
    ExamStudent: role_exam_user,
    Teacher: role_teacher,
    Staff: role_staff,
    TeachersAndStaff: role_teacher,
}


complete_role_matrix = [
    student_as_dict(),
    teacher_as_dict(),
    staff_as_dict(),
    exam_student_as_dict(),
    teacher_and_staff_as_dict(),
]

student_matrix = [
    (student_as_dict()),
    (exam_student_as_dict()),
]


def filter_log_messages(logs, name):
    return "".join([m for n, _, m in logs if n == name])


@pytest.mark.parametrize(
    "get_user_a,get_user_b",
    [
        (student_as_dict, teacher_as_dict),
        (student_as_dict, staff_as_dict),
        (student_as_dict, teacher_and_staff_as_dict),
        (student_as_dict, exam_student_as_dict),
        (teacher_as_dict, staff_as_dict),
        (teacher_as_dict, student_as_dict),
        (teacher_as_dict, teacher_and_staff_as_dict),
        (teacher_as_dict, exam_student_as_dict),
        (staff_as_dict, teacher_as_dict),
        (staff_as_dict, student_as_dict),
        (staff_as_dict, exam_student_as_dict),
        (staff_as_dict, teacher_and_staff_as_dict),
        (exam_student_as_dict, teacher_as_dict),
        (exam_student_as_dict, student_as_dict),
        (exam_student_as_dict, teacher_and_staff_as_dict),
        (exam_student_as_dict, staff_as_dict),
        (teacher_and_staff_as_dict, student_as_dict),
        (teacher_and_staff_as_dict, teacher_as_dict),
        (teacher_and_staff_as_dict, staff_as_dict),
        (teacher_and_staff_as_dict, exam_student_as_dict),
    ],
)
def test_correct_ldap_position(caplog, get_user_a, get_user_b, random_logger):
    random_logger = random_logger()
    user_a = get_user_a()
    user_b = get_user_b()
    user_a["position"] = user_b["position"]
    validate(user_a, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "has wrong position in ldap" in log
    assert "{}".format(user_a) in secret_logs


@pytest.mark.parametrize("user_dict", complete_role_matrix)
def test_wrong_ucsschool_role(caplog, user_dict, random_logger):
    random_logger = random_logger()
    user_dict["props"]["ucsschoolRole"] = ["{}:school:{}".format(uts.random_name(), uts.random_name())]
    validate(user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "is not part of schools: {}".format("".format(user_dict["props"]["school"])) in log
    assert "{}".format(user_dict) in secret_logs


@pytest.mark.parametrize("user_dict", student_matrix)
def test_missing_student_role(caplog, user_dict, random_logger):
    random_logger = random_logger()
    for role in user_dict["props"]["ucsschoolRole"]:
        if "student" in role:
            user_dict["props"]["ucsschoolRole"].remove(role)
    validate(user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert (
            "is missing a student role at schools: {}".format("".format(user_dict["props"]["school"]))
            in log
        )
    assert "{}".format(user_dict) in secret_logs


@pytest.mark.parametrize("user_dict", (exam_student_as_dict(),))
def test_missing_exam_context_role(caplog, user_dict, random_logger):
    random_logger = random_logger()
    for role in user_dict["props"]["ucsschoolRole"]:
        r, c, s = role.split(":")
        if "exam" == c:
            user_dict["props"]["ucsschoolRole"].remove(role)
    validate(user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "ExamStudents must have an ucsschoolRole with context exam." in log
    assert "{}".format(user_dict) in secret_logs


@pytest.mark.parametrize("user_dict", complete_role_matrix)
def test_missing_role_group(caplog, user_dict, random_logger):
    options = user_dict["options"]
    if "ucsschoolTeacher" in options and "ucsschoolStaff" in options:
        # is tested in test_missing_teachers_and_staff_group
        return
    random_logger = random_logger()
    role_container = get_role_container(user_dict["options"])
    for group in user_dict["props"]["groups"]:
        if re.match(r"cn={}-[^,]+,cn=groups,.+".format(role_container), group):
            user_dict["props"]["groups"].remove(group)
    validate(user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert (
            "is missing groups for the following schools: {}".format(
                ",".join(user_dict["props"]["school"])
            )
            in log
        )
    assert "{}".format(user_dict) in secret_logs


@pytest.mark.parametrize("role", ["teacher", "staff"])
@pytest.mark.parametrize("user_dict", student_matrix)
def test_students_wrong_role(caplog, user_dict, role, random_logger):
    random_logger = random_logger()
    user_dict["props"]["ucsschoolRole"].append("{}:school:{}".format(role, uts.random_name()))
    validate(user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "Students must not any other roles than 'student' or 'exam_student'" in log
    assert "{}".format(user_dict) in secret_logs


@pytest.mark.parametrize(
    "expected_role,user_dict",
    [
        (role_student, student_as_dict()),
        (role_teacher, teacher_as_dict()),
        (role_staff, staff_as_dict()),
        (role_exam_user, exam_student_as_dict()),
        (role_teacher, teacher_and_staff_as_dict()),
    ],
)
def test_test_missing_role(caplog, user_dict, expected_role, random_logger):
    random_logger = random_logger()
    for role in user_dict["props"]["ucsschoolRole"]:
        r, c, s = role.split(":")
        if r == expected_role:
            user_dict["props"]["ucsschoolRole"].remove(role)
    validate(user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "does not have {}-role.".format(expected_role) in log
    assert "{}".format(user_dict) in secret_logs


@pytest.mark.parametrize("user_dict", complete_role_matrix)
def test_missing_domain_users_group(caplog, user_dict, random_logger):
    random_logger = random_logger()
    for group in user_dict["props"]["groups"]:
        if re.match(r"cn=Domain Users.+", group):
            user_dict["props"]["groups"].remove(group)
    validate(user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert (
            "is missing the Domain Users groups for the following schools: {}".format(
                ",".join(user_dict["props"]["school"])
            )
            in log
        )
    assert "{}".format(user_dict) in secret_logs


@pytest.mark.parametrize(
    "user_dict",
    [student_as_dict, teacher_as_dict, staff_as_dict, exam_student_as_dict, teacher_and_staff_as_dict,],
)
@pytest.mark.parametrize(
    "required_attribute",
    ["username", "ucsschoolRole", "school", "firstname", "lastname", "groups", "primaryGroup",],
)
def test_missing_required_attribute(caplog, user_dict, random_logger, required_attribute):
    random_logger = random_logger()
    _user_dict = user_dict()
    _user_dict["props"][required_attribute] = []
    validate(_user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "is missing required attributes: {}".format(required_attribute) in log
    assert "{}".format(_user_dict) in secret_logs


@pytest.mark.parametrize("user_dict", student_matrix)
def test_student_missing_class(caplog, user_dict, random_logger):
    random_logger = random_logger()
    for group in user_dict["props"]["groups"]:
        if "cn=klassen,cn=schueler,cn=groups" in group:
            user_dict["props"]["groups"].remove(group)
    validate(user_dict, random_logger)
    assert (
        "is missing a class for the following schools: {}".format(",".join(user_dict["props"]["school"]))
        in caplog.text
    )
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert (
            "is missing a class for the following schools: {}".format(
                ",".join(user_dict["props"]["school"])
            )
            in log
        )
    assert "{}".format(user_dict) in secret_logs


@pytest.mark.parametrize(
    "get_user_a,get_user_b",
    [
        (student_as_dict, teacher_as_dict),
        (teacher_as_dict, staff_as_dict),
        (exam_student_as_dict, teacher_as_dict),
        (teacher_and_staff_as_dict, student_as_dict),
    ],
)
def test_validate_group_membership(caplog, get_user_a, get_user_b, random_logger):
    random_logger = random_logger()
    user_a = get_user_a()
    user_b = get_user_b()
    for group in user_b["props"]["groups"]:
        if group not in user_a["props"]["groups"]:
            user_a["props"]["groups"].append(group)
    validate(user_a, random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "Disallowed member of group" in log
    assert "{}".format(user_a) in secret_logs


@pytest.mark.parametrize(
    "user_dict,remove_teachers_group",
    [(teacher_and_staff_as_dict(), True), (teacher_and_staff_as_dict(), False),],
)
def test_missing_teachers_and_staff_group(caplog, user_dict, random_logger, remove_teachers_group):
    random_logger = random_logger()
    for group in user_dict["props"]["groups"]:
        if remove_teachers_group and re.match(teachers_group_regex, group):
            user_dict["props"]["groups"].remove(group)
        elif re.match(staff_group_regex, group):
            user_dict["props"]["groups"].remove(group)
    validate(user_dict, random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "is missing a Teacher or Staff group" in log
    assert "{}".format(user_dict) in secret_logs
