#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: UDM hook prevents creating and modifying user objects with forbidden option combinations
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41351]

import pytest

import univention.testing.strings as uts
import univention.testing.utils as utils
from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff
from ucsschool.lib.roles import create_ucsschool_role_string
from univention.admin.uexceptions import invalidOptions
from univention.testing.udm import UCSTestUDM_CreateUDMObjectFailed

blacklisted_option_combinations = {
    "ucsschoolAdministrator": {"ucsschoolExam", "ucsschoolStudent"},
    "ucsschoolExam": {"ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"},
    "ucsschoolStaff": {"ucsschoolExam", "ucsschoolStudent"},
    "ucsschoolStudent": {"ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"},
    "ucsschoolTeacher": {"ucsschoolExam", "ucsschoolStudent"},
}


def test_invalid_option_combinations(ucr, udm_session, schoolenv):
    print("*** Testing creation...\n*")
    for kls, bad_options in blacklisted_option_combinations.items():
        for bad_option in bad_options:
            with pytest.raises(UCSTestUDM_CreateUDMObjectFailed):
                udm_session.create_user(options=[kls, bad_option])

    print("*\n*** Testing modification...\n*")
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    lo = schoolenv.open_ldap_connection(admin=True)
    for kls, ldap_cls in [
        (ExamStudent, "ucsschoolExam"),
        (Staff, "ucsschoolStaff"),
        (Student, "ucsschoolStudent"),
        (Teacher, "ucsschoolTeacher"),
        (TeachersAndStaff, "ucsschoolAdministrator"),
    ]:
        for bad_option in blacklisted_option_combinations[ldap_cls]:
            print("*** Creating {} and trying to add option {}...".format(kls.type_name, bad_option))
            user = kls(
                name=uts.random_username(),
                school=ou_name,
                firstname=uts.random_name(),
                lastname=uts.random_name(),
            )
            user.create(lo)
            utils.verify_ldap_object(
                user.dn,
                expected_attr={
                    "uid": [user.name],
                    "ucsschoolRole": [
                        create_ucsschool_role_string(role, ou_name) for role in user.default_roles
                    ],
                },
                strict=False,
                should_exist=True,
            )

            udm_user = user.get_udm_object(lo)
            udm_user.options.append(bad_option)
            with pytest.raises(invalidOptions):
                udm_user.modify(lo)
            user.remove(lo)
