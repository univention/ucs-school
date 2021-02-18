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
# $ pytest -s -l -v ./......py::test_*
#
import re

try:
    from typing import Any, Dict, List, Tuple
except ImportError:
    pass

import tempfile

from faker import Faker
import pytest

from ucsschool.lib.models import validator as validator
from ucsschool.lib.models.utils import ucr
from ucsschool.lib.models.validator import (
    VALIDATION_LOGGER,
    ExamStudentValidator,
    StaffValidator,
    StudentValidator,
    TeachersAndStaffValidator,
    TeacherValidator,
    get_class,
    validate,
)
from ucsschool.lib.roles import role_exam_user, role_school_admin, role_staff, role_student, role_teacher
from ucsschool.lib.schoolldap import SchoolSearchBase

fake = Faker()
ldap_base = ucr["ldap/base"]
SchoolSearchBase._load_containers_and_prefixes()
staff_group_regex = SchoolSearchBase.get_is_staff_group_regex()
student_group_regex = SchoolSearchBase.get_is_student_group_regex()
teachers_group_regex = SchoolSearchBase.get_is_teachers_group_regex()


def _inside_docker():
    try:
        import ucsschool.kelvin.constants
    except ImportError:
        return False
    return ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists()


must_run_in_container = pytest.mark.skipif(
    not _inside_docker(),
    reason="Must run inside Docker container started by appcenter.",
)


def base_user(firstname, lastname):  # type: (str, str) ->  Dict[str, Any]
    return {
        "dn": "",
        "props": {
            "mobileTelephoneNumber": [],
            "postOfficeBox": [],
            "groups": [],
            "sambahome": "\\\\{}\\{}.{}".format(ucr["hostname"], firstname, lastname),
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
            "school": [
                "DEMOSCHOOL",
            ],
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
        "options": {},
        "objectType": "users/user",
    }


def student_user():  # type: () ->  Dict[str, Any]
    firstname = fake.first_name()
    lastname = fake.last_name()
    user = base_user(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        firstname, lastname, SchoolSearchBase._containerStudents, ldap_base
    )
    user["props"]["groups"] = [
        "cn=schueler-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=DEMOSCHOOL-Democlass,cn=klassen,cn={},cn=groups,ou=DEMOSCHOOL,{}".format(
            SchoolSearchBase._containerStudents, ldap_base
        ),
    ]
    user["props"]["unixhome"] = "/home/DEMOSCHOOL/schueler/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "student:school:DEMOSCHOOL",
    ]
    user["position"] = "cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        SchoolSearchBase._containerStudents, ldap_base
    )
    user["options"]["ucsschoolStudent"] = True
    return user


def exam_user():  # type: () -> Dict[str, Any]
    firstname = fake.first_name()
    lastname = fake.last_name()
    user = base_user(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},ou=DEMOSCHOOL,{}".format(
        firstname, lastname, SchoolSearchBase._examUserContainerName, ldap_base
    )
    user["props"]["groups"] = [
        "cn=schueler-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=OUdemoschool-Klassenarbeit,cn=ucsschool,cn=groups,{}".format(ldap_base),
        "cn=DEMOSCHOOL-Democlass,cn=klassen,cn={},cn=groups,ou=DEMOSCHOOL,{}".format(
            SchoolSearchBase._containerStudents, ldap_base
        ),
    ]
    user["props"]["unixhome"] = "/home/DEMOSCHOOL/schueler/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "student:school:DEMOSCHOOL",
        "exam_user:school:DEMOSCHOOL",
        "exam_user:exam:demo-exam-DEMOSCHOOL",
    ]
    user["position"] = "cn=examusers,ou=DEMOSCHOOL,{}".format(ldap_base)
    user["options"]["ucsschoolStudent"] = True
    user["options"]["ucsschoolExam"] = True
    return user


