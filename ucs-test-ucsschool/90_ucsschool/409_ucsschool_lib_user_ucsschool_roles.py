#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.user.User ucsschool_roles
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib


import pytest

from ucsschool.lib.models.attributes import ValidationError
from ucsschool.lib.models.user import Student


@pytest.mark.parametrize(
    "extra_role,allowed",
    [
        ("my:funny:role", True),
        ("not:funny", False),
        ("123", False),
        ("my:school:not_allowed", False),
    ],
)
def test_create_arbitrary_extra_roles(extra_role, allowed, schoolenv):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    if extra_role == "duplicate_role":
        extra_role = "student:school:{}".format(ou_name)
    expected_error = r"Role has bad format" if "school" not in extra_role else r"Unknown role"
    if not allowed:
        with pytest.raises(ValidationError, match=expected_error):
            schoolenv.create_student(ou_name=ou_name, ucsschool_roles=[extra_role])
    else:
        schoolenv.create_student(ou_name=ou_name, ucsschool_roles=[extra_role])


@pytest.mark.parametrize(
    "extra_role,allowed",
    [
        ("my:funny:role", True),
        ("not:funny", False),
        ("123", False),
        ("my:school:existing_school", False),
    ],
)
def test_modify_keep_arbitrary_extra_roles(extra_role, allowed, schoolenv):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    stu, dn = schoolenv.create_student(ou_name=ou_name)
    stu = Student.from_dn(lo=schoolenv.lo, school=ou_name, dn=dn)
    extra_role = extra_role.replace("existing_school", ou_name)
    stu.ucsschool_roles.append(extra_role)
    expected_error = r"Role has bad format" if "school" not in extra_role else r"Unknown role"
    if not allowed:
        with pytest.raises(ValidationError, match=expected_error):
            stu.modify(schoolenv.lo)
    else:
        stu.modify(schoolenv.lo)


@pytest.mark.parametrize(
    "extra_role,allowed",
    [
        ("my:funny:role", True),
        ("not:funny", False),
        ("123", False),
        ("my:school:existing_school", False),
    ],
)
def test_move_keep_arbitrary_extra_roles(extra_role, allowed, schoolenv):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(
        2, name_edudc=schoolenv.ucr["hostname"]
    )
    stu, dn = schoolenv.create_student(ou_name=ou_name)
    stu = Student.from_dn(lo=schoolenv.lo, school=ou_name, dn=dn)
    extra_role = extra_role.replace("existing_school", ou_name)
    stu.ucsschool_roles.append(extra_role)
    success = stu.change_school(ou_name2, lo=schoolenv.lo)
    assert success is True
    users = Student.get_all(schoolenv.lo, ou_name2, "uid={}".format(stu.name))
    assert len(users) == 1
    user = users[0]
    if allowed:
        assert extra_role in user.ucsschool_roles
    else:
        assert extra_role not in user.ucsschool_roles
