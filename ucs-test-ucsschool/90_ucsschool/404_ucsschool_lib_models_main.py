#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.__main__
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

import sys
from typing import Dict, List, Tuple  # noqa: F401

import pytest

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.utils import exec_cmd
from univention.testing import utils
from univention.testing.ucr import UCSTestConfigRegistry
from univention.testing.ucsschool.importusers import Person


@pytest.fixture(scope="session")
def cmd_line_role():
    def _func(role):
        if role == "teacher_and_staff":
            return "TeachersAndStaff"
        else:
            return "{}{}".format(role[0].upper(), role[1:])

    return _func


def test_list_models():
    cmd = [sys.executable, "-m", "ucsschool.lib.models", "list-models"]
    rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
    # space saving list (black would make it completely vertical):
    for model in (
        "AnyComputer AnyDHCPService BasicGroup BasicSchoolGroup ClassShare ComputerRoom Container "
        "DHCPDNSPolicy DHCPServer DHCPService DHCPSubnet DNSReverseZone ExamStudent Group GroupShare "
        "IPComputer ImportStaff ImportStudent ImportTeacher ImportTeachersAndStaff MacComputer "
        "MailDomain MarketplaceShare Network Policy School SchoolAdmin SchoolClass SchoolComputer "
        "SchoolDC SchoolDCSlave SchoolGroup Staff Student Teacher TeachersAndStaff "
        "UMCPolicy WindowsComputer WorkGroup WorkGroupShare"
    ).split():
        assert model in stdout


def test_list_models_details():
    # checking just a few samples
    cmd = [sys.executable, "-m", "ucsschool.lib.models", "list-models", "--attributes"]
    rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
    assert (
        "Student\n    birthday\n    disabled\n    email\n    expiration_date\n    firstname [required]\n"
        "    lastname [required]\n    name [required]\n    password\n    school [required]\n    "
        "school_classes\n    schools\n    ucsschool_roles"
    ) in stdout
    assert (
        "ClassShare\n    name [required]\n    school [required]\n    school_group [required]\n    "
        "ucsschool_roles"
    ) in stdout
    assert (
        "ImportTeachersAndStaff\n    birthday\n    disabled\n    email\n    expiration_date\n    "
        "firstname [required]\n    lastname [required]\n    name [required]\n    password\n    "
        "record_uid\n    school [required]\n    school_classes\n    schools\n    source_uid\n    "
        "ucsschool_roles"
    ) in stdout
    assert (
        "School\n    administrative_servers\n    class_share_file_server\n    dc_name\n    "
        "dc_name_administrative\n    display_name\n    educational_servers\n    home_share_file_server"
        "\n    name [required]\n    ucsschool_roles"
    ) in stdout
    assert (
        "WindowsComputer\n    inventory_number\n    ip_address [required]\n    mac_address [required]\n"
        "    name [required]\n    school [required]\n    subnet_mask\n    ucsschool_roles\n    zone"
    ) in stdout


def test_list(cmd_line_role, ucr_hostname, ucr_ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr_hostname)
        # list one user by school and name
        user_names = {}
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            create_func = getattr(schoolenv, "create_{}".format(role))
            user_name, user_dn = create_func(ou_name, wait_for_replication=False)
            user_names.setdefault(role, []).append(user_name)
            cmd = [
                sys.executable,
                "-m",
                "ucsschool.lib.models",
                "list",
                cmd_line_role(role),
                "--name",
                user_name,
                "--school",
                ou_name,
            ]
            rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
            assert "name: '{}'".format(user_name) in stdout
            assert "school: '{}'".format(ou_name) in stdout
            if role == "teacher_and_staff":
                assert (
                    "ucsschool_roles: ['teacher:school:{0}', 'staff:school:{0}']".format(ou_name)
                    in stdout
                    or "ucsschool_roles: ['staff:school:{0}', 'teacher:school:{0}']".format(ou_name)
                    in stdout
                )
            else:
                assert "ucsschool_roles: ['{}:school:{}']".format(role, ou_name) in stdout

        # list multiple users for same OU
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            create_func = getattr(schoolenv, "create_{}".format(role))
            user_name, user_dn = create_func(ou_name, wait_for_replication=False)
            user_names.setdefault(role, []).append(user_name)
            cmd = [
                sys.executable,
                "-m",
                "ucsschool.lib.models",
                "list",
                cmd_line_role(role),
                "--school",
                ou_name,
            ]
            rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
            for user_name in user_names[role]:
                assert user_name in stdout
                assert (
                    "{}(name='{}', school='{}', dn=".format(cmd_line_role(role), user_name, ou_name)
                    in stdout
                )

        # list school_classes from multiple OUs
        school_classes = {}  # type: Dict[str, List[Tuple[str, str]]]
        for ou in (ou_name, ou_name2):
            for _ in range(3):
                school_class_name = "{}-{}".format(ou, uts.random_username())
                cmd = [
                    sys.executable,
                    "-m",
                    "ucsschool.lib.models",
                    "--debug",
                    "create",
                    "schoolclass",
                    "--name",
                    school_class_name,
                    "--school",
                    ou,
                ]
                rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
                dn = "cn={},cn=klassen,cn=schueler,cn=groups,ou={},{}".format(
                    school_class_name, ou, ucr_ldap_base
                )
                assert dn in stdout
                school_classes.setdefault(ou, []).append((school_class_name, dn))
        cmd = [
            sys.executable,
            "-m",
            "ucsschool.lib.models",
            "list",
            "schoolclass",
        ]
        rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
        for ou, classes in school_classes.items():
            for name, dn in classes:
                assert "SchoolClass(name='{}', school='{}', dn='{}')".format(name, ou, dn) in stdout


