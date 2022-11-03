import sys

import pytest  # isort: skip

sys.path.insert(1, "modules")
from ucsschool.lib.models.school import School  # noqa: E402
from ucsschool.lib.models.utils import ucr  # noqa: E402
from ucsschool.lib.models.validator import TeacherValidator  # noqa: E402

ldapbase = ucr.get("ldap/base")
School.get_search_base("MustermannSchule")
School._search_base_cache["MustermannSchule"]._schoolDN = "ou=MustermannSchule,{}".format(ldapbase)


def make_udmobj(school_roles):
    return {
        "props": {
            "username": "mmustermann",
            "uidNumber": "2016",
            "gidNumber": "5098",
            "firstname": "Max",
            "lastname": "Mustermann",
            "gecos": "Max Mustermann",
            "displayName": "Max Mustermann",
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
            "departmentNumber": ["MustermannSchule"],
            "employeeType": "",
            "homePostalAddress": [],
            "physicalDeliveryOfficeName": "",
            "homeTelephoneNumber": [],
            "mobileTelephoneNumber": [],
            "pagerTelephoneNumber": [],
            "birthday": "",
            "unixhome": "/home/MustermannSchule/lehrer/mmustermann",
            "shell": "/bin/bash",
            "sambahome": "\\\\dc0\\mmustermann",
            "scriptpath": "ucs-school-logon.vbs",
            "profilepath": "%LOGONSERVER%\\%USERNAME%\\windows-profiles\\default",
            "homedrive": "I:",
            "sambaRID": "5032",
            "groups": [
                "cn=lehrer-mustermannschule,cn=groups,ou=MustermannSchule,{0}".format(ldapbase),
                "cn=Domain Users MustermannSchule,cn=groups,ou=MustermannSchule,{0}".format(ldapbase),
            ],
            "primaryGroup": "cn=Domain Users MustermannSchule,cn=groups,ou=MustermannSchule,{0}".format(
                ldapbase
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
            "school": ["MustermannSchule"],
            "ucsschoolSourceUID": "",
            "ucsschoolRecordUID": "",
            "ucsschoolPurgeTimestamp": "",
            "ucsschoolRole": school_roles,
        },
        "dn": "uid=mmustermann,cn=lehrer,cn=users,ou=MustermannSchule,{0}".format(ldapbase),
        "position": "cn=lehrer,cn=users,ou=MustermannSchule,{0}".format(ldapbase),
        "options": {"ucsschoolTeacher": True, "default": True},
    }


class TestRoleValidation:

    UNKNOWN_ROLE = "foo"
    UNKNOWN_CONTEXT_TYPE = "bar"

    def test_valid(self):
        role_str = ["teacher:school:MustermannSchule"]
        result = TeacherValidator.validate(make_udmobj(role_str))
        expected_errstrs = [
            self.split_errstr(role_str),
            self.destructuring_errstr(role_str),
            self.invalid_role_errstr(role_str, TestRoleValidation.UNKNOWN_ROLE),
            self.invalid_context_errstr(role_str, TestRoleValidation.UNKNOWN_CONTEXT_TYPE),
        ]
        assert set(result).isdisjoint(set(expected_errstrs))

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

    # tests
    def test_wrong_number_of_elems_1(self):
        """
        Can't split at all!
        """
        roles = ["teacher-bad-format"]
        assert self.split_errstr(roles[0]) in TeacherValidator.validate(make_udmobj(roles))

    def test_wrong_number_of_elems_2(self):
        """
        splits 4 items, we destructure this into 3 items!
        """
        roles = ["a:s:d:f"]
        assert self.destructuring_errstr(roles[0]) in TeacherValidator.validate(make_udmobj(roles))

    @pytest.mark.parametrize(
        "role",
        [
            UNKNOWN_ROLE + ":school:y",
            UNKNOWN_ROLE + ":" + UNKNOWN_CONTEXT_TYPE + ":y",
        ],
    )
    def test_invalid_role_name(self, role):
        """
        correct number of elements, but the role is not in roles.py all_roles
        """
        validator_result = [
            result for result in TeacherValidator.validate(make_udmobj([role])) if result is not None
        ]

        if role.split(":")[1] != TestRoleValidation.UNKNOWN_CONTEXT_TYPE:
            assert self.invalid_role_errstr(role, role.split(":")[0]) in validator_result
        else:
            assert ["is missing roles ['teacher:school:MustermannSchule']"] == validator_result

    @pytest.mark.parametrize(
        "role",
        [
            UNKNOWN_ROLE + ":" + UNKNOWN_CONTEXT_TYPE + ":x",
            "teacher:school:x",
        ],
    )
    def test_unknown_context_type_is_valid(self, role):
        """
        correct number of elements, but the context_type is not in roles.py all_context_types
        """
        validator_result = [
            result for result in TeacherValidator.validate(make_udmobj(role)) if result is not None
        ]
        assert (
            self.invalid_context_errstr(role, TestRoleValidation.UNKNOWN_CONTEXT_TYPE)
            not in validator_result
        )

    def test_role_and_context_variations(self):
        roles = [
            "teacher:school:MustermannSchule",
            TestRoleValidation.UNKNOWN_ROLE + ":school:y",
            "teacher:" + TestRoleValidation.UNKNOWN_CONTEXT_TYPE + ":y",
            TestRoleValidation.UNKNOWN_ROLE + ":" + TestRoleValidation.UNKNOWN_CONTEXT_TYPE + ":y",
        ]
        expected_errstr = [
            self.invalid_role_errstr(
                TestRoleValidation.UNKNOWN_ROLE + ":school:y", TestRoleValidation.UNKNOWN_ROLE
            ),
        ]
        validator_result = [
            result for result in TeacherValidator.validate(make_udmobj(roles)) if result is not None
        ]

        assert expected_errstr == validator_result
