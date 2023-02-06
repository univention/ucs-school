#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: valid hostname
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: []

from __future__ import print_function

import subprocess

import pytest

import univention.testing.strings as uts
from univention.testing import utils
from ucsschool.lib.models.attributes import ValidationError
from univention.testing.ucsschool.school import School
from univention.testing.umc import Client

INVALID_CHARS_CLI = [
    "ä",
    "ö",
    "ü",
    "ß",
    "%",
    "§",
    "$",
    "!",
    "&",
    "[",
    "]",
    "{",
    "}",
    "<",
    ">",
    "^",
    "\\",
    "?",
    "~",
]
INVALID_CHARS = INVALID_CHARS_CLI + ["_"]
INVALID_STARTING_CHARS = INVALID_CHARS + ["-"]
INVALID_ENDING_CHARS = INVALID_STARTING_CHARS


def test_valid_hostname(ucr, schoolenv):
    host = ucr.get("ldap/master")
    client = Client(host)
    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw
    client.authenticate(admin, passwd)
    if ucr.is_true("ucsschool/singlemaster"):
        pytest.skip("This test is only for Multi Server Environments")

    # Using ucs-school-lib
    def process_school(school, dc_name, should_fail=True):
        try:
            ou, oudn = schoolenv.create_ou(ou_name=school, name_edudc=dc_name, use_cache=False)
            assert (
                not should_fail
            ), "Creating a school(%s) with dc_name=%s was possible, expected to fail)" % (
                school,
                dc_name,
            )
            print(
                "Creating a school(%s) with dc_name=%s, expected to succeed"
                % (
                    school,
                    dc_name,
                )
            )
        except ValidationError as ex:
            assert should_fail and "dc_name" in str(
                ex
            ), "Creating a school(%s) with dc_name=%s, expected to fail: %s)" % (
                school,
                dc_name,
                str(ex),
            )

    # Using ucs-school-import
    def process_school_cli(school, dc_name, should_fail=True):
        cmd = ["/usr/share/ucs-school-import/scripts/create_ou", "--verbose", school, dc_name]
        try:
            subprocess.check_call(cmd)
            assert (
                not should_fail
            ), "Creating a school(%s) cli with dc_name=%s was unexpectedly successful" % (
                school,
                dc_name,
            )
        except subprocess.CalledProcessError:
            assert should_fail, "Creating a school(%s) cli with dc_name=%s failed unexpectedly" % (
                school,
                dc_name,
            )

    # Using UMCP
    def process_school_umcp(school, dc_name, should_fail=True):
        created = False
        try:
            school.create()
            created = True
        except AssertionError as ex:
            assert should_fail and "DC Name:" in str(
                ex
            ), "Creating a school(%s) umcp with dc_name=%s, expected to fail: %s)" % (
                school.name,
                dc_name,
                str(ex),
            )
        else:
            assert (
                not should_fail
            ), "Creating a school(%s) umcp with dc_name=%s was unexpectedly successful" % (
                school.name,
                dc_name,
            )
        finally:
            if created:
                school.remove()

    # Checking legal chars in dc_name
    for _count in range(5):
        dc_name = uts.random_name()
        school = uts.random_name()
        process_school(school, dc_name, should_fail=False)
        process_school_cli(school, dc_name, should_fail=False)
        school = School(dc_name=dc_name, ucr=ucr, connection=client)
        process_school_umcp(school, dc_name, should_fail=False)

    # Checking illegal char in the beginning of the dc_name
    for char in INVALID_STARTING_CHARS:
        dc_name = "%s%s" % (char, uts.random_name(6))
        school = uts.random_name()
        process_school(school, dc_name)
        process_school_cli(school, dc_name)
        school = School(dc_name=dc_name, ucr=ucr, connection=client)
        process_school_umcp(school, dc_name)

    # Checking illegal char in the middle of the dc_name
    for char in INVALID_CHARS:
        dc_name = "%s%s%s" % (uts.random_name(4), char, uts.random_name(3))
        school = uts.random_name()
        process_school(school, dc_name)
        school = School(dc_name=dc_name, ucr=ucr, connection=client)
        process_school_umcp(school, dc_name)

    for char in INVALID_CHARS_CLI:
        dc_name = "%s%s%s" % (uts.random_name(4), char, uts.random_name(3))
        school = uts.random_name()
        process_school_cli(school, dc_name)

    # Checking illegal char in the end of the dc_name
    for char in INVALID_ENDING_CHARS:
        dc_name = "%s%s" % (uts.random_name(6), char)
        school = uts.random_name()
        process_school(school, dc_name)
        process_school_cli(school, dc_name)
        school = School(dc_name=dc_name, ucr=ucr, connection=client)
        process_school_umcp(school, dc_name)
