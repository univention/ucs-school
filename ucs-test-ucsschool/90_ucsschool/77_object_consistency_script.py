#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.group.WorkGroup CRUD operations
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

from typing import Tuple  # noqa: F401

import pytest

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
from ucsschool.lib.models.user import Student
from ucsschool.lib.models.utils import exec_cmd, ucr as lib_ucr
from ucsschool.lib.roles import create_ucsschool_role_string, role_staff, role_student, role_teacher
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing import utils
from univention.udm import UDM

with ucr_test.UCSTestConfigRegistry() as ucr:
    ucr.load()
    groupprefix_admins = ucr.get("ucsschool/ldap/default/groupprefix/admins", "admins-")
    groupprefix_teachers = ucr.get("ucsschool/ldap/default/groupprefix/teachers", "lehrer-")
    groupprefix_staff = ucr.get("ucsschool/ldap/default/groupprefix/staff", "mitarbeiter-")
    groupprefix_students = ucr.get("ucsschool/ldap/default/groupprefix/pupils", "schueler-")
    ldap_base = ucr.get("ldap/base")


@pytest.fixture(scope="session")
def udm_instance():
    def _func(udm_module):
        return UDM.admin().version(1).get(udm_module)

    return _func


def exec_script(ou_name):
    script_path = "/usr/share/ucs-school-umc-diagnostic/scripts/ucs-school-object-consistency"
    if ou_name:
        rv, stdout, stderr = exec_cmd([script_path, "--school", ou_name], log=True, raise_exc=True)
    else:
        rv, stdout, stderr = exec_cmd([script_path], log=True, raise_exc=True)

    return stdout, stderr


def assert_error_msg_in_script_output(script_output, dn, error_msg):
    for line in script_output.split("\n\n"):
        if dn in line:
            assert error_msg in line
            break
    else:
        raise AssertionError("No line containing DN {!r} found.".format(dn))


def assert_error_msg_not_in_script_output(script_output, dn, error_msg):
    for line in script_output.split("\n\n"):
        if dn in line:
            assert error_msg not in line


def test_no_errors_exec_script(schoolenv, ucr_hostname):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname, use_cache=False)
    stdout, stderr = exec_script(ou_name)
    assert stdout == ""


def input_ids_wrong_school_role(role_and_bad_value):  # type: (Tuple[str, str, str]) -> str
    role_str, bad_value, expected = role_and_bad_value
    return role_str


@pytest.mark.parametrize(
    # the third value is the expected missing role. It is necessary for combined roles
    # E.g.: create teacher_and_staff; its (only!) role is set to staff -> teacher is missing
    "role_and_bad_value",
    (
        ("student", role_staff, "student"),
        ("teacher", role_student, "teacher"),
        ("staff", role_teacher, "staff"),
        ("teacher_and_staff", role_staff, "teacher"),
    ),
    ids=input_ids_wrong_school_role,
)
def test_wrong_school_role(schoolenv, ucr_hostname, udm_instance, role_and_bad_value):
    role_str, bad_value, expected = role_and_bad_value
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
    create_func = getattr(schoolenv, "create_{}".format(role_str))

    name, dn = create_func(ou_name, wait_for_replication=False)
    bad_role = create_ucsschool_role_string(bad_value, ou_name)

    user_mod = udm_instance("users/user")
    obj = user_mod.get(dn)
    obj.props.ucsschoolRole = [bad_role]
    obj.save()

    stdout, stderr = exec_script(ou_name)
    expected_error = "User does not have UCS@school Role {}:school".format(expected)
    assert_error_msg_in_script_output(stdout, dn, expected_error)


def test_wrong_school_role_for_each_school(schoolenv, ucr_hostname, udm_instance):
    # this test is intentionally only applied for checking the student role.
    # test_wrong_school_role() already ensures that this should also work for all other roles.
    (ou_name1, ou_dn1), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr_hostname)
    student_name, student_dn = schoolenv.create_student(ou_name1, wait_for_replication=False)
    student = Student.from_dn(student_dn, ou_name1, schoolenv.lo)
    student.schools.append(ou_name2)
    student.modify(schoolenv.lo)
    utils.verify_ldap_object(
        student_dn,
        expected_attr={
            "uid": [student_name],
            "ucsschoolSchool": [ou_name1, ou_name2],
            "ucsschoolRole": [
                create_ucsschool_role_string("student", ou)
                for role in student.default_roles
                for ou in [ou_name1, ou_name2]
            ],
        },
        strict=False,
        should_exist=True,
    )
    bad_role1 = create_ucsschool_role_string(role_staff, ou_name1)
    bad_role2 = create_ucsschool_role_string(role_staff, ou_name2)

    user_mod = udm_instance("users/user")
    obj = user_mod.get(student_dn)
    obj.props.ucsschoolRole = [bad_role1, bad_role2]
    obj.save()

    stdout, stderr = exec_script(None)
    expected_error = "User does not have UCS@school Role {}:school".format("student")
    assert_error_msg_in_script_output(stdout, student_dn, expected_error)


