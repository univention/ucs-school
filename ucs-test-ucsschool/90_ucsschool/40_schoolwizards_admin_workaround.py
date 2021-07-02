#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
# -*- coding: utf-8 -*-
## desc: Check the hardening of the UMC school wizard admin workaround
## roles: [domaincontroller_master]
## exposure: dangerous
## tags: [apptest, ucsschool, base1]
## bugs: [52757]
from typing import List

import pytest

from ucsschool.lib.models.user import User
from univention.config_registry import handler_get, handler_set, handler_unset
from univention.lib.umc import BadRequest, Client
from univention.testing.ucsschool.conftest import UserType
from univention.udm import UDM


@pytest.fixture(scope="session")
def school_admin_school_wizard_policy(ucr_ldap_base):
    operation_sets_to_allow = [
        operation_set.format(ucr_ldap_base)
        for operation_set in ["cn=schoolwizards-users,cn=operations,cn=UMC,cn=univention,{}"]
    ]
    operation_sets_to_clean = list()
    uas_umc_admin_policy = (
        UDM.admin()
        .version(1)
        .obj_by_dn("cn=ucsschool-umc-admins-default,cn=UMC,cn=policies,{}".format(ucr_ldap_base))
    )
    for o_set in operation_sets_to_allow:
        if o_set not in uas_umc_admin_policy.props.allow:
            uas_umc_admin_policy.props.allow.append(o_set)
            operation_sets_to_clean.append(o_set)
    uas_umc_admin_policy = uas_umc_admin_policy.save()
    yield
    for o_set in operation_sets_to_clean:
        uas_umc_admin_policy.props.allow.remove(o_set)
    uas_umc_admin_policy.save()


@pytest.fixture()
def umc_wizards_admin_workaround():
    original_value = list(handler_get(["ucsschool/wizards/schoolwizards/workaround/admin-connection"]))
    handler_set(["ucsschool/wizards/schoolwizards/workaround/admin-connection=yes"])
    yield
    if len(original_value) == 0:
        handler_unset(["ucsschool/wizards/schoolwizards/workaround/admin-connection"])
    else:
        handler_set(
            ["ucsschool/wizards/schoolwizards/workaround/admin-connection={}".format(original_value[0])]
        )


@pytest.fixture()
def create_ou_user(user_school_attributes, lo, model_school_object_class):
    def _create_ou_user(ous, user_type, password="univention"):  # type: (List[str]) -> User
        ou_user = model_school_object_class(user_type)(**user_school_attributes(ous, user_type))
        ou_user.password = password
        assert ou_user.create(lo)
        return ou_user

    return _create_ou_user


@pytest.fixture()
def create_umc_client(ucr):
    def _create_umc_client(username, password="univention", host_name=None):
        return Client(username=username, password=password, hostname=host_name, language="en_US")

    return _create_umc_client


def test_create_user_correct(
    school_admin_school_wizard_policy,
    umc_wizards_admin_workaround,
    create_ou,
    create_ou_user,
    user_school_attributes,
    create_umc_client,
):
    ou1_name, ou1_dn = create_ou()
    ou1_admin = create_ou_user([ou1_name], UserType.SchoolAdmin)
    client = create_umc_client(ou1_admin.name)
    ou1_user_data = user_school_attributes([ou1_name], UserType.Teacher)
    params = [
        {
            "object": ou1_user_data,
            "options": None,
        }
    ]
    response = client.umc_command("schoolwizards/users/add", params, "schoolwizards/users")
    assert response.result == [True]


def test_create_user_other_school(
    school_admin_school_wizard_policy,
    umc_wizards_admin_workaround,
    create_ou,
    create_ou_user,
    user_school_attributes,
    create_umc_client,
):
    ou1_name, ou1_dn = create_ou(ou_name="A")
    ou2_name, ou2_dn = create_ou(ou_name="B")
    ou1_admin = create_ou_user([ou1_name], UserType.SchoolAdmin)
    client = create_umc_client(ou1_admin.name)
    ou2_user_data = user_school_attributes([ou2_name], UserType.Teacher)
    params = [
        {
            "object": ou2_user_data,
            "options": None,
        }
    ]
    with pytest.raises(BadRequest) as exc_info:
        client.umc_command("schoolwizards/users/add", params, "schoolwizards/users")
    assert (
        exc_info.value.message
        == "You do not have the rights to create an object for the schools set([u'B'])"
    )


