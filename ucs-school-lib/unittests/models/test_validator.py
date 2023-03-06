import sys

import pytest

sys.path.insert(1, "modules")
from ucsschool.lib.models.school import School  # noqa: E402
from ucsschool.lib.models.utils import ucr  # noqa: E402
from ucsschool.lib.models.validator import (  # noqa: E402
    ExamStudentValidator,
    TeacherValidator,
)
from ucsschool.lib.roles import (  # noqa: E402
    context_type_exam,
    create_ucsschool_role_string,
    role_student,
)

ldapbase = ucr.get("ldap/base")
school_name = "MustermannSchule"
School.get_search_base(school_name)
School._search_base_cache[school_name]._schoolDN = "ou={},{}".format(school_name, ldapbase)


def make_udmobj_user(role_name="lehrer", props_overrides=None):
    props_overrides = props_overrides or {}
    username = props_overrides.get("username", "msmith")
    base = {
        "props": {
            "username": username,
            "uidNumber": "2000",
            "gidNumber": "5000",
            "firstname": "Mary",
            "lastname": "Smith",
            "gecos": "Mary Smith",
            "displayName": "Mary Smith",
            "title": "",
            "initials": "",
            "preferredDeliveryMethod": "",
            "sambaPrivileges": [],
            "description": "",
            "organisation": "",
            "userexpiry": None,
            "passwordexpiry": None,
            "pwdChangeNextLogin": "",
            "preferredLanguage": "",
            "disabled": "0",
            "accountActivationDate": "",
            "locked": "0",
            "lockedTime": "0",
            "unlock": "",
            "unlockTime": "",
            "password": "{crypt}$6$p1A727prgEviftBf$4BRbc894OXOC2PteaOQt410zwVUTvCdBf6eXNB29WpXktgCsDEzLTVoxGi1Sk9ExIYivmNsbx5FUuVOD2N46T/",  # noqa: E501
            "street": "",
            "e-mail": [],
            "postcode": "",
            "postOfficeBox": [],
            "city": "",
            "country": "",
            "phone": [],
            "employeeNumber": "",
            "roomNumber": [],
            "secretary": [],
            "departmentNumber": [school_name],
            "employeeType": "",
            "homePostalAddress": [],
            "physicalDeliveryOfficeName": "",
            "homeTelephoneNumber": [],
            "mobileTelephoneNumber": [],
            "pagerTelephoneNumber": [],
            "birthday": "",
            "unixhome": "/home/{}/{}".format(school_name, username),
            "shell": "/bin/bash",
            "sambahome": "\\\\dc0\\{}".format(username),
            "scriptpath": "ucs-school-logon.vbs",
            "profilepath": "%LOGONSERVER%\\%USERNAME%\\windows-profiles\\default",
            "homedrive": "I:",
            "sambaRID": "5032",
            "groups": [
                "cn=Domain Users {},cn=groups,ou={},{}".format(school_name, school_name, ldapbase),
                "cn={}-{},cn=groups,ou={},{}".format(
                    role_name,
                    school_name.lower(),
                    school_name,
                    ldapbase,
                ),
            ],
            "primaryGroup": "cn=Domain Users {},cn=groups,ou={},{}".format(
                school_name,
                school_name,
                ldapbase,
            ),
            "mailHomeServer": "",
            "mailPrimaryAddress": "",
            "mailAlternativeAddress": [],
            "mailForwardAddress": [],
            "mailForwardCopyToSelf": "0",
            "overridePWHistory": "",
            "overridePWLength": "",
            "homeShare": "",
            "homeSharePath": "",
            "sambaUserWorkstations": [],
            "sambaLogonHours": "",
            "jpegPhoto": "",
            "umcProperty": [],
            "serviceSpecificPassword": "",
            "objectFlag": [],
            "lastbind": "",
            "serviceprovider": [],
            "school": [school_name],
            "ucsschoolSourceUID": "",
            "ucsschoolRecordUID": "",
            "ucsschoolPurgeTimestamp": "",
            "ucsschoolRole": [],
        },
        "dn": "uid={},cn={},cn=users,ou={},{}".format(
            username,
            role_name,
            school_name,
            ldapbase,
        ),
        "position": "cn={},cn=users,ou={},{}".format(role_name, school_name, ldapbase),
        "options": {
            "ucsschoolTeacher": role_name == "lehrer",
            "ucsschoolStudent": role_name == "student",
            "default": True,
        },
    }
    base["props"].update(props_overrides)
    return base


def make_udmobj_student(school_roles):
    overrides = {
        "username": "bsmith",
        "uidNumber": "2017",
        "gidNumber": "5099",
        "firstname": "Bob",
        "lastname": "Smith",
        "gecos": "Bob Smith",
        "displayName": "Bob Smith",
        "ucsschoolRole": school_roles,
    }
    return make_udmobj_user("student", overrides)


def make_udmobj_teacher(school_roles):
    overrides = {
        "username": "mmustermann",
        "uidNumber": "2016",
        "gidNumber": "5098",
        "firstname": "Max",
        "lastname": "Mustermann",
        "gecos": "Max Mustermann",
        "displayName": "Max Mustermann",
        "ucsschoolRole": school_roles,
    }
    return make_udmobj_user("lehrer", overrides)