def input_ids_wrong_group_membership(role_and_prefix):  # type: (Tuple[str, str, str]) -> str
    role_str, prefix, expected = role_and_prefix
    return role_str


@pytest.mark.parametrize(
    "role_and_prefix",
    (
        ("student", groupprefix_students, "Not member of group cn={}".format(groupprefix_students)),
        ("teacher", groupprefix_teachers, "Not member of group cn={}".format(groupprefix_teachers)),
        ("staff", groupprefix_staff, "Not member of group cn={}".format(groupprefix_staff)),
        ("teacher_and_staff", groupprefix_staff, "Not member of group cn={}".format(groupprefix_staff)),
        ("school_admin", groupprefix_admins, "Not member of group cn={}".format(groupprefix_admins)),
    ),
    ids=input_ids_wrong_group_membership,
)
def test_wrong_group_membership(create_ou, schoolenv, udm_instance, ucr_hostname, role_and_prefix):
    role_str, prefix, expected_error = role_and_prefix
    ou_name, ou_dn = create_ou(name_edudc=ucr_hostname)
    create_func = getattr(schoolenv, "create_{}".format(role_str))
    name, user_dn = create_func(ou_name, wait_for_replication=False)

    if role_str == "school_admin":
        group_dn = "cn={0}{1},cn=ouadmins,cn=groups,{2}".format(prefix, ou_name, ldap_base)
    else:
        group_dn = "cn={0}{1},cn=groups,ou={1},{2}".format(prefix, ou_name, ldap_base)

    group_mod = udm_instance("groups/group")
    obj = group_mod.get(group_dn)
    obj.props.users.remove(user_dn)
    obj.save()

    stdout, stderr = exec_script(ou_name)
    assert_error_msg_in_script_output(stdout, user_dn, expected_error)


@pytest.mark.parametrize(
    "role_and_prefix",
    (
        ("student", groupprefix_students, "Not member of group cn={}".format(groupprefix_students)),
        ("teacher", groupprefix_teachers, "Not member of group cn={}".format(groupprefix_teachers)),
        ("staff", groupprefix_staff, "Not member of group cn={}".format(groupprefix_staff)),
        ("teacher_and_staff", groupprefix_staff, "Not member of group cn={}".format(groupprefix_staff)),
    ),
    ids=input_ids_wrong_group_membership,
)
def test_case_insensitive_group_membership(
    create_ou, schoolenv, udm_instance, ucr_hostname, role_and_prefix
):
    role_str, prefix, expected_error = role_and_prefix
    ou_name, ou_dn = create_ou(name_edudc=ucr_hostname)
    create_func = getattr(schoolenv, "create_{}".format(role_str))
    name, user_dn = create_func(ou_name, wait_for_replication=False)
    user_mod = udm_instance("users/user")
    obj = user_mod.get(user_dn)
    obj.props.groups = [group.lower() for group in list(obj.props.groups)]
    obj.save()
    stdout, stderr = exec_script(ou_name)
    assert_error_msg_not_in_script_output(stdout, user_dn, expected_error)


@pytest.mark.parametrize(
    # the 2nd value is the expected missing role. It is necessary for combined roles
    # E.g.: create teacher_and_staff; its (only!) role is set to staff -> teacher is missing
    "role_and_expected_value",
    (
        ("student", role_student),
        ("teacher", role_teacher),
        ("staff", role_staff),
        ("teacher_and_staff", role_teacher),
    ),
    ids=lambda role_and_expected_value: role_and_expected_value[0],
)
def test_case_insensitive_school_roles(schoolenv, ucr_hostname, udm_instance, role_and_expected_value):
    role_str, expected = role_and_expected_value
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
    create_func = getattr(schoolenv, "create_{}".format(role_str))

    name, dn = create_func(ou_name, wait_for_replication=False)
    user_mod = udm_instance("users/user")
    obj = user_mod.get(dn)
    obj.props.ucsschoolRole = [r.lower() for r in obj.props.ucsschoolRole]
    obj.save()

    stdout, stderr = exec_script(ou_name)
    expected_error = "User does not have UCS@school Role {}:school".format(expected)
    assert_error_msg_not_in_script_output(stdout, dn, expected_error)


def input_ids_not_existing_mandatory_group(group):  # type: (Tuple[str, str]) -> str
    group, expected = group
    return group.split(",", 1)[0].rsplit("=", 1)[-1]


