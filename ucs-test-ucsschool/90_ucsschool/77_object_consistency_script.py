#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.group.WorkGroup CRUD operations
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python-ucs-school

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./......py::test_create
#

try:
    from typing import Dict, List, Tuple
except ImportError:
    pass

import pytest

import univention.testing.ucr as ucr_test
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.share import ClassShare, MarketplaceShare, WorkGroupShare
from ucsschool.lib.models.utils import exec_cmd
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_exam_user,
    role_school_admin,
    role_school_class,
    role_school_class_share,
    role_staff,
    role_student,
    role_teacher,
)
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.udm import UDM

with ucr_test.UCSTestConfigRegistry() as ucr:
    ucr.load()
    container_admins = ucr.get("ucsschool/ldap/default/containers/admins", "admins")
    container_teachers = ucr.get("ucsschool/ldap/default/containers/teachers", "lehrer")
    container_staff = ucr.get("ucsschool/ldap/default/containers/staff", "mitarbeiter")
    container_students = ucr.get("ucsschool/ldap/default/containers/pupils", "schueler")
    ldap_base = ucr.get("ldap/base")


@pytest.fixture(scope="session")
def udm_instance():
    def _func(udm_module):
        return UDM.admin().version(1).get(udm_module)

    return _func


def exec_script(ou_name):
    script_path = "/usr/share/ucs-school-umc-diagnostic/scripts/ucs-school-object-consistency"
    rv, stdout, stderr = exec_cmd([script_path, "--school", ou_name], log=True, raise_exc=True)

    return stdout, stderr


def test_no_errors_exec_script(schoolenv, ucr_hostname):
    ou_name, ou_dn = schoolenv.create_ou()
    stdout, stderr = exec_script(ou_name)
    assert stdout == ""


def test_school_role_for_each_school(schoolenv, ucr_hostname, udm_instance):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
    student_name, student_dn = schoolenv.create_student(
        ou_name, use_cli=False, wait_for_replication=False
    )
    teacher_name, teacher_dn = schoolenv.create_teacher(
        ou_name, use_cli=False, wait_for_replication=False
    )
    teasta, teasta_dn = schoolenv.create_teacher_and_staff(
        ou_name, use_cli=False, wait_for_replication=False
    )

    staff_role_string = create_ucsschool_role_string(role_staff, ou_name)
    student_role_string = create_ucsschool_role_string(role_student, ou_name)

    user_mod = udm_instance("users/user")
    obj = user_mod.get(student_dn)
    obj.props.ucsschoolRole = staff_role_string
    obj.save()

    obj = user_mod.get(teacher_dn)
    obj.props.ucsschoolRole = student_role_string
    obj.save()

    obj = user_mod.get(teasta_dn)
    obj.props.ucsschoolRole = staff_role_string
    obj.save()

    stdout, stderr = exec_script(ou_name)
    entries = stdout.split("\n\n")
    for entry in entries:
        if student_dn in entry:
            assert "User does not have UCS@School Role student:school:" in entry
        elif teacher_dn in entry:
            assert "User does not have UCS@School Role teacher:school:" in entry
        elif teasta_dn in entry:
            assert "User does not have UCS@School Role teacher:school:" in entry


def test_group_membership_for_each_school(create_ou, schoolenv, udm_instance):
    ou_name, ou_dn = create_ou()
    student_name, student_dn = schoolenv.create_student(
        ou_name, use_cli=False, wait_for_replication=False
    )
    teasta, teasta_dn = schoolenv.create_teacher_and_staff(
        ou_name, use_cli=False, wait_for_replication=False
    )
    student_group_dn = "cn={0}-{1},cn=groups,ou={1},{2}".format(container_students, ou_name, ldap_base)
    staff_group_dn = "cn={0}-{1},cn=groups,ou={1},{2}".format(container_staff, ou_name, ldap_base)

    group_mod = udm_instance("groups/group")
    obj = group_mod.get(student_group_dn)
    obj.props.users = [student_dn]
    obj.delete()

    obj = group_mod.get(staff_group_dn)
    obj.props.users = [teasta_dn]
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    entries = stdout.split("\n\n")
    for entry in entries:
        if student_dn in entry:
            assert "Not member of group cn=schueler-" in entry
        if teasta_dn in entry:
            assert "Not member of group cn=mitarbeiter-" in entry


def test_mandatory_group_existence_for_each_school(create_ou, schoolenv, udm_instance):
    ou_name, ou_dn = create_ou(use_cache=False)

    # check global group seperately
    group_dc_edu = "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ldap_base)
    group_domain_users = "cn=Domain Users {0},cn=groups,ou={0},{1}".format(ou_name, ldap_base)
    group_klassenarbeit = "cn=OU{0}-Klassenarbeit,cn=ucsschool,cn=groups,{1}".format(ou_name, ldap_base)

    group_mod = udm_instance("groups/group")
    obj = group_mod.get(group_dc_edu)
    obj.delete()

    obj = group_mod.get(group_domain_users)
    obj.delete()

    obj = group_mod.get(group_klassenarbeit)
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    entries = stdout.split("\n\n")
    for entry in entries:
        if group_dc_edu in entry:
            assert "Mandatory group cn=DC-Edukativnetz" in entry
        if group_domain_users in entry:
            assert "Mandatory group cn=Domain Users" in entry
        if group_klassenarbeit in entry:
            assert "Mandatory group cn=OU{}-Klassenarbeit".format(ou_name) in entry


def test_mandatory_container_existence_for_each_school(create_ou, schoolenv, udm_instance):
    ou_name, ou_dn = create_ou(use_cache=False)
    search_base = SchoolSearchBase([ou_name])

    container_mod = udm_instance("container/cn")
    obj = container_mod.get(search_base.examUsers)
    obj.delete()

    obj = container_mod.get(search_base.classes)
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    entries = stdout.split("\n\n")
    for entry in entries:
        if search_base.examUsers in entry:
            assert "Mandatory container cn=examusers" in entry
        if search_base.classes in entry:
            assert "Mandatory container cn=klassen" in entry


def test_class_share_without_corresponding_class(create_ou, schoolenv, udm_instance):
    ou_name, ou_dn = create_ou()
    class_name, grp_dn = schoolenv.create_school_class(ou_name, wait_for_replication=False)

    groups_mod = udm_instance("groups/group")
    obj = groups_mod.get(grp_dn)
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    entries = stdout.split("\n\n")
    for entry in entries:
        if "cn={},cn=klassen,cn=shares".format(class_name) in entry:
            assert "Corresponding class {}".format(class_name) in entry


def test_martkplatz_share_existence_for_each_school(create_ou, udm_instance):
    ou_name, ou_dn = create_ou(use_cache=False)
    marktplatz_share = "cn=Marktplatz,cn=shares,{}".format(ou_dn)

    shares_mod = udm_instance("shares/share")
    obj = shares_mod.get(marktplatz_share)
    obj.delete()

    stdout, stderr = exec_script(ou_name)
    entries = stdout.split("\n\n")
    for entry in entries:
        if marktplatz_share in entry:
            assert "does not exist." in entry


if __name__ == "__main__":
    assert pytest.main(["-l", "-v", __file__]) == 0
