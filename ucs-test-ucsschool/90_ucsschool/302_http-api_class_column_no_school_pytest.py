#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## -*- coding: utf-8 -*-
## desc: Check that school names in classes column are not used
## tags: [apptest,ucsschool,ucsschool_import1,skip_in_upgrade_singleserver]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import-http-api
##   - ucs-school-import-http-api-client
## bugs: [47156]

# skipped in upgrade singleserver scenario, see Issue #1234


import logging
import random
import subprocess
import tempfile
import time
from csv import QUOTE_ALL, DictReader, DictWriter, excel

import pytest
from ldap.filter import filter_format

import univention.testing.strings as uts
from ucsschool.http_api.client import Client
from ucsschool.importer.utils.test_user_creator import TestUserCreator
from ucsschool.importer.writer.test_user_csv_exporter import HttpApiTestUserCsvExporter
from ucsschool.lib.models.group import SchoolClass
from univention.testing import utils
from univention.testing.ucsschool.importusers_http import HttpApiImportTester

TESTER = HttpApiImportTester()


class DNNameTuple:
    def __init__(self, name, dn):
        self.name = name
        self.dn = dn


def get_school_classes_for_user(ou_name, filter_s, ldap_connection):
    users = ldap_connection.lo.search(filter_s)
    if len(users) != 1:
        TESTER.fail("Could not find user from filter {!r}. Got: {!r}".format(filter_s, users))
    school_classes = SchoolClass.get_all(
        ldap_connection.lo,
        ou_name,
        filter_format("memberUid=%s", (users[0][1]["uid"][0].decode("UTF-8"),)),
    )
    TESTER.log.debug(
        "Got school classes for user %r: %r", users[0][1]["uid"][0].decode("UTF-8"), school_classes
    )
    return school_classes


@pytest.fixture()
def reset_import_http_api():
    def _reset_import_http_api():
        subprocess.call(["/bin/systemctl", "restart", "ucs-school-import-http-api"])
        time.sleep(4)

    return _reset_import_http_api


@pytest.fixture()
def create_ous(schoolenv, ucr):
    ou1 = schoolenv.create_ou("ou_A")
    ou2 = schoolenv.create_ou("ou_302", name_edudc=ucr["hostname"], use_cache=False)
    return (DNNameTuple(name=ou1[0], dn=ou1[1]), DNNameTuple(name=ou2[0], dn=ou2[1]))


@pytest.fixture()
def create_security_group(schoolenv):
    def _create_security_group(ou_dn, allowed_ou_names, user_dns):
        g1 = schoolenv.udm.create_group(
            position="cn=groups,{}".format(ou_dn),
            options=["posix", "samba", "ucsschoolImportGroup"],
            append={
                "users": user_dns,
                "ucsschoolImportRole": ["student", "teacher", "teacher_and_staff"],
                "ucsschoolImportSchool": allowed_ou_names,
            },
        )

        group = DNNameTuple(name=g1[1], dn=g1[0])

        utils.verify_ldap_object(
            group.dn,
            expected_attr={
                "cn": [group.name],
                "ucsschoolImportRole": ["student", "teacher", "teacher_and_staff"],
                "ucsschoolImportSchool": allowed_ou_names,
                "uniqueMember": user_dns,
            },
            strict=False,
            should_exist=True,
        )

        return group

    return _create_security_group


@pytest.fixture()
def testusercreator():
    def _testusercreator(ou_name):
        return TestUserCreator(
            [ou_name], students=3, teachers=3, staffteachers=2, classes=2, schools=1, email=False
        )

    return _testusercreator


@pytest.fixture()
def make_import_file():
    def _make_import_file(exporter, creator):
        tmpfile = tempfile.NamedTemporaryFile()
        exporter.dump(creator.make_users(), tmpfile.name)

        return tmpfile

    return _make_import_file


def successful_import(client, filename, ou_name, ldap_connection):
    role = random.choice(["student", "teacher", "teacher_and_staff"])

    import_job = TESTER.run_http_import_through_python_client(
        client=client,
        filename=filename,
        school=ou_name,
        role=role,
        dryrun=False,
        timeout=600,
        config=TESTER.default_config,
    )

    if import_job.status == "Finished":
        return validate_import(filename, ou_name, import_job, ldap_connection)

    TESTER.log.error(f"HTTP import failed with status {import_job.status}")
    return False


def validate_import(filename, ou_name, import_job, ldap_connection):
    with open(filename) as fp:
        reader = DictReader(fp)
        for row in reader:
            school_classes_in_ldap = get_school_classes_for_user(
                ou_name=ou_name,
                ldap_connection=ldap_connection,
                filter_s=filter_format("(&(givenName=%s)(sn=%s))", (row["Vorname"], row["Nachname"])),
            )
            school_class_names_in_csv = [
                f"{ou_name}-{schoolclass}" for schoolclass in row["Klassen"].split(",")
            ]
            for schoolclass in school_classes_in_ldap:
                if schoolclass.school != ou_name or schoolclass.name not in school_class_names_in_csv:
                    TESTER.fail(
                        "Unexpected school class name: school={!r} and name={!r}, expected {!r} "
                        "and one of {!r}.".format(
                            schoolclass.school, schoolclass.name, ou_name, school_class_names_in_csv
                        ),
                        import_job=import_job,
                    )
                    return False
        return True
    return False


