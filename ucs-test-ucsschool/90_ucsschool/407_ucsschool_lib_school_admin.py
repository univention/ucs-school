#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.user.SchoolAdmin CRUD operations
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./......py::test_create
#

from univention.testing import utils
from ucsschool.lib.models.user import SchoolAdmin
from univention.testing.ucsschool.conftest import UserType


def test_create(create_ou, lo, user_ldap_attributes, user_school_attributes):
    ou_name, ou_dn = create_ou()
    ldap_attrs = user_ldap_attributes([ou_name], UserType.SchoolAdmin)
    groups = [x.decode("UTF-8") for x in ldap_attrs.pop("groups")]
    school_attrs = user_school_attributes([ou_name], UserType.SchoolAdmin, ldap_attrs=ldap_attrs)
    obj = SchoolAdmin(**school_attrs)
    res = obj.create(lo)
    assert res
    utils.verify_ldap_object(obj.dn, expected_attr=ldap_attrs, strict=False)
    for dn in groups:
        utils.verify_ldap_object(dn, expected_attr={"uniqueMember": [obj.dn]}, strict=False)


def test_get_all(create_ou, lo, user_school_attributes):
    ou_name, ou_dn = create_ou(use_cache=False)
    attrs = (
        user_school_attributes([ou_name], UserType.SchoolAdmin),
        user_school_attributes([ou_name], UserType.SchoolAdmin),
        user_school_attributes([ou_name], UserType.SchoolAdmin),
    )
    for school_attrs in attrs:
        obj = SchoolAdmin(**school_attrs)
        res = obj.create(lo)
        assert res
        assert obj.exists(lo)

    objs = SchoolAdmin.get_all(lo, ou_name)
    assert len(objs) == len(attrs)
    names = [_attrs["name"] for _attrs in attrs]
    for obj in objs:
        assert isinstance(obj, SchoolAdmin)
        assert obj.name in names


def test_modify(create_ou, lo, user_ldap_attributes, user_school_attributes):
    ou_name, ou_dn = create_ou()
    ldap_attrs = user_ldap_attributes([ou_name], UserType.SchoolAdmin)
    groups = [x.decode("UTF-8") for x in ldap_attrs.pop("groups")]
    school_attrs = user_school_attributes([ou_name], UserType.SchoolAdmin, ldap_attrs=ldap_attrs)
    obj = SchoolAdmin(**school_attrs)
    res = obj.create(lo)
    assert res
    utils.verify_ldap_object(obj.dn, expected_attr=ldap_attrs, strict=False)
    for dn in groups:
        utils.verify_ldap_object(dn, expected_attr={"uniqueMember": [obj.dn]}, strict=False)
    ldap_attrs_new = user_ldap_attributes([ou_name], UserType.SchoolAdmin)
    groups = [x.decode("UTF-8") for x in ldap_attrs_new.pop("groups")]
    school_attrs_new = user_school_attributes([ou_name], UserType.SchoolAdmin, ldap_attrs=ldap_attrs_new)
    assert obj.name != school_attrs_new["name"]
    for k, v in school_attrs_new.items():
        setattr(obj, k, v)
    assert obj.name == school_attrs_new["name"]
    res = obj.modify(lo)
    assert res
    utils.verify_ldap_object(obj.dn, expected_attr=ldap_attrs_new, strict=False)
    for dn in groups:
        utils.verify_ldap_object(dn, expected_attr={"uniqueMember": [obj.dn]}, strict=False)


def test_delete(
    create_ou,
    lo,
    model_ldap_object_classes,
    user_ldap_attributes,
    user_school_attributes,
):
    ou_name, ou_dn = create_ou()
    ldap_attrs = user_ldap_attributes([ou_name], UserType.SchoolAdmin)
    groups = [x.decode("UTF-8") for x in ldap_attrs.pop("groups")]
    school_attrs = user_school_attributes([ou_name], UserType.SchoolAdmin, ldap_attrs=ldap_attrs)
    obj = SchoolAdmin(**school_attrs)
    res = obj.create(lo)
    assert res
    utils.verify_ldap_object(obj.dn, expected_attr=ldap_attrs, strict=False)
    for dn in groups:
        utils.verify_ldap_object(dn, expected_attr={"uniqueMember": [obj.dn]}, strict=False)
    obj_dn = obj.dn
    res = obj.remove(lo)
    assert res
    utils.verify_ldap_object(obj_dn, should_exist=False)
    for dn in groups:
        assert obj_dn not in lo.get(dn, attr=["uniqueMember"]).get("uniqueMember", [])
    ocs = model_ldap_object_classes(UserType.SchoolAdmin)
    filter_ocs = "".join("(objectClass={})".format(oc) for oc in ocs)
    filter_s = "(&(cn={}){})".format(obj.name, filter_ocs)
    assert lo.searchDn(filter_s) == []


def test_remove_from_groups_of_school(create_ou, lo, user_school_attributes, ucr_ldap_base):
    # Bug 54368
    # remove_from_groups_of_school() doesn't remove school admins from admins-OU group
    ou_name, _ = create_ou()
    attrs = user_school_attributes([ou_name], UserType.SchoolAdmin)
    admin = SchoolAdmin(**attrs)
    assert admin.create(lo)

    du_school_dn = f"cn=Domain Users {ou_name},cn=groups,ou={ou_name},{ucr_ldap_base}"
    ou_admins_dn = f"cn=admins-{ou_name},cn=ouadmins,cn=groups,{ucr_ldap_base}"

    for dn in (du_school_dn, ou_admins_dn):
        assert admin.dn in [
            x.decode("UTF-8") for x in lo.get(dn, attr=["uniqueMember"]).get("uniqueMember", [])
        ]

    admin.remove_from_groups_of_school(ou_name, lo)

    for dn in (du_school_dn, ou_admins_dn):
        assert admin.dn not in [
            x.decode("UTF-8") for x in lo.get(dn, attr=["uniqueMember"]).get("uniqueMember", [])
        ]
