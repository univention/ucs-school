#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## -*- coding: utf-8 -*-
## desc: Check all roles through the python client
## tags: [apptest,ucsschool,ucsschool_import1,ucs-school-import]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import-http-api
##   - ucs-school-import-http-api-client
## bugs: [45749]

import pprint
from collections import namedtuple

import pytest
from ldap.filter import filter_format

import univention.testing.strings as uts
from ucsschool.http_api.client import Client

OuType = namedtuple("OU", ["name", "dn"])


@pytest.fixture
def create_test_ou(schoolenv, ucr_hostname):
    return OuType(*schoolenv.create_ou(name_edudc=ucr_hostname))


@pytest.mark.parametrize("role", ["student", "teacher", "staff", "teacher_and_staff", "legal_guardian"])
def test_role_via_api(schoolenv, lo, create_test_ou, create_http_import_security_group, role):
    ou = create_test_ou
    password = uts.random_string()

    print("*** Creating user...")
    username, user_dn = schoolenv.create_teacher(ou.name, password=password)

    print("*** Create import-permission groups...")
    group = create_http_import_security_group(
        ou_dn=ou.dn, allowed_ou_names=[ou.name], roles=[role], user_dns=[user_dn]
    )
    for dn, obj in lo.search(
        filter_format("(&(objectClass=ucsschoolImportGroup)(memberUid=%s))", (username,))
    ):
        print("%s: %s", dn, pprint.pformat(obj))

    client = Client(username, password, log_level=Client.LOG_RESPONSE)

    print("*** Checking schools via Python-API...")
    schools = client.school.list()
    expected_schools = {ou.name}
    received_schools = {s.name for s in schools}
    print(f"Expected schools: {expected_schools!r}")
    print(f"Received schools: {received_schools!r}")
    assert expected_schools == received_schools

    print("*** Checking roles via Python-API...")
    expected_roles = {role}
    roles_from_api = client.school.get(ou.name).roles
    received_roles = {r.name for r in roles_from_api}
    print(f"Expected roles: {expected_roles!r}")
    print(f"Received roles: {received_roles!r}")
    assert expected_roles == received_roles

    schoolenv.udm.remove_object("groups/group", wait_for_replication=True, dn=group.dn)
