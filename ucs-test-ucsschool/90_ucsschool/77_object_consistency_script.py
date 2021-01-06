#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
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
import univention.testing.udm
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

with ucr_test.UCSTestConfigRegistry() as ucr:
    ucr.load()
    container_admins = ucr.get("ucsschool/ldap/default/containers/admins", "admins")
    container_teachers = ucr.get("ucsschool/ldap/default/containers/teachers", "lehrer")
    container_staff = ucr.get("ucsschool/ldap/default/containers/staff", "mitarbeiter")
    container_students = ucr.get("ucsschool/ldap/default/containers/pupils", "schueler")
    ldap_base = ucr.get("ldap/base")


@pytest.fixture
def exec_script():
    script_path = "./usr/share/ucs-school-umc-diagnostic/scripts/ucs-school-object-consistency"
    rv, stdout, stderr = exec_cmd([script_path], log=True, raise_exc=True)

    return stdout, stderr


def test_school_role_for_each_school(create_ou, schoolenv, exec_script):
    ou_name, ou_dn = create_ou()
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

    # student gets staff role
    udm.modify_object("users/user", dn=student_dn, modify={"ucsschoolRole": staff_role_string})
    # teacher gets student role
    udm.modify_object("users/user", dn=teacher_dn, modify={"ucsschoolRole": student_role_string})
    # teacher and staff gets only staff role
    udm.modify_object("users/user", dn=teasta_dn, modify={"ucsschoolRole": staff_role_string})

    exec_script()
    # check stdout for containing the two role errors


def test_group_membership_for_each_school(create_ou, schoolenv, exec_script):
    ou_name, ou_dn = create_ou()
    student_name, student_dn = schoolenv.create_student(
        ou_name, use_cli=False, wait_for_replication=False
    )
    teasta, teasta_dn = schoolenv.create_teacher_and_staff(
        ou_name, use_cli=False, wait_for_replication=False
    )
    student_group_dn = "cn={0}-{1},cn=groups,ou={0},{2}".format(container_staff, ou_name, ldap_base)
    staff_group_dn = "cn={0}-{1},cn=groups,ou={0},{2}".format(container_staff, ou_name, ldap_base)

    # remove student from student group
    udm.modify_object("groups/group", dn=student_group_dn, remove={"users": student_dn})
    # remove teacher and staff from staff group
    udm.modify_object("groups/group", dn=staff_group_dn, remove={"users": teasta_dn})

    exec_script()
    # check stdout for containing the two group errors


def test_mandatory_group_existence_for_each_school(create_ou, exec_script):
    ou_name, ou_dn = create_ou()

    group_dc_edu = "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ldap_base)
    group_domain_users = "cn=Domain Users {0},cn=groups,ou={0},{1}".format(ou_name, ldap_base)
    group_klassenarbeit = "cn=OU{0}-Klassenarbeit,cn=ucsschool,cn=groups,{1}".format(ou_name, ldap_base)

    udm.remove_object("groups/group", dn=group_dc_edu)
    udm.remove_object("groups/group", dn=group_domain_users)
    udm.remove_object("groups/group", dn=group_klassenarbeit)

    exec_script()
    # check stdout for containing the three group errors


def test_mandatory_container_existence_for_each_school(create_ou, exec_script):
    ou_name, ou_dn = create_ou()
    search_base = SchoolSearchBase([ou_name])

    udm.remove_object("container/cn", dn=search_base.examUsers)
    udm.remove_object("container/cn", dn=search_base.classes)

    exec_script()


def test_class_shares(create_ou, schoolenv, exec_script):
    ou_name, ou_dn = create_ou()
    class_name = schoolenv.create_school_class(ou_name, wait_for_replication=False)
    share_dn = "cn={0},cn=klassen,cn=shares,ou={1},{2}".format(class_name, ou_name, ldap_base)

    udm.remove_object("shares/share", dn=share_dn)

    exec_script()


def test_martkplatz_share_existence_for_each_school(create_ou, exec_script):
    ou_name, ou_dn = create_ou()

    marktplatz_share = "cn=Marktplatz,cn=shares,{}".format(ou_dn)
    udm.remove_object("shares/share", dn=marktplatz_share)

    exec_script()