def test_delete_user_correct(
    school_admin_school_wizard_policy,
    umc_wizards_admin_workaround,
    create_ou,
    create_ou_user,
    user_school_attributes,
    create_umc_client,
):
    ou1_name, ou1_dn = create_ou()
    ou1_admin = create_ou_user([ou1_name], UserType.SchoolAdmin)
    ou1_teacher = create_ou_user([ou1_name], UserType.Teacher)
    client = create_umc_client(ou1_admin.name)
    params = [
        {
            "object": {"remove_from_school": ou1_name, "$dn$": ou1_teacher.dn},
            "options": None,
        }
    ]
    response = client.umc_command("schoolwizards/users/remove", params, "schoolwizards/users")
    assert response.result == [True]


def test_delete_user_other_school(
    school_admin_school_wizard_policy,
    umc_wizards_admin_workaround,
    create_ou,
    create_ou_user,
    user_school_attributes,
    create_umc_client,
):
    ou1_name, ou1_dn = create_ou(ou_name="A")
    ou2_name, ou2_dn = create_ou(ou_name="B")
    ou1_admin = create_ou_user([ou1_name], UserType.SchoolAdmin)
    ou2_teacher = create_ou_user([ou2_name], UserType.Teacher)
    client = create_umc_client(ou1_admin.name)
    params = [
        {
            "object": {"remove_from_school": ou1_name, "$dn$": ou2_teacher.dn},
            "options": None,
        }
    ]
    with pytest.raises(BadRequest) as exc_info:
        client.umc_command("schoolwizards/users/remove", params, "schoolwizards/users")
    assert (
        exc_info.value.message
        == "You do not have the right to delete the user with the dn %s from the school %s."
        % (ou2_teacher.dn, ou1_name)
    )


def test_edit_user_correct(
    school_admin_school_wizard_policy,
    umc_wizards_admin_workaround,
    create_ou,
    create_ou_user,
    user_school_attributes,
    create_umc_client,
):
    ou1_name, ou1_dn = create_ou()
    ou1_admin = create_ou_user([ou1_name], UserType.SchoolAdmin)
    ou1_teacher = create_ou_user([ou1_name], UserType.Teacher)
    client = create_umc_client(ou1_admin.name)
    params = [
        {
            "object": {"firstname": "other_name", "$dn$": ou1_teacher.dn, "school": ou1_name},
            "options": None,
        }
    ]
    response = client.umc_command("schoolwizards/users/put", params, "schoolwizards/users")
    assert response.result == [True]


def test_edit_user_other_school(
    school_admin_school_wizard_policy,
    umc_wizards_admin_workaround,
    create_ou,
    create_ou_user,
    user_school_attributes,
    create_umc_client,
):
    ou1_name, ou1_dn = create_ou(ou_name="A")
    ou2_name, ou2_dn = create_ou(ou_name="B")
    ou1_admin = create_ou_user([ou1_name], UserType.SchoolAdmin)
    ou2_teacher = create_ou_user([ou2_name], UserType.Teacher)
    client = create_umc_client(ou1_admin.name)
    params = [
        {
            "object": {"firstname": "other_name", "$dn$": ou2_teacher.dn, "school": ou2_name},
            "options": None,
        }
    ]
    with pytest.raises(BadRequest) as exc_info:
        client.umc_command("schoolwizards/users/put", params, "schoolwizards/users")
    assert (
        exc_info.value.message
        == "You do not have the right to modify the object with the DN %s from the schools set(['B'])."
        % ou2_teacher.dn
    )
