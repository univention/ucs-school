#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Users(schools) module
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1,skip_in_large_schoolenv]
## exposure: dangerous
## packages: [ucs-school-umc-wizards]

# Test is skipped in large schoolenv, see univention/ucsschool#1235

from __future__ import print_function

from copy import deepcopy

import pytest
from ldap.filter import filter_format

import univention.testing.strings as uts
from univention.config_registry import handler_set
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import get_mail_domain
from univention.testing.ucsschool.klasse import Klasse
from univention.testing.ucsschool.user import User
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client


def _test(student_classes, teacher_classes, schools, ucr, remove_from_school=None, connection=None):
    print("\n>>>> Creating 4 users...\n")
    users = []

    user = User(
        school=schools[0],
        role="student",
        school_classes=deepcopy(student_classes),
        schools=schools,
        connection=connection,
    )
    user.create()
    user.verify()
    user.check_get()
    users.append(user)

    user = User(
        school=schools[0],
        role="teacher",
        school_classes=deepcopy(teacher_classes),
        schools=schools,
        connection=connection,
    )
    user.create()
    user.verify()
    user.check_get()
    users.append(user)

    user = User(
        school=schools[0], role="staff", school_classes={}, schools=schools, connection=connection
    )
    user.create()
    user.verify()
    user.check_get()
    users.append(user)

    user = User(
        school=schools[0],
        role="teacher_staff",
        school_classes=deepcopy(teacher_classes),
        schools=schools,
        connection=connection,
    )
    user.create()
    user.verify()
    user.check_get()
    users.append(user)

    users[0].check_query([users[0].dn, users[1].dn])

    print("\n>>>> Editing and removing (remove_from_school=%r) 4 users...\n" % (remove_from_school,))
    for num, user in enumerate(users):
        new_attrs = {
            "email": "%s@%s" % (uts.random_name(), get_mail_domain()),
            "firstname": "first_name%d" % num,
            "lastname": "last_name%d" % num,
            "password": uts.random_string(20),
        }
        user.edit(new_attrs)
        wait_for_drs_replication(filter_format("cn=%s", (user.username,)))

        # Passwords are not returned via the get request, so it is not expected
        new_attrs["password"] = None
        user.check_get(expected_attrs=new_attrs)
        user.verify()
        school_classes = deepcopy(user.school_classes)
        try:
            school_classes.pop(remove_from_school)
        except KeyError:
            pass
        user.remove(remove_from_school)
        # importusers expects that the class groups are moved as well as the user during a school change
        # schoolwizard does not do that -> reset the school classes that got modified during the school
        # move see bug #47208
        user.school_classes = school_classes
        utils.wait_for_replication()
        user.verify()

    return users


def test_users_module(schoolenv, ucr):
    umc_connection = Client.get_test_connection(ucr.get("ldap/master"))
    (ou, oudn), (ou2, oudn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr.get("hostname"))
    class_01 = Klasse(school=ou, connection=umc_connection)
    class_01.create()
    class_01.verify()
    class_02 = Klasse(school=ou, connection=umc_connection)
    class_02.create()
    class_02.verify()
    student_classes = {ou: ["%s-%s" % (ou, class_01.name)]}
    teacher_classes = {ou: ["%s-%s" % (ou, class_01.name), "%s-%s" % (ou, class_02.name)]}

    print("\n>>>> Testing module with users in 1 OU ({}).\n".format(ou))
    _test(student_classes, teacher_classes, [ou], ucr, ou, connection=umc_connection)

    class_03 = Klasse(school=ou2, connection=umc_connection)
    class_03.create()
    class_03.verify()
    student_classes = {
        ou: ["%s-%s" % (ou, class_01.name)],
        ou2: ["%s-%s" % (ou2, class_03.name)],
    }
    teacher_classes = {
        ou: ["%s-%s" % (ou, class_01.name), "%s-%s" % (ou, class_02.name)],
        ou2: ["%s-%s" % (ou2, class_03.name)],
    }

    print("\n>>>> Testing module with users in 2 OUs (primary: {} secondary: {}).".format(ou, ou2))
    print(">>>> Removing user from primary OU first.\n")
    users = _test(student_classes, teacher_classes, [ou, ou2], ucr, ou, connection=umc_connection)

    for user in users:
        print((user.username, user.role, user.school, user.schools))
        wait_for_drs_replication(filter_format("cn=%s", (user.username,)))
        user.get()
        user.verify()
        user.remove()
        wait_for_drs_replication(filter_format("cn=%s", (user.username,)), should_exist=False)
        utils.wait_for_replication()
        user.verify()

    print("\n>>>> Testing module with users in 2 OUs (primary: {} secondary: {}).".format(ou, ou2))
    print(">>>> Removing user from secondary OU first.\n")
    users = _test(student_classes, teacher_classes, [ou, ou2], ucr, ou2, connection=umc_connection)

    for user in users:
        wait_for_drs_replication(filter_format("cn=%s", (user.username,)))
        user.get()
        user.verify()
        user.remove()
        utils.wait_for_replication()
        wait_for_drs_replication(filter_format("cn=%s", (user.username,)), should_exist=False)
        user.verify()


