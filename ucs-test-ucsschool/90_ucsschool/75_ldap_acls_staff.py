#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: Check if staff users have at least the required LDAP permissions for UCS@school
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-ldap-acls-master]

from ldap.filter import filter_format

from univention.testing.ucsschool.acl import Acl
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.schoolroom import ComputerRoom


def test_ldap_acls_staff(schoolenv, ucr):
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    school_admin, school_admin_dn = schoolenv.create_school_admin(school)
    staff, staff_dn = schoolenv.create_user(school, is_staff=True)
    stu, stu_dn = schoolenv.create_user(school)
    class_name, class_dn = schoolenv.create_school_class(school)

    open_ldap_co = schoolenv.open_ldap_connection()
    # importing 2 random computers
    computers = Computers(open_ldap_co, school, 1, 0, 0)
    created_computers = computers.create()
    computers_dns = computers.get_dns(created_computers)
    room = ComputerRoom(school, host_members=computers_dns)
    room.add()

    acl = Acl(school, staff_dn, "ALLOWED")

    acl.assert_base_dn("read")

    # Disabled with Bug #50669
    # acl.assert_student(stu_dn, 'write')

    acl.assert_room(room.dn(), "write")

    acl.assert_temps("write")
    acl.assert_gid_temps("write")

    acl.assert_ou("read")

    acl.assert_global_containers("read")

    # Bug #41720
    share_dn = open_ldap_co.searchDn(
        filter=filter_format("(&(objectClass=univentionShare)(cn=%s))", (class_name,))
    )[0]
    acl.assert_share_object_access(share_dn, "read", "ALLOWED")
    acl.assert_share_object_access(share_dn, "write", "DENIED")
    share_dn = "cn=Marktplatz,cn=shares,%s" % (oudn,)
    acl.assert_share_object_access(share_dn, "read", "ALLOWED")
    acl.assert_share_object_access(share_dn, "write", "DENIED")