@pytest.fixture()
def setup_test(
    schoolenv,
    create_ous,
    ucr,
    caplog,
    reset_import_http_api,
    create_security_group,
    testusercreator,
    make_import_file,
):
    caplog.set_level(logging.WARNING)
    has_admin_credentials = ucr["server/role"] in (
        "domaincontroller_master",
        "domaincontroller_backup",
    )
    ldap_connection = schoolenv.open_ldap_connection(admin=has_admin_credentials)

    ou_A, ou_302 = create_ous

    password = uts.random_name()
    username, user_dn = schoolenv.create_teacher(ou_302.name, password=password)

    create_security_group(ou_dn=ou_A.dn, allowed_ou_names=[ou_A.name], user_dns=[user_dn])
    create_security_group(ou_dn=ou_302.dn, allowed_ou_names=[ou_302.name], user_dns=[user_dn])

    reset_import_http_api()

    client = Client(username, password, log_level=logging.WARNING)

    test_user_creator = testusercreator(ou_A.name)
    test_user_creator.make_classes()
    csv_dialect = excel()
    csv_dialect.doublequote = True
    csv_dialect.quoting = QUOTE_ALL

    return {
        "client": client,
        "user_creator": test_user_creator,
        "ou_A": ou_A,
        "ou_302": ou_302,
        "ldap_connection": ldap_connection,
        "csv_dialect": csv_dialect,
    }


def test_base(
    schoolenv,
    create_ous,
    ucr,
    caplog,
    reset_import_http_api,
    create_security_group,
    testusercreator,
    make_import_file,
):
    has_admin_credentials = ucr["server/role"] in (
        "domaincontroller_master",
        "domaincontroller_backup",
    )
    TESTER.log.info("Getting ldap connection.")
    ldap_connection = schoolenv.open_ldap_connection(admin=has_admin_credentials)

    TESTER.log.info("Creating OUs.")
    ou_A, ou_302 = create_ous

    TESTER.log.info("Creating user for import.")
    password = uts.random_name()
    username, user_dn = schoolenv.create_teacher(ou_302.name, password=password)

    TESTER.log.info("Creating security groups.")
    create_security_group(ou_dn=ou_A.dn, allowed_ou_names=[ou_A.name], user_dns=[user_dn])
    create_security_group(ou_dn=ou_302.dn, allowed_ou_names=[ou_302.name], user_dns=[user_dn])

    TESTER.log.info("Restarting import http API")
    reset_import_http_api()

    TESTER.log.info("Setting ImportClient with previously created user credentials")
    client = Client(username, password, log_level=logging.INFO)

    TESTER.log.info("Creating test users and classes")
    test_user_creator = testusercreator(ou_A.name)
    test_user_creator.make_classes()

    TESTER.log.info("Setting csv parameters.")
    csv_dialect = excel()
    csv_dialect.doublequote = True
    csv_dialect.quoting = QUOTE_ALL

    TESTER.log.info("Creating CSV import file.")
    import_file = make_import_file(exporter=HttpApiTestUserCsvExporter(), creator=test_user_creator)

    TESTER.log.info("Starting import: Expecting success.")
    assert successful_import(
        client, import_file.name, ou_A.name, ldap_connection
    ), "Import threw an unexpected failure."


def test_ou_allowed(setup_test, make_import_file):
    TESTER.log.info("Fetching 'base' test as fixture for setting up.")
    test_params = setup_test
    TESTER.log.info("Test setup done.")
    TESTER.log.info("Creating CSV import file.")
    import_file = make_import_file(
        exporter=HttpApiTestUserCsvExporter(), creator=test_params["user_creator"]
    )
    manipulated_import_file = tempfile.NamedTemporaryFile()
    TESTER.log.info("Manipulating CSV: Writing OU name into class column.")
    with open(import_file.name) as fp_in, open(manipulated_import_file.name, "w") as fp_out:
        reader = DictReader(fp_in)
        writer = None
        for row in reader:
            row["Klassen"] = ",".join(
                ["{}-{}".format(test_params["ou_A"].name, kl) for kl in row["Klassen"].split(",")]
            )
            if not writer:
                writer = DictWriter(
                    fp_out, fieldnames=list(row.keys()), dialect=test_params["csv_dialect"]
                )
                writer.writeheader()
            writer.writerow(row)
    TESTER.log.info("Starting import: Expecting success.")
    assert successful_import(
        test_params["client"],
        manipulated_import_file.name,
        test_params["ou_A"].name,
        test_params["ldap_connection"],
    ), "Import with manipulated CSV threw an unexpected failure."
    TESTER.log.info("Import finished successfully.")


def test_ou_disallowed(setup_test, make_import_file):
    TESTER.log.info("Fetching 'base' test as fixture for setting up.")
    test_params = setup_test
    TESTER.log.info("Test setup done.")
    TESTER.log.info("Creating CSV import file.")
    import_file = make_import_file(
        exporter=HttpApiTestUserCsvExporter(), creator=test_params["user_creator"]
    )
    manipulated_import_file = tempfile.NamedTemporaryFile()
    TESTER.log.info("Manipulating CSV: Writing OU name into class column.")
    with open(import_file.name) as fp_in, open(manipulated_import_file.name, "w") as fp_out:
        reader = DictReader(fp_in)
        writer = None
        for row in reader:
            row["Klassen"] = ",".join(
                ["{}-{}".format(test_params["ou_302"].name, kl) for kl in row["Klassen"].split(",")]
            )
            if not writer:
                writer = DictWriter(
                    fp_out, fieldnames=list(row.keys()), dialect=test_params["csv_dialect"]
                )
                writer.writeheader()
            writer.writerow(row)
    TESTER.log.info("Starting import: Expecting Failure.")
    assert not successful_import(
        test_params["client"],
        manipulated_import_file.name,
        test_params["ou_302"].name,
        test_params["ldap_connection"],
    ), "Import with manipulated CSV did not fail as exepcted."
    TESTER.log.info("Import finished and failed as expected.")
