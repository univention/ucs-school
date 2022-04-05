import sys

sys.path.insert(1, "modules")
from ucsschool.lib.models.utils import ucr
from ucsschool.lib.models.validator import TeacherValidator
from ucsschool.lib.roles import all_roles


def make_udmobj(school_role):
    dnbase = ucr.get("ldap/base")
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
            "password": "{crypt}$6$p1A727prgEviftBf$4BRbc894OXOC2PteaOQt410zwVUTvCdBf6eXNB29WpXktgCsDEzLTVoxGi1Sk9ExIYivmNsbx5FUuVOD2N46T/",
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
                "cn=lehrer-mustermannschule,cn=groups,ou=MustermannSchule,{0}".format(dnbase),
                "cn=Domain Users MustermannSchule,cn=groups,ou=MustermannSchule,{0}".format(dnbase),
            ],
            "primaryGroup": "cn=Domain Users MustermannSchule,cn=groups,ou=MustermannSchule,{0}".format(
                dnbase
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
            "ucsschoolRole": [school_role],
        },
        "dn": "uid=mmustermann,cn=lehrer,cn=users,ou=MustermannSchule,{0}".format(dnbase),
        "position": "cn=lehrer,cn=users,ou=MustermannSchule,{0}".format(dnbase),
        "options": {"ucsschoolTeacher": True, "default": True},
    }


class TestRoleValidation:

    ROLE = "foo"
    CONTEXT_TYPE = "bar"
    
    def test_valid(self):
        role_str = "teacher:school:MustermannSchule"
        result = TeacherValidator.validate(make_udmobj(role_str))
        expected_errstrs = [self.split_errstr(role_str),
                            self.destructuring_errstr(role_str),
                            self.invalid_role_errstr(role_str, TestRoleValidation.ROLE),
                            self.invalid_context_errstr(role_str, TestRoleValidation.CONTEXT_TYPE)]
        assert set(result).isdisjoint(set(expected_errstrs))

    def split_errstr(self, role_str):
        return "Invalid UCS@school role string: {!r}.".format(role_str)
    
    def test_wrong_number_of_elems_1(self):
        """
        Can't split at all!
        """
        role_str = "teacher-bad-format"
        assert self.split_errstr(role_str) in TeacherValidator.validate(
            make_udmobj(role_str)
        )

    def destructuring_errstr(self, role_str):
        return "Invalid UCS@school role string: {!r}.".format(role_str)
    
    def test_wrong_number_of_elems_2(self):
        """
        splits 4 items, we destructure this into 3 items!
        """
        role_str = "a:s:d:f"
        assert self.destructuring_errstr(role_str) in TeacherValidator.validate(
            make_udmobj(role_str)
        )

    def invalid_role_errstr(self, role_str, role):
        return "The role string {!r} includes the unknown role {!r}.".format(
            role_str, role
        )
    
    def test_invalid_role_name(self):
        """
        correct number of elements, but the role is not in roles.py all_roles
        """
        role_str = TestRoleValidation.ROLE + ":x:y"
        assert self.invalid_role_errstr(role_str, TestRoleValidation.ROLE) in TeacherValidator.validate(make_udmobj(role_str))

    def invalid_context_errstr(self, role_str, context_type):
        return "The role string {!r} includes the unknown context type {!r}.".format(
            role_str, context_type
        )
    
    def test_invalid_context_type(self):
        """
        correct number of elements, but the context_type is not in roles.py all_context_types
        """
        role_str = "teacher:" + TestRoleValidation.CONTEXT_TYPE + ":x"
        assert self.invalid_context_errstr(role_str, TestRoleValidation.CONTEXT_TYPE) in TeacherValidator.validate(make_udmobj(role_str))