def teacher_user():  # type: () -> Dict[str, Any]
    firstname = fake.first_name()
    lastname = fake.last_name()
    user = base_user(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        firstname, lastname, SchoolSearchBase._containerTeachers, ldap_base
    )
    user["props"]["groups"] = [
        "cn=lehrer-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
    ]
    user["props"]["unixhome"] = "/home/DEMOSCHOOL/lehrer/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "teacher:school:DEMOSCHOOL",
    ]
    user["position"] = "cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        SchoolSearchBase._containerTeachers, ldap_base
    )
    user["options"]["ucsschoolTeacher"] = True
    return user


def staff_user():  # type: () -> Dict[str, Any]
    firstname = fake.first_name()
    lastname = fake.last_name()
    user = base_user(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        firstname, lastname, SchoolSearchBase._containerStaff, ldap_base
    )
    user["props"]["groups"] = [
        "cn=mitarbeiter-demoschool,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
        "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{}".format(ldap_base),
    ]
    user["props"]["unixhome"] = "/home/DEMOSCHOOL/mitarbeiter/{}.{}".format(firstname, lastname)
    user["props"]["ucsschoolRole"] = [
        "staff:school:DEMOSCHOOL",
    ]
    user["position"] = "cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        SchoolSearchBase._containerStaff, ldap_base
    )
    user["options"]["ucsschoolStaff"] = True
    return user


def teacher_and_staff_user():  # type: () -> Dict[str, Any]
    firstname = fake.first_name()
    lastname = fake.last_name()
    user = base_user(firstname, lastname)
    user["dn"] = "uid={}.{},cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        firstname, lastname, SchoolSearchBase._containerTeachersAndStaff, ldap_base
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
    user["position"] = "cn={},cn=users,ou=DEMOSCHOOL,{}".format(
        SchoolSearchBase._containerTeachersAndStaff, ldap_base
    )
    user["options"]["ucsschoolStaff"] = True
    user["options"]["ucsschoolTeacher"] = True
    return user


@pytest.fixture(autouse=True)
def mock_logger_file(mocker):
    with tempfile.NamedTemporaryFile() as f:
        mocker.patch.object(validator, "LOG_FILE", f.name)


all_user_role_objects = [
    student_user(),
    teacher_user(),
    staff_user(),
    exam_user(),
    teacher_and_staff_user(),
]
all_user_roles_names = [role_student, role_teacher, role_staff, role_exam_user, "teacher_and_staff"]


def filter_log_messages(logs, name):  # type: (List[Tuple[str, int, str]], str) -> str
    """
    get all log messages for logger with name
    """
    return "".join([m for n, _, m in logs if n == name])


def check_logs(dict_obj, record_tuples, public_logger_name, expected_msg):
    # type: (Dict[str, Any], Any, str, str) -> None
    public_logs = filter_log_messages(record_tuples, public_logger_name)
    secret_logs = filter_log_messages(record_tuples, VALIDATION_LOGGER)
    for log in (public_logs, secret_logs):
        assert expected_msg in log
    assert "{}".format(dict_obj) in secret_logs
    assert "{}".format(dict_obj) not in public_logs


@pytest.mark.parametrize(
    "dict_obj,ObjectClass",
    zip(
        all_user_role_objects,
        [
            StudentValidator,
            TeacherValidator,
            StaffValidator,
            ExamStudentValidator,
            TeachersAndStaffValidator,
        ],
    ),
    ids=all_user_roles_names,
)
def test_get_class(dict_obj, ObjectClass):
    assert get_class(dict_obj) is ObjectClass


@must_run_in_container
@pytest.mark.parametrize("dict_obj", all_user_role_objects, ids=all_user_roles_names)
def test_correct_object(caplog, dict_obj, random_logger):
    """
    correct objects should not produce validation errors (logs).
    """
    validate(dict_obj, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, VALIDATION_LOGGER)
    for log in (public_logs, secret_logs):
        assert not log
    assert "{}".format(dict_obj) not in secret_logs


def test_correct_uuid(caplog, random_logger):
    """
    the uuids for the logging event should be identical in both loggers.
    """
    user_dict = student_user()
    user_dict["props"]["school"] = []
    validate(user_dict, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, VALIDATION_LOGGER)
    uuids = []
    for log in (public_logs, secret_logs):
        uuids.append(re.search(r"^([0-9a-f\-]+)", log).group(1))
    assert len(uuids) == 2
    assert uuids[0] == uuids[1]


