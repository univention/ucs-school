#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check that models of users cannot be changed.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [python3-ucsschool-lib]

import univention.testing.strings as uts
from ucsschool.lib.models.base import WrongModel
from ucsschool.lib.models.user import Staff, Student, Teacher, TeachersAndStaff, User

cls_role_map = {
    "Staff": ["is_staff"],
    "Student": ["is_student"],
    "Teacher": ["is_teacher"],
    "TeachersAndStaff": ["is_staff", "is_teacher"],
}
role_funcs = ["is_staff", "is_student", "is_teacher", "is_administrator"]
cls_options_map = {
    "Staff": ["ucsschoolStaff"],
    "Student": ["ucsschoolStudent"],
    "Teacher": ["ucsschoolTeacher"],
    "TeachersAndStaff": ["ucsschoolStaff", "ucsschoolTeacher"],
}
options = ["ucsschoolStaff", "ucsschoolStudent", "ucsschoolTeacher"]


def test_user_model_change(schoolenv, ucr):
    ou, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    print("*** Created school environment. ou='{}' oudn='{}'.".format(ou, oudn))

    lo = schoolenv.open_ldap_connection()
    users = {}
    for cls in [Staff, Student, Teacher, TeachersAndStaff]:
        print("*** Creating a {}...".format(cls))
        user = cls(
            school=ou,
            name=uts.random_name(),
            firstname=uts.random_name(),
            lastname=uts.random_name(),
        )
        user.create(lo)
        users[cls] = user

    print("*** Testing *.is_*()...")
    for user in users.values():
        for func in role_funcs:
            res = getattr(user, func)(lo)
            if res:
                assert func in cls_role_map[user.__class__.__name__]
            else:
                assert func not in cls_role_map[user.__class__.__name__]

    print("*** Testing options...")
    for user in users.values():
        udm_obj = user.get_udm_object(lo)
        for opt in options:
            if (opt in udm_obj.options and opt not in cls_options_map[user.__class__.__name__]) or (
                opt not in udm_obj.options and opt in cls_options_map[user.__class__.__name__]
            ):
                raise AssertionError(
                    "UDM object of user {} has options {}, but should have {}.\n (Ignoring non-ucsschool* options.)".format(
                        user, udm_obj.options, cls_options_map[user.__class__.__name__]
                    )
                )

    for cls in [User, Staff, Student, Teacher, TeachersAndStaff]:
        print("*** Testing {}.from_dn()...".format(cls.__name__))
        for users_cls, user in users.items():
            try:
                ucs_user = cls.from_dn(user.dn, ou, lo)
                assert users_cls == ucs_user.__class__, "{} should be of class {}.".format(
                    ucs_user, users_cls
                )
            except WrongModel:
                assert users_cls != cls, "User of type {} should have been found.".format(cls)
