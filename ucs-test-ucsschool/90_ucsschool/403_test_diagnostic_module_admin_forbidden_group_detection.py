#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: test forbidden groups diagnosis for a school admin of multiple schools
## roles: [domaincontroller_master]
## tags: [ucsschool,diagnostic_test,apptest,ucsschool_base1]
## exposure: dangerous
## bugs: [54415]
## packages:
##   - python3-ucsschool-lib

import importlib

from pytest import raises

from ucsschool.lib.models.school import School
from univention.udm import UDM

plugin908 = importlib.import_module(
    "univention.management.console.modules.diagnostic.plugins.908_ucsschool_school_admin_accounts"
)


def test_admin_in_correct_groups(schoolenv):
    # we create 2 schools, and copy the groups, schools and school
    # roles of the second school's admin into that of the first
    # school, thus creating a school admin (no. 1) which is correctly
    # setup to be admin in the second school as well. in this context
    # running the diagnostics should not raise the forbidden groups
    # warning.
    schools = schoolenv.create_multiple_ous(2)
    school1_name, _ = schools[0]
    _, school1_admin_dn = schoolenv.create_school_admin(school1_name)
    udm_obj1 = UDM.admin().version(2).obj_by_dn(school1_admin_dn)
    school2_name, _ = schools[1]
    _, school2_admin_dn = schoolenv.create_school_admin(school2_name)
    udm_obj2 = UDM.admin().version(2).obj_by_dn(school2_admin_dn)
    udm_obj1.props.groups.extend(udm_obj2.props.groups)
    udm_obj1.props.school.extend(udm_obj2.props.school)
    udm_obj1.props.ucsschoolRole.extend(udm_obj2.props.ucsschoolRole)
    udm_obj1.save()
    try:
        plugin908.run(None)
    except plugin908.Warning as exc:
        assert not all(
            [s in str(exc.message) for s in [school2_admin_dn, plugin908.FORBIDDEN_GROUPS_WARN_STR]]
        ), (
            "The diagnostics module 908_ucsschool_school_admin_accounts.py expected "
            "not to raise any warning for {}!".format(school2_admin_dn)
        )


def test_admin_in_wrong_groups(schoolenv):
    schools = schoolenv.create_multiple_ous(2)
    school1_name, _ = schools[0]
    school2_name, _ = schools[1]
    _, school1_admin_dn = schoolenv.create_school_admin(school1_name)
    school2_admins_group_dn = School.get_search_base(school2_name).admins_group
    udm_obj = UDM.admin().version(2).obj_by_dn(school2_admins_group_dn)
    udm_obj.props.users.append(school1_admin_dn)
    udm_obj.save()
    with raises(plugin908.Warning) as exc:
        plugin908.run(None)
        assert plugin908.FORBIDDEN_GROUPS_WARN_STR in str(exc.message)
        assert school2_admins_group_dn in str(exc.message)