class RoleValidationTestCase:
    UNKNOWN_ROLE = "foo"
    UNKNOWN_CONTEXT_TYPE = "bar"

    # error string generators
    def split_errstr(self, role_str):
        return "Invalid UCS@school role string: {!r}.".format(role_str)

    def destructuring_errstr(self, role_str):
        return "Invalid UCS@school role string: {!r}.".format(role_str)

    def invalid_role_errstr(self, role_str, role):
        return "The role string {!r} includes the unknown role {!r}.".format(role_str, role)

    def invalid_context_errstr(self, role_str, context_type):
        return "The role string {!r} includes the unknown context type {!r}.".format(
            role_str, context_type
        )


class TestExamStudentValidator(RoleValidationTestCase):
    def test_exam_role_with_colons_invalid(self):
        exam_name = "Spring 2028: Biology 101: Middterm-DEMOSCHOOL"
        role_str = "{}:{}:{}".format(role_student, context_type_exam, exam_name)
        result = ExamStudentValidator.validate(make_udmobj_student([role_str]))
        assert self.split_errstr(role_str) in result
        assert self.destructuring_errstr(role_str) in result

    def test_exam_role_created_with_create_ucsschool_role_string_valid(self):
        exam_name = "Spring 2028: Biology 101: Middterm-DEMOSCHOOL"
        role_str = create_ucsschool_role_string(
            role_student,
            exam_name,
            context_type_exam,
        )
        result = ExamStudentValidator.validate(make_udmobj_student([role_str]))
        assert self.split_errstr(role_str) not in result
        assert self.destructuring_errstr(role_str) not in result


class TestTeacherValidatorRoles(RoleValidationTestCase):
    def test_valid(self):
        role_str = ["teacher:school:{}".format(school_name)]
        result = TeacherValidator.validate(make_udmobj_teacher(role_str))
        expected_errstrs = [
            self.split_errstr(role_str),
            self.destructuring_errstr(role_str),
            self.invalid_role_errstr(role_str, self.UNKNOWN_ROLE),
            self.invalid_context_errstr(role_str, self.UNKNOWN_CONTEXT_TYPE),
        ]
        assert set(result).isdisjoint(set(expected_errstrs))

    # tests
    def test_wrong_number_of_elems_1(self):
        """Can't split at all!"""
        roles = ["teacher-bad-format"]
        assert self.split_errstr(roles[0]) in TeacherValidator.validate(
            make_udmobj_teacher(roles),
        )

    def test_wrong_number_of_elems_2(self):
        """splits 4 items, we destructure this into 3 items!"""
        roles = ["a:s:d:f"]
        assert self.destructuring_errstr(roles[0]) in TeacherValidator.validate(
            make_udmobj_teacher(roles),
        )

    @pytest.mark.parametrize(
        "role",
        [
            RoleValidationTestCase.UNKNOWN_ROLE + ":school:y",
            (
                RoleValidationTestCase.UNKNOWN_ROLE
                + ":"
                + RoleValidationTestCase.UNKNOWN_CONTEXT_TYPE
                + ":y"
            ),
        ],
    )
    def test_invalid_role_name(self, role):
        """correct number of elements, but the role is not in roles.py all_roles"""
        validator_result = [
            result
            for result in TeacherValidator.validate(make_udmobj_teacher([role]))
            if result is not None
        ]

        if role.split(":")[1] != self.UNKNOWN_CONTEXT_TYPE:
            assert self.invalid_role_errstr(role, role.split(":")[0]) in validator_result
        else:
            assert ["is missing roles ['teacher:school:{}']".format(school_name)] == validator_result

    @pytest.mark.parametrize(
        "role",
        [
            (
                RoleValidationTestCase.UNKNOWN_ROLE
                + ":"
                + RoleValidationTestCase.UNKNOWN_CONTEXT_TYPE
                + ":x"
            ),
            "teacher:school:x",
        ],
    )
    def test_unknown_context_type_is_valid(self, role):
        """correct number of elements, but the context_type is not in roles.py all_context_types"""
        validator_result = [
            result
            for result in TeacherValidator.validate(make_udmobj_teacher(role))
            if result is not None
        ]
        assert self.invalid_context_errstr(role, self.UNKNOWN_CONTEXT_TYPE) not in validator_result

    def test_role_and_context_variations(self):
        roles = [
            "teacher:school:{}".format(school_name),
            self.UNKNOWN_ROLE + ":school:y",
            "teacher:" + self.UNKNOWN_CONTEXT_TYPE + ":y",
            self.UNKNOWN_ROLE + ":" + self.UNKNOWN_CONTEXT_TYPE + ":y",
        ]
        expected_errstr = [
            self.invalid_role_errstr(self.UNKNOWN_ROLE + ":school:y", self.UNKNOWN_ROLE),
        ]
        validator_result = [
            result
            for result in TeacherValidator.validate(make_udmobj_teacher(roles))
            if result is not None
        ]

        assert expected_errstr == validator_result
