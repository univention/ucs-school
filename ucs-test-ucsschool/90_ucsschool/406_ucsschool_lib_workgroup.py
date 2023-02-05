#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.group.WorkGroup CRUD operations
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

from univention.testing import utils
from ucsschool.lib.models.group import WorkGroup
from ucsschool.lib.models.share import WorkGroupShare


def test_create_with_share(
    create_ou, lo, ucr_hostname, workgroup_ldap_attributes, workgroup_school_attributes
):
    ou_name, ou_dn = create_ou()
    ldap_attrs = workgroup_ldap_attributes(ou_name)
    school_attrs = workgroup_school_attributes(ou_name, ldap_attrs=ldap_attrs)
    wg = WorkGroup(**school_attrs)
    res = wg.create(lo)
    assert res
    utils.verify_ldap_object(wg.dn, expected_attr=ldap_attrs, strict=False)
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolGroup))".format(wg.name)) == [wg.dn]
    wgs = WorkGroupShare.from_school_group(wg)
    assert wgs.name == wg.name
    assert wgs.school == wg.school
    assert wgs.exists(lo)
    utils.verify_ldap_object(
        wgs.dn,
        expected_attr={"cn": [wg.name], "ucsschoolRole": ["workgroup_share:school:{}".format(ou_name)]},
        strict=False,
    )
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolShare))".format(wg.name)) == [wgs.dn]


def test_create_without_share(
    create_ou, lo, workgroup_ldap_attributes, workgroup_school_attributes, ucr_hostname
):
    ou_name, ou_dn = create_ou()
    ldap_attrs = workgroup_ldap_attributes(ou_name)
    school_attrs = workgroup_school_attributes(ou_name, ldap_attrs=ldap_attrs)
    wg = WorkGroup(create_share=False, **school_attrs)
    res = wg.create(lo)
    assert res
    utils.verify_ldap_object(wg.dn, expected_attr=ldap_attrs, strict=False)
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolGroup))".format(wg.name)) == [wg.dn]
    wgs = WorkGroupShare.from_school_group(wg)
    assert not wgs.exists(lo)
    utils.verify_ldap_object(wgs.dn, should_exist=False)
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolShare))".format(wg.name)) == []


def test_get_all(create_ou, lo, ucr_hostname, workgroup_ldap_attributes, workgroup_school_attributes):
    ou_name, ou_dn = create_ou(use_cache=False)
    wg_attrs = (
        workgroup_school_attributes(ou_name),
        workgroup_school_attributes(ou_name),
        workgroup_school_attributes(ou_name),
    )
    for school_attrs in wg_attrs:
        wg = WorkGroup(create_share=False, **school_attrs)
        res = wg.create(lo)
        assert res
        assert wg.exists(lo)

    objs = WorkGroup.get_all(lo, ou_name)
    assert len(objs) == len(wg_attrs)
    wg_names = [_wg["name"] for _wg in wg_attrs]
    for obj in objs:
        assert isinstance(obj, WorkGroup)
        assert obj.name in wg_names


def test_modify_with_share(
    create_ou, lo, workgroup_ldap_attributes, workgroup_school_attributes, ucr_hostname
):
    ou_name, ou_dn = create_ou()
    ldap_attrs = workgroup_ldap_attributes(ou_name)
    school_attrs = workgroup_school_attributes(ou_name, ldap_attrs=ldap_attrs)
    wg = WorkGroup(**school_attrs)
    res = wg.create(lo)
    assert res
    utils.verify_ldap_object(wg.dn, expected_attr=ldap_attrs, strict=False)
    wgs = WorkGroupShare.from_school_group(wg)
    assert wgs.exists(lo)
    utils.verify_ldap_object(
        wgs.dn,
        expected_attr={"cn": [wg.name], "ucsschoolRole": ["workgroup_share:school:{}".format(ou_name)]},
        strict=False,
    )
    ldap_attrs_new = workgroup_ldap_attributes(ou_name)
    school_attrs_new = workgroup_school_attributes(ou_name, ldap_attrs=ldap_attrs_new)
    assert wg.name != school_attrs_new["name"]
    for k, v in school_attrs_new.items():
        setattr(wg, k, v)
    assert wg.name == school_attrs_new["name"]
    res = wg.modify(lo)
    assert res
    utils.verify_ldap_object(wg.dn, expected_attr=ldap_attrs_new, strict=False)
    wgs = WorkGroupShare.from_school_group(wg)
    assert wgs.name == school_attrs_new["name"]
    assert wgs.exists(lo)
    utils.verify_ldap_object(
        wgs.dn,
        expected_attr={
            "cn": [wgs.name],
            "ucsschoolRole": ["workgroup_share:school:{}".format(ou_name)],
        },
        strict=False,
    )