def test_create_user(cmd_line_role, ucr_hostname, ucr_ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(ou_name, role)
            person.set_random_birthday()
            cmd = [
                sys.executable,
                "-m",
                "ucsschool.lib.models",
                "--debug",
                "create",
                cmd_line_role(role),
                "--name",
                person.username,
                "--school",
                person.school,
                "--set",
                "firstname",
                person.firstname,
                "--set",
                "lastname",
                person.lastname,
                "--set",
                "email",
                person.mail,
                "--set",
                "birthday",
                person.birthday,
            ]
            rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
            container = {
                "student": "schueler",
                "teacher": "lehrer",
                "staff": "mitarbeiter",
                "teacher_and_staff": "lehrer und mitarbeiter",
            }[role]
            dn = "uid={},cn={},cn=users,ou={},{}".format(
                person.username, container, ou_name, ucr_ldap_base
            )
            assert dn in stdout
            utils.verify_ldap_object(
                dn,
                expected_attr={
                    "uid": [person.username],
                    "givenName": [person.firstname],
                    "sn": [person.lastname],
                    "mailPrimaryAddress": [person.mail],
                    "ucsschoolSchool": [ou_name],
                    "univentionBirthday": [person.birthday],
                },
                strict=False,
                should_exist=True,
            )


@pytest.mark.parametrize(
    "windows_check_enabled",
    ["", "true", "false"],
    ids=lambda v: "ucsschool/validation/username/windows-check={}".format(v),
)
def test_create_user_windows_reserved_name(
    cmd_line_role, ucr_hostname, ucr_ldap_base, windows_check_enabled
):
    with utu.UCSTestSchool() as schoolenv, UCSTestConfigRegistry() as ucr_test:
        ucr_test.handler_set(
            ["ucsschool/validation/username/windows-check={}".format(windows_check_enabled)]
        )
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            container = {
                "student": "schueler",
                "teacher": "lehrer",
                "staff": "mitarbeiter",
                "teacher_and_staff": "lehrer und mitarbeiter",
            }[role]
            username = "com1.{}".format(uts.random_username())
            person = Person(ou_name, role, username=username)
            person.set_random_birthday()
            cmd = [
                sys.executable,
                "-m",
                "ucsschool.lib.models",
                "--debug",
                "create",
                cmd_line_role(role),
                "--name",
                person.username,
                "--school",
                person.school,
                "--set",
                "firstname",
                person.firstname,
                "--set",
                "lastname",
                person.lastname,
                "--set",
                "email",
                person.mail,
                "--set",
                "birthday",
                person.birthday,
            ]
            dn = "uid={},cn={},cn=users,ou={},{}".format(
                person.username, container, ou_name, ucr_ldap_base
            )
            rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=False)
            if windows_check_enabled in ["", "false"]:
                # creating users which do not adhere to the windows naming conventions
                # is deprecated and with 5.2 this test should be adjusted accordingly
                assert rv == 0
                assert person.username in stdout

                utils.verify_ldap_object(dn, should_exist=True, retry_count=3, delay=5)
            else:
                assert rv != 0
                assert "ucsschool.lib.models.attributes.ValidationError" in stderr
                assert "May not be a Windows reserved name" in stderr

                assert person.username in stdout

                utils.verify_ldap_object(dn, should_exist=False, retry_count=3, delay=5)


