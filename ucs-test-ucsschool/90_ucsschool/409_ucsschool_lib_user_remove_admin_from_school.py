#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.users.User remove_from_groups_of_school for admin users
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

from ldap.filter import filter_format

from ucsschool.lib.models.group import (
    BasicGroup,
    SchoolClass,
    SchoolGroup,
    WorkGroup,
)
from ucsschool.lib.models.user import User
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_school_admin,
    role_school_admin_group,
)


def test_remove_admin_from_groups_of_school(schoolenv):
    # Test scenario:
    # A user who is a teacher and an admin in two schools.
    # When the user is removed from the second school,
    # both the admin and teacher groups will be completely removed for the second school,
    # leaving the first school as-is

    # School setup
    school1_name, school1_dn = schoolenv.create_ou(
        ou_name="school1_keep_admin",
        name_edudc=schoolenv.ucr["hostname"],
    )
    school2_name, school2_dn = schoolenv.create_ou(
        ou_name="school2_remove_admin",
        name_edudc=schoolenv.ucr["hostname"],
    )
    school_names = [school1_name, school2_name]
    class1_name, class1_dn = schoolenv.create_school_class(ou_name=school1_name)
    class2_name, class2_dn = schoolenv.create_school_class(ou_name=school2_name)
    wg1_name, wg1_dn = schoolenv.create_workgroup(ou_name=school1_name)
    wg2_name, wg2_dn = schoolenv.create_workgroup(ou_name=school2_name)

    # User setup: both teacher and admin
    user_name, user_dn = schoolenv.create_teacher(
        ou_name=school1_name,
        schools=school_names,
        classes=f"{class1_name},{class2_name}",
    )
    user = User.from_dn(user_dn, None, schoolenv.lo)
    user.roles.append(role_school_admin)
    for school in school_names:
        role = create_ucsschool_role_string(role_school_admin, school)
        user.ucsschool_roles.append(role)
    user.modify(schoolenv.lo)
    user_obj = user.get_udm_object(schoolenv.lo)
    user_obj.oldattr["objectClass"].append("ucsschoolAdministrator".encode("UTF-8"))
    user_obj.modify(schoolenv.lo)

    # User group setup
    for wg_dn, school in ((wg1_dn, school1_name), (wg2_dn, school2_name)):
        wg = WorkGroup.from_dn(wg_dn, school, schoolenv.lo)
        wg.users.append(user_dn)
        wg.modify(schoolenv.lo)

    admin_group_dns = user.get_school_admin_groups(school_names)
    for dn in admin_group_dns:
        group = BasicGroup.from_dn(dn, None, schoolenv.lo)
        group.users.append(user_dn)
        group.modify(schoolenv.lo)

    ldap_filter = filter_format("uniqueMember=%s", (user_dn,))
    sc1_dn = SchoolClass.get_all(schoolenv.lo, school1_name, ldap_filter)[0].dn
    sc2_dn = SchoolClass.get_all(schoolenv.lo, school2_name, ldap_filter)[0].dn
    sg1_dn = SchoolGroup.get_all(schoolenv.lo, school1_name, ldap_filter)[0].dn
    sg2_dn = SchoolGroup.get_all(schoolenv.lo, school2_name, ldap_filter)[0].dn

    # Testing
    user.remove_from_groups_of_school(school2_name, schoolenv.lo)

    sc1 = SchoolClass.from_dn(sc1_dn, school1_name, schoolenv.lo)
    sc2 = SchoolClass.from_dn(sc2_dn, school2_name, schoolenv.lo)
    assert user_dn in sc1.users
    assert user_dn not in sc2.users

    sg1 = SchoolGroup.from_dn(sg1_dn, school1_name, schoolenv.lo)
    sg2 = SchoolGroup.from_dn(sg2_dn, school2_name, schoolenv.lo)
    assert user_dn in sg1.users
    assert user_dn not in sg2.users

    wg1 = WorkGroup.from_dn(wg1_dn, school1_name, schoolenv.lo)
    wg2 = WorkGroup.from_dn(wg2_dn, school2_name, schoolenv.lo)
    assert user_dn in wg1.users
    assert user_dn not in wg2.users

    for dn, school_name in zip(admin_group_dns, school_names):
        group = BasicGroup.from_dn(dn, None, schoolenv.lo)
        expected_role = create_ucsschool_role_string(
            role_school_admin_group,
            school_name,
        )
        # Bug 55986 -- when saving BasicGroup, make sure it doesn't remove
        # the group's roles
        assert group.ucsschool_roles == [expected_role]

        if school_name == school1_name:
            assert user_dn in group.users
        else:
            assert user_dn not in group.users