@pytest.mark.parametrize("dict_obj", [student_user(), exam_user()], ids=[role_student, role_exam_user])
@pytest.mark.parametrize("disallowed_role", [role_staff, role_teacher])
def test_students_exclusive_role(caplog, dict_obj, random_logger, disallowed_role):
    dict_obj["props"]["ucsschoolRole"].append("{}:school:DEMOSCHOOL".format(disallowed_role))
    validate(dict_obj, logger=random_logger)
    expected_msg = "must not have these roles: {!r}.".format(
        [role_teacher, role_staff, role_school_admin]
    )
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


@pytest.mark.parametrize(
    "get_user_a,get_user_b",
    [
        (student_user, teacher_user),
        (teacher_user, staff_user),
        (staff_user, teacher_user),
        (exam_user, teacher_user),
        (teacher_and_staff_user, student_user),
    ],
    ids=all_user_roles_names,
)
def test_false_ldap_position(caplog, get_user_a, get_user_b, random_logger):
    user_a = get_user_a()
    user_b = get_user_b()
    user_a["position"] = user_b["position"]
    validate(user_a, logger=random_logger)
    expected_msg = "has wrong position in ldap"
    check_logs(user_a, caplog.record_tuples, random_logger.name, expected_msg)


@pytest.mark.parametrize("dict_obj", all_user_role_objects, ids=all_user_roles_names)
def test_wrong_ucsschool_role(caplog, dict_obj, random_logger, random_user_name):
    wrong_school = random_user_name()
    dict_obj["props"]["ucsschoolRole"] = ["{}:school:{}".format(random_user_name(), wrong_school)]
    validate(dict_obj, logger=random_logger)
    expected_msg = "is not part of schools: {!r}".format([wrong_school])
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


def test_missing_exam_context_role(caplog, random_logger):
    dict_obj = exam_user()
    for role in list(dict_obj["props"]["ucsschoolRole"]):
        r, c, s = role.split(":")
        if "exam" == c:
            dict_obj["props"]["ucsschoolRole"].remove(role)
            break
    validate(dict_obj, logger=random_logger)
    expected_msg = "is missing role with context exam."
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


@must_run_in_container
@pytest.mark.parametrize(
    "container,dict_obj",
    [
        (SchoolSearchBase._containerStudents, student_user()),
        (SchoolSearchBase._containerTeachers, teacher_user()),
        (SchoolSearchBase._containerStaff, staff_user()),
    ],
    ids=[role_student, role_teacher, role_staff],
)
def test_missing_role_group(caplog, dict_obj, container, random_logger):
    role_group = "dummy"
    for group in list(dict_obj["props"]["groups"]):
        if re.match(r"cn={}-[^,]+,cn=groups,.+".format(container), group):
            dict_obj["props"]["groups"].remove(group)
            role_group = group
            break
    validate(dict_obj, logger=random_logger)
    expected_msg = "is missing groups at positions {!r}".format([role_group])
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


@must_run_in_container
def test_exam_student_missing_exam_group(caplog, random_logger):
    dict_obj = exam_user()
    is_exam_user = dict_obj["options"].get("ucsschoolExam", False)
    exam_group = "dummy"
    for group in list(dict_obj["props"]["groups"]):
        if is_exam_user and "cn=ucsschool,cn=groups" in group:
            dict_obj["props"]["groups"].remove(group)
            exam_group = group
            break
    validate(dict_obj, logger=random_logger)
    expected_msg = "is missing groups at positions {!r}".format([exam_group])
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


def test_missing_role_teachers_and_staff(caplog, random_logger):
    dict_obj = teacher_and_staff_user()
    missing_roles = [role for role in dict_obj["props"]["ucsschoolRole"]]
    dict_obj["props"]["ucsschoolRole"] = []
    validate(dict_obj, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, VALIDATION_LOGGER)
    for log in (public_logs, secret_logs):
        assert "is missing roles" in log
        for role in missing_roles:
            assert role in log
    assert "{}".format(dict_obj) in secret_logs
    assert "{}".format(dict_obj) not in public_logs


