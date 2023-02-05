#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: test _filter_users function
## roles: [domaincontroller_master]
## tags: [ucsschool,apptest,ucsschool_base1]
## bugs: [54040]
## exposure: dangerous
## packages: [ucs-school-umc-groups]

from unittest.mock import patch

import pytest

import univention.admin.uexceptions as udm_exceptions
from univention.testing import utils
from ucsschool.lib.models import User
from ucsschool.lib.school_umc_base import Display
from univention.lib.umc import BadRequest
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.schoolgroups import _filter_users
from univention.testing.ucsschool.computerroom import UmcComputer
from univention.testing.ucsschool.user import User as TestUser
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client

flavors = ["workgroup-admin", "class", "workgroup"]
test_user = User(name="test_user", schools=["test_school"], dn="test_user_dn")


@pytest.mark.parametrize("flavor", flavors)
@patch.object(User, "from_dn", side_effect=udm_exceptions.noObject)
@patch.object(MODULE, "error")
def test_filter_users_fails_if_not_user_exist(user_from_dn_mock, module_error_mock, flavor):
    result = _filter_users(["fake_user"], "fake_school", flavor)
    user_from_dn_mock.assert_called()
    module_error_mock.assert_called()
    assert result == []


@pytest.mark.parametrize("flavor", flavors)
@patch.object(Display, "user", return_value="test_user_2")
@patch.object(User, "get_udm_object")
@patch.object(User, "from_dn", return_value=User(schools=[], name="test_user_2"))
def test_filter_users_if_not_schools(
    user_from_dn_mock,
    user_get_udm_object_mock,
    display_user_mock,
    flavor,
):
    with pytest.raises(UMC_Error):
        _filter_users(["fake_user"], "test_school", flavor)

    user_from_dn_mock.assert_called()
    user_get_udm_object_mock.assert_called()
    display_user_mock.assert_called()


@pytest.mark.parametrize("flavor", flavors)
@patch.object(User, "is_teacher", return_value=False)
@patch.object(User, "is_staff", return_value=False)
@patch.object(User, "is_administrator", return_value=False)
@patch.object(User, "is_student", return_value=False)
@patch.object(Display, "user", return_value=test_user.name)
@patch.object(User, "get_udm_object")
@patch.object(User, "from_dn", return_value=test_user)
def test_filter_users_fails_if_user_has_no_role_in_school(
    user_from_dn_mock,
    user_get_udm_object_mock,
    display_user_mock,
    user_is_student_mock,
    user_is_administrator_mock,
    user_is_staff_mock,
    user_is_teacher_mock,
    flavor,
):
    with pytest.raises(UMC_Error):
        _filter_users(["fake_user"], "test_school", flavor)

    user_from_dn_mock.assert_called()
    user_get_udm_object_mock.assert_called()
    display_user_mock.assert_called()
    if flavor == "class":
        user_is_teacher_mock.assert_called()
    elif flavor == "workgroup":
        user_is_student_mock.assert_called()
    else:
        user_is_student_mock.assert_called()
        user_is_administrator_mock.assert_called()
        user_is_staff_mock.assert_called()
        user_is_teacher_mock.assert_called()


@pytest.mark.parametrize("flavor", flavors)
@patch.object(User, "is_teacher", return_value=True)
@patch.object(User, "is_staff", return_value=True)
@patch.object(User, "is_administrator", return_value=True)
@patch.object(User, "is_student", return_value=True)
@patch.object(User, "from_dn", return_value=test_user)
def test_filter_users_does_not_filter_if_all_ok(
    user_from_dn_mock,
    user_is_student_mock,
    user_is_administrator_mock,
    user_is_staff_mock,
    user_is_teacher_mock,
    flavor,
):
    result = _filter_users([test_user], "test_school", flavor)
    user_from_dn_mock.assert_called()

    if flavor == "class":
        user_is_teacher_mock.assert_called()
    elif flavor == "workgroup":
        user_is_student_mock.assert_called()
    else:
        user_is_student_mock.assert_called()

    assert result == [test_user.dn]


def test_add_student_from_other_school_to_workgroup_fails(ucr, schoolenv):
    host = ucr.get("hostname")
    school, _ = schoolenv.create_ou(name_edudc=host)
    connection = Client.get_test_connection()
    work_group = Workgroup(school, connection=connection)
    work_group.create()
    utils.wait_for_replication()
    work_group.verify_exists(group_should_exist=True, share_should_exist=True)

    school_student = TestUser(school, "student", None, connection=connection)
    school_student.create()

    # adding a student from the workgroup's same school should work
    add_student_from_school = connection.umc_command(
        "schoolgroups/put",
        flavor="workgroup-admin",
        options=[
            {
                "object": {
                    "$dn$": work_group.dn(),
                    "members": [school_student.dn],
                }
            }
        ],
    ).result

    assert add_student_from_school

    other_school, _ = schoolenv.create_ou(name_edudc="other")
    other_school_student = TestUser(other_school, "student", None, connection=connection)
    other_school_student.create()

    # adding a student from another school should fail
    with pytest.raises(BadRequest):
        connection.umc_command(
            "schoolgroups/put",
            flavor="workgroup-admin",
            options=[
                {
                    "object": {
                        "$dn$": work_group.dn(),
                        "members": [other_school_student.dn],
                    }
                }
            ],
        )


def test_non_user_objects_are_not_removed(ucr, schoolenv, lo):
    host = ucr.get("hostname")
    school, _ = schoolenv.create_ou(name_edudc=host)
    connection = Client.get_test_connection()
    work_group = Workgroup(school, connection=connection)
    work_group.create()
    computer = UmcComputer(school, "windows")
    computer.create()
    utils.wait_for_replication()
    work_group.verify_exists(group_should_exist=True, share_should_exist=True)
    users = [computer.dn()]

    result = _filter_users(users, school, "workgroup-admin", lo)
    assert result == users

    add_computer = connection.umc_command(
        "schoolgroups/put",
        flavor="workgroup-admin",
        options=[
            {
                "object": {
                    "$dn$": work_group.dn(),
                    "members": users,
                }
            }
        ],
    ).result

    assert add_computer