def test_create_school_class(ucr_hostname, ucr_ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
        user_name1, user_dn1 = schoolenv.create_student(ou_name, wait_for_replication=False)
        user_name2, user_dn2 = schoolenv.create_teacher(ou_name, wait_for_replication=False)
        school_class_name = "{}-{}".format(ou_name, uts.random_username())
        description = uts.random_username()
        cmd = [
            sys.executable,
            "-m",
            "ucsschool.lib.models",
            "--debug",
            "create",
            "schoolclass",
            "--name",
            school_class_name,
            "--school",
            ou_name,
            "--append",
            "users",
            user_dn1,
            "--append",
            "users",
            user_dn2,
            "--set",
            "description",
            description,
        ]
        rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
        dn = "cn={},cn=klassen,cn=schueler,cn=groups,ou={},{}".format(
            school_class_name, ou_name, ucr_ldap_base
        )
        assert dn in stdout
        utils.verify_ldap_object(
            dn,
            expected_attr={
                "cn": [school_class_name],
                "description": [description],
                "ucsschoolRole": ["school_class:school:{}".format(ou_name)],
                "uniqueMember": [user_dn1, user_dn2],
            },
            strict=False,
            should_exist=True,
        )


def test_modify(cmd_line_role, ucr_hostname, ucr_ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            create_func = getattr(schoolenv, "create_{}".format(role))
            user_name, user_dn = create_func(ou_name, wait_for_replication=False)
            person = Person(ou_name, role)
            person.set_random_birthday()

            # get by DN and modify
            cmd = [
                sys.executable,
                "-m",
                "ucsschool.lib.models",
                "--debug",
                "modify",
                cmd_line_role(role),
                "--dn",
                user_dn,
                "--set",
                "firstname",
                person.firstname,
                "--set",
                "lastname",
                person.lastname,
                "--set",
                "email",
                person.mail,
                "--set",
                "birthday",
                person.birthday,
            ]
            rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
            assert user_dn in stdout
            utils.verify_ldap_object(
                user_dn,
                expected_attr={
                    "uid": [user_name],
                    "givenName": [person.firstname],
                    "sn": [person.lastname],
                    "mailPrimaryAddress": [person.mail],
                    "ucsschoolSchool": [ou_name],
                    "univentionBirthday": [person.birthday],
                },
                strict=False,
                should_exist=True,
            )

            # get by school+name and modify
            person = Person(ou_name, role)
            person.set_random_birthday()
            cmd = [
                sys.executable,
                "-m",
                "ucsschool.lib.models",
                "--debug",
                "modify",
                cmd_line_role(role),
                "--school",
                ou_name,
                "--name",
                user_name,
                "--set",
                "firstname",
                person.firstname,
                "--set",
                "lastname",
                person.lastname,
                "--set",
                "email",
                person.mail,
                "--set",
                "birthday",
                person.birthday,
            ]
            rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
            assert user_dn in stdout
            utils.verify_ldap_object(
                user_dn,
                expected_attr={
                    "uid": [user_name],
                    "givenName": [person.firstname],
                    "sn": [person.lastname],
                    "mailPrimaryAddress": [person.mail],
                    "ucsschoolSchool": [ou_name],
                    "univentionBirthday": [person.birthday],
                },
                strict=False,
                should_exist=True,
            )

        # modify with --append
        school_class_name = "{}-{}".format(ou_name, uts.random_username())
        description = uts.random_username()
        cmd = [
            sys.executable,
            "-m",
            "ucsschool.lib.models",
            "--debug",
            "create",
            "schoolclass",
            "--name",
            school_class_name,
            "--school",
            ou_name,
            "--set",
            "description",
            description,
        ]
        rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
        dn = "cn={},cn=klassen,cn=schueler,cn=groups,ou={},{}".format(
            school_class_name, ou_name, ucr_ldap_base
        )
        assert dn in stdout
        utils.verify_ldap_object(
            dn,
            expected_attr={
                "cn": [school_class_name],
                "description": [description],
                "ucsschoolRole": ["school_class:school:{}".format(ou_name)],
                "uniqueMember": [],
            },
            strict=False,
            should_exist=True,
        )
        description = uts.random_username()
        user_name1, user_dn1 = schoolenv.create_student(ou_name, wait_for_replication=False)
        user_name2, user_dn2 = schoolenv.create_teacher(ou_name, wait_for_replication=False)
        cmd = [
            sys.executable,
            "-m",
            "ucsschool.lib.models",
            "--debug",
            "modify",
            "schoolclass",
            "--name",
            school_class_name,
            "--school",
            ou_name,
            "--set",
            "description",
            description,
            "--append",
            "users",
            user_dn1,
            "--append",
            "users",
            user_dn2,
        ]
        rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
        assert dn in stdout
        utils.verify_ldap_object(
            dn,
            expected_attr={
                "cn": [school_class_name],
                "description": [description],
                "ucsschoolRole": ["school_class:school:{}".format(ou_name)],
                "uniqueMember": [user_dn1, user_dn2],
            },
            strict=False,
            should_exist=True,
        )


def test_delete(cmd_line_role, ucr_hostname):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            create_func = getattr(schoolenv, "create_{}".format(role))
            user_name, user_dn = create_func(ou_name, wait_for_replication=False)
            cmd = [
                sys.executable,
                "-m",
                "ucsschool.lib.models",
                "--debug",
                "delete",
                cmd_line_role(role),
                "--dn",
                user_dn,
            ]
            rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
            assert user_dn in stdout
            utils.verify_ldap_object(user_dn, should_exist=False)