def test_users_module_workgroups_attribute(schoolenv, ucr):
    umc_connection = Client.get_test_connection(ucr.get("ldap/master"))
    (ou, oudn) = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    wg = Workgroup(school=ou, name="testwg", connection=umc_connection)
    wg.create()
    user_workgroups = {ou: ["%s-%s" % (ou, wg.name)]}
    cl = Klasse(school=ou, connection=umc_connection)
    cl.create()
    user = User(
        school=ou,
        role="student",
        school_classes={ou: [cl.name]},
        workgroups=deepcopy(user_workgroups),
        schools=[ou],
        connection=umc_connection,
    )
    print(
        "\n>>>> Going to create user with workgroups (user: {} workgroups: {}).".format(
            user.dn, user_workgroups
        )
    )
    user.create()
    user.get()
    user_dict = user.get()
    assert user_dict["workgroups"] == user_workgroups
    print(
        "\n>>>> Cleaning up user, workgroup and class (user: {} workgroup: {}, class: {}).".format(
            user.dn, wg.dn, cl.dn
        )
    )
    user.remove()
    wg.remove()
    cl.remove()
    utils.wait_for_replication()
    wait_for_drs_replication(filter_format("cn=%s", (user.username,)), should_exist=False)
    user.verify()


@pytest.mark.parametrize("check_password_policies", [True, False])
def test_create_check_password_policies(schoolenv, check_password_policies):
    # 00_password_policies
    umc_connection = Client.get_test_connection(schoolenv.ucr.get("ldap/master"))
    (ou, oudn) = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
    ucr_var_name = "ucsschool/wizards/schoolwizards/users/check-password-policies"
    handler_set(["{}={}".format(ucr_var_name, check_password_policies)])
    cl = Klasse(school=ou, connection=umc_connection)
    cl.create()
    user = User(
        school=ou,
        role="student",
        school_classes={ou: [cl.name]},
        schools=[ou],
        password="funk",
        connection=umc_connection,
    )
    if check_password_policies:
        with pytest.raises(AssertionError):
            user.create()
    else:
        user.create()
        user.remove()
    cl.remove()


def test_modify_always_check_password_policies(schoolenv):
    # 00_password_policies
    umc_connection = Client.get_test_connection(schoolenv.ucr.get("ldap/master"))
    (ou, oudn) = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
    cl = Klasse(school=ou, connection=umc_connection)
    cl.create()
    user = User(
        school=ou,
        role="student",
        school_classes={ou: [cl.name]},
        schools=[ou],
        connection=umc_connection,
    )
    user.create()
    with pytest.raises(AssertionError):
        new_attributes = {"password": "funky"}
        user.edit(new_attributes)
    cl.remove()