@pytest.mark.parametrize(
    "group",
    (
        pytest.param(
            ("cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{ldap_base}", "cn=DC-Edukativnetz"),
            marks=pytest.mark.skip(
                reason="Deleting this group breaks the replication for ALL educative domain servers"
            ),
        ),
        ("cn=Domain Users {ou},cn=groups,ou={ou},{ldap_base}", "cn=Domain Users"),
        ("cn=OU{ou}-Klassenarbeit,cn=ucsschool,cn=groups,{ldap_base}", "cn=OU{ou}-Klassenarbeit"),
    ),
    ids=input_ids_not_existing_mandatory_group,
)
def test_not_existing_mandatory_group(udm_instance, ucr_hostname, group, create_ou):
    ou_name, ou_dn = create_ou(use_cache=False)

    group_dn, expected_error = group
    group_dn = group_dn.format(ou=ou_name, ldap_base=ldap_base)
    expected_error = expected_error.format(ou=ou_name)

    group_mod = udm_instance("groups/group")
    obj = group_mod.get(group_dn)
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    assert_error_msg_in_script_output(stdout, group_dn, expected_error)


@pytest.mark.parametrize(
    "group",
    (
        ("cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{ldap_base}", "cn=DC-Edukativnetz"),
        ("cn=OU{ou}-DC-Edukativnetz,cn=ucsschool,cn=groups,{ldap_base}", "cn=OU{ou}-DC-Edukativnetz"),
    ),
    ids=input_ids_not_existing_mandatory_group,
)
def test_missing_membership_group(udm_instance, ucr_hostname, group, create_ou):
    name_edudc = "dcschool77"
    ou_name, ou_dn = create_ou(use_cache=False, name_edudc=name_edudc)
    dn_edudc = "cn={},cn=dc,cn=server,cn=computers,{}".format(name_edudc, ou_dn)

    group_dn, expected_error = group
    group_dn = group_dn.format(ou=ou_name, ldap_base=ldap_base)
    expected_error = expected_error.format(ou=ou_name)

    group_mod = udm_instance("groups/group")
    obj = group_mod.get(group_dn)
    obj.props.hosts.remove(dn_edudc)
    obj.save()

    stdout, stderr = exec_script(ou_name)
    assert_error_msg_in_script_output(stdout, group_dn, expected_error)


def input_ids_not_existing_mandatory_container(containers):  # type: (Tuple[str, str]) -> str
    container, expected = containers
    return container


@pytest.mark.parametrize(
    "containers",
    (("examUsers", "Mandatory container cn=examusers"), ("classes", "Mandatory container cn=klassen")),
    ids=input_ids_not_existing_mandatory_container,
)
def test_not_existing_mandatory_container(create_ou, udm_instance, ucr_hostname, containers):
    container_type, expected_error = containers
    ou_name, ou_dn = create_ou(name_edudc=ucr_hostname, use_cache=False)
    search_base = SchoolSearchBase([ou_name])
    get_container = getattr(search_base, container_type)

    container_mod = udm_instance("container/cn")
    obj = container_mod.get(get_container)
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    assert_error_msg_in_script_output(stdout, get_container, expected_error)


def test_class_share_without_corresponding_class(create_ou, schoolenv, udm_instance, ucr_hostname):
    ou_name, ou_dn = create_ou(name_edudc=ucr_hostname)
    class_name, grp_dn = schoolenv.create_school_class(ou_name, wait_for_replication=False)

    groups_mod = udm_instance("groups/group")
    obj = groups_mod.get(grp_dn)
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    class_dn = "cn={},cn=klassen,cn=shares".format(class_name)
    expected_error = "Corresponding class {}".format(class_name)
    assert_error_msg_in_script_output(stdout, class_dn, expected_error)


def test_not_existing_martkplatz_share(create_ou, udm_instance, ucr_hostname):
    ou_name, ou_dn = create_ou(name_edudc=ucr_hostname, use_cache=False)
    marktplatz_share = "cn=Marktplatz,cn=shares,{}".format(ou_dn)

    shares_mod = udm_instance("shares/share")
    obj = shares_mod.get(marktplatz_share)
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    assert_error_msg_in_script_output(stdout, marktplatz_share, "does not exist")


def test_no_errors_exec_script_no_default_group_prefix(schoolenv, ucr_hostname, ucr):
    ucr.handler_set(
        [
            "ucsschool/ldap/default/groupprefix/admins={groupprefix_admins}-".format(
                groupprefix_admins=uts.random_string()
            )
        ]
    )
    lib_ucr.load()
    ou_name, ou_dn = schoolenv.create_ou(use_cache=False, name_edudc=ucr_hostname)
    stdout, stderr = exec_script(ou_name)
    assert stdout == ""
