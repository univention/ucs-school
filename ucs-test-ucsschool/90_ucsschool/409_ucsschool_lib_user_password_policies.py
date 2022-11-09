#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.user.User password policies
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib


import pytest

from ucsschool.lib.models.user import Student
from univention.admin.uexceptions import pwToShort

# this password is so short, the global password policy will fail
# if checks are enabled
SHORT_PSW = "s"


@pytest.mark.parametrize("check_password_policies", [True, False])
def test_create_check_password_policy(check_password_policies, schoolenv):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    password = SHORT_PSW
    if check_password_policies:
        with pytest.raises(pwToShort, match=r".*The password is too short.*"):
            schoolenv.create_student(
                ou_name=ou_name, check_password_policies=check_password_policies, password=password
            )
    else:
        schoolenv.create_student(
            ou_name=ou_name, check_password_policies=check_password_policies, password=password
        )


@pytest.mark.parametrize("check_password_policies", [True, False])
def test_modify_check_password_policy(check_password_policies, schoolenv):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    stu, dn = schoolenv.create_student(ou_name=ou_name)
    stu = Student.from_dn(lo=schoolenv.lo, school=ou_name, dn=dn)
    stu.password = SHORT_PSW
    if check_password_policies:
        with pytest.raises(pwToShort, match=r".*The password is too short.*"):
            stu.modify(schoolenv.lo, check_password_policies=check_password_policies)
    else:
        stu.modify(schoolenv.lo, check_password_policies=check_password_policies)