def test_modify_without_share(
    create_ou, lo, workgroup_ldap_attributes, workgroup_school_attributes, ucr_hostname
):
    ou_name, ou_dn = create_ou(name_edudc=ucr_hostname)
    ldap_attrs = workgroup_ldap_attributes(ou_name)
    school_attrs = workgroup_school_attributes(ou_name, ldap_attrs=ldap_attrs)
    wg = WorkGroup(create_share=False, **school_attrs)
    res = wg.create(lo)
    assert res
    utils.verify_ldap_object(wg.dn, expected_attr=ldap_attrs, strict=False)
    wgs = WorkGroupShare.from_school_group(wg)
    assert not wgs.exists(lo)
    utils.verify_ldap_object(wgs.dn, should_exist=False)
    ldap_attrs_new = workgroup_ldap_attributes(ou_name)
    school_attrs_new = workgroup_school_attributes(ou_name, ldap_attrs=ldap_attrs_new)
    assert wg.name != school_attrs_new["name"]
    for k, v in school_attrs_new.items():
        setattr(wg, k, v)
    assert wg.name == school_attrs_new["name"]
    res = wg.modify(lo)
    assert res
    utils.verify_ldap_object(wg.dn, expected_attr=ldap_attrs_new, strict=False)
    wgs = WorkGroupShare.from_school_group(wg)
    assert not wgs.exists(lo)
    utils.verify_ldap_object(wgs.dn, should_exist=False)
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolShare))".format(wg.name)) == []


def test_delete_with_share(
    create_ou, lo, workgroup_ldap_attributes, workgroup_school_attributes, ucr_hostname
):
    ou_name, ou_dn = create_ou(name_edudc=ucr_hostname)
    ldap_attrs = workgroup_ldap_attributes(ou_name)
    school_attrs = workgroup_school_attributes(ou_name, ldap_attrs=ldap_attrs)
    wg = WorkGroup(**school_attrs)
    res = wg.create(lo)
    assert res
    utils.verify_ldap_object(wg.dn, expected_attr=ldap_attrs, strict=False)
    wgs = WorkGroupShare.from_school_group(wg)
    assert wgs.exists(lo)
    wg_dn = wg.dn
    wgs_dn = wgs.dn
    res = wg.remove(lo)
    assert res
    utils.verify_ldap_object(wg_dn, should_exist=False)
    utils.verify_ldap_object(wgs_dn, should_exist=False)
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolGroup))".format(wg.name)) == []
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolShare))".format(wg.name)) == []


def test_delete_without_share(
    create_ou, lo, workgroup_ldap_attributes, workgroup_school_attributes, ucr_hostname
):
    ou_name, ou_dn = create_ou(name_edudc=ucr_hostname)
    ldap_attrs = workgroup_ldap_attributes(ou_name)
    school_attrs = workgroup_school_attributes(ou_name, ldap_attrs=ldap_attrs)
    wg = WorkGroup(create_share=False, **school_attrs)
    res = wg.create(lo)
    assert res
    utils.verify_ldap_object(wg.dn, expected_attr=ldap_attrs, strict=False)
    wgs = WorkGroupShare.from_school_group(wg)
    wg_dn = wg.dn
    wgs_dn = wgs.dn
    utils.verify_ldap_object(wgs_dn, should_exist=False)
    res = wg.remove(lo)
    assert res
    utils.verify_ldap_object(wg_dn, should_exist=False)
    utils.verify_ldap_object(wgs_dn, should_exist=False)
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolGroup))".format(wg.name)) == []
    assert lo.searchDn("(&(cn={})(objectClass=ucsschoolShare))".format(wg.name)) == []
