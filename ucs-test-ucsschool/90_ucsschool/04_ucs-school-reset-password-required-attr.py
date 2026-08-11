#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-reset-password-required-attr
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1,ucs-school-umc-users]
## exposure: dangerous
## packages: [ucs-school-umc-users]

from __future__ import print_function

import pytest

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.config_registry import ucr
from univention.lib.umc import BadRequest, HTTPError
from univention.testing import utils
from univention.testing.umc import Client

INIT_PASSWORD = "univention"


def auth(host, username, password):
    try:
        client = Client(host)
        return client.authenticate(username, password)
    except HTTPError as exc:
        return exc.response


@pytest.mark.xfail(
    condition=ucr.get("server/role") == "domaincontroller_slave",
    reason="Currently we can't fix missing attributes on school replicas :(",
    raises=BadRequest,
)
def test_empty_required_attr():
    with utu.UCSTestSchool() as schoolenv:
        schoolenv.ucr.load()
        host = schoolenv.ucr.get("hostname")
        schoolName, _ = schoolenv.create_ou(name_edudc=host)
        # Only the student must be missing the extended attribute - that is what this test is
        # about. The attribute below is required for *every* users/user object, so while it
        # exists, no user lacking it can be modified: ready() raises insufficientInformation
        # before _ldap_pre_modify() gets a chance to fill in the default. That also hits the
        # S4 connector, which back-syncs the attributes Samba writes when a user is created or
        # authenticates, and it then logs a traceback (failing 01_var_log_tracebacks).
        # So: create the student first and let its back-sync finish before the attribute
        # exists, and create the teacher afterwards, so UDM gives it the default value.
        student, studentDn = schoolenv.create_user(schoolName)
        utils.wait_for_replication()
        utils.wait_for_connector_replication()
        properties_extended_attribute = {
            "position": f"cn=custom attributes,{schoolenv.udm.UNIVENTION_CONTAINER}",
            "name": uts.random_name(),
            "shortDescription": uts.random_string(),
            "CLIName": uts.random_name(),
            "module": "users/user",
            "objectClass": "univentionFreeAttributes",
            "ldapMapping": "univentionFreeAttribute15",
            "default": uts.random_name(),
            "valueRequired": 1,
            "syntax": "string",
            "mayChange": 1,
        }
        schoolenv.udm.create_object(
            "settings/extended_attribute",
            **properties_extended_attribute,
        )
        teacher, teacherDn = schoolenv.create_user(schoolName, is_teacher=True)
        schoolenv.udm.verify_udm_object(
            "users/user",
            teacherDn,
            expected_properties={
                properties_extended_attribute["CLIName"]: [properties_extended_attribute["default"]],
            },
        )
        client = Client(host, teacher, INIT_PASSWORD)
        options = {
            "userDN": studentDn,
            "newPassword": uts.random_string(),
            "nextLogin": False,
        }
        flavor = "student"
        schoolenv.udm.verify_udm_object(
            "users/user", studentDn, expected_properties={properties_extended_attribute["CLIName"]: []}
        )
        result = client.umc_command("schoolusers/password/reset", options, flavor).result
        assert result
        schoolenv.udm.verify_udm_object(
            "users/user",
            studentDn,
            expected_properties={
                properties_extended_attribute["CLIName"]: [properties_extended_attribute["default"]],
            },
        )
        utils.wait_for_replication()
        utils.wait_for_connector_replication()
        auth_response = auth(host, student, options["newPassword"])
        assert auth_response.status == 200