@must_run_in_container
@pytest.mark.parametrize("dict_obj", all_user_role_objects, ids=all_user_roles_names)
def test_missing_domain_users_group(caplog, dict_obj, random_logger):
    domain_users_groups = "dummy"
    for group in list(dict_obj["props"]["groups"]):
        if re.match(r"cn=Domain Users.+", group):
            dict_obj["props"]["groups"].remove(group)
            domain_users_groups = group
            break
    validate(dict_obj, logger=random_logger)
    expected_msg = "is missing groups at positions {!r}".format([domain_users_groups])
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


@must_run_in_container
@pytest.mark.parametrize(
    "required_attribute",
    ["username", "ucsschoolRole", "school", "firstname", "lastname"],
)
@pytest.mark.parametrize(
    "get_dict_obj",
    [student_user, teacher_user, staff_user, exam_user, teacher_and_staff_user],
    ids=[role_student, role_teacher, role_staff, role_exam_user, "teacher_and_staff"],
)
def test_missing_required_attribute(caplog, get_dict_obj, random_logger, required_attribute):
    dict_obj = get_dict_obj()
    dict_obj["props"][required_attribute] = []
    validate(dict_obj, logger=random_logger)
    expected_msg = "is missing required attributes: {!r}".format([required_attribute])
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


@must_run_in_container
@pytest.mark.parametrize(
    "dict_obj",
    [
        student_user(),
        exam_user(),
    ],
    ids=[role_student, role_exam_user],
)
def test_student_missing_class(caplog, dict_obj, random_logger):
    klass_group = "dummy"
    for group in list(dict_obj["props"]["groups"]):
        if "cn=klassen,cn=schueler,cn=groups" in group:
            dict_obj["props"]["groups"].remove(group)
            klass_group = group
            break
    validate(dict_obj, random_logger)
    klass_container = re.search(r"(cn=klassen.+)", klass_group).group()
    expected_msg = "is missing groups at positions {!r}".format([klass_container])
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


@must_run_in_container
@pytest.mark.parametrize(
    "get_user_a,get_user_b",
    [
        (student_user, teacher_user),
        (teacher_user, staff_user),
        (exam_user, teacher_user),
        (teacher_and_staff_user, student_user),
    ],
    ids=[
        "student_has_teacher_groups",
        "exam_student_has_teacher_groups",
        "teacher_has_staff_groups",
        "teacher_has_student_groups",
    ],
)
def test_validate_group_membership(caplog, get_user_a, get_user_b, random_logger):
    user_a = get_user_a()
    user_b = get_user_b()
    for group in list(user_b["props"]["groups"]):
        if group not in user_a["props"]["groups"]:
            user_a["props"]["groups"].append(group)
    validate(user_a, random_logger)
    expected_msg = "Disallowed member of group"
    check_logs(user_a, caplog.record_tuples, random_logger.name, expected_msg)


@must_run_in_container
@pytest.mark.parametrize(
    "dict_obj,remove_teachers_group",
    [(teacher_and_staff_user(), True), (teacher_and_staff_user(), False)],
    ids=["missing_teacher_group", "missing_staff_group"],
)
def test_missing_teachers_and_staff_group(caplog, dict_obj, random_logger, remove_teachers_group):
    missing_groups = []
    for group in list(dict_obj["props"]["groups"]):
        if remove_teachers_group and re.match(teachers_group_regex, group):
            dict_obj["props"]["groups"].remove(group)
            missing_groups.append(group)
        elif re.match(staff_group_regex, group):
            dict_obj["props"]["groups"].remove(group)
            missing_groups.append(group)
    validate(dict_obj, random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, VALIDATION_LOGGER)
    for log in (public_logs, secret_logs):
        assert "is missing groups at positions" in log
        for group in missing_groups:
            assert group in log
    assert "{}".format(dict_obj) in secret_logs
    assert "{}".format(dict_obj) not in public_logs
