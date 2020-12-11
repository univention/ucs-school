#!/usr/share/ucs-test/runner python
# coding=utf-8
## desc: Check if the permissions to user password attributes are correct
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-ldap-acls-master]

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm as udm_test
from univention.testing.ucsschool.acl import Acl


def main():
    attrs = ["sambaNTPassword", "userPassword", "krb5Key", "sambaPasswordHistory", "pwhistory"]
    with utu.UCSTestSchool() as schoolenv:
        with ucr_test.UCSTestConfigRegistry() as ucr:
            with udm_test.UCSTestUDM() as udm:
                school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
                school_admin, school_admin_dn = schoolenv.create_school_admin(school)
                school_admin2, school_admin_dn2 = schoolenv.create_school_admin(school)
                school_teacher, school_teacher_dn = schoolenv.create_teacher(school)
                school_teacher2, school_teacher_dn2 = schoolenv.create_teacher(school)
                staff, staff_dn = schoolenv.create_user(school, is_staff=True)
                staff2, staff_dn2 = schoolenv.create_user(school, is_staff=True)
                stu, stu_dn = schoolenv.create_user(school)
                stu2, stu_dn2 = schoolenv.create_user(school)
                global_user, global_user_dn = udm.create_user()
                global_user2, global_user_dn2 = udm.create_user()

                # check access for global users
                acl = Acl(None, global_user_dn, "DENIED")
                for target_dn in (school_admin_dn, school_teacher_dn, staff_dn, stu_dn, global_user_dn2):
                    acl.assert_acl(target_dn, "read", attrs)

                # check access for students
                acl = Acl(school, stu_dn, "DENIED")
                for target_dn in (school_admin_dn, school_teacher_dn, staff_dn, stu_dn2, global_user_dn):
                    acl.assert_acl(target_dn, "read", attrs)

                # check access for teachers
                acl = Acl(school, school_teacher_dn, "DENIED")
                for target_dn in (school_teacher_dn2, school_admin_dn, staff_dn, global_user_dn):
                    acl.assert_acl(target_dn, "read", attrs)
                acl.assert_acl(stu_dn, "read", attrs, "ALLOWED")

                # check access for staff
                acl = Acl(school, staff_dn, "DENIED")
                for target_dn in (school_admin_dn, school_teacher_dn, staff_dn2, stu_dn, global_user_dn):
                    acl.assert_acl(target_dn, "read", attrs)

                # check access for school admin
                acl = Acl(school, school_admin_dn, "ALLOWED")
                for target_dn in (stu_dn, school_teacher_dn, staff_dn):
                    acl.assert_acl(target_dn, "read", attrs)
                for target_dn in (school_admin_dn2, global_user_dn):
                    acl.assert_acl(target_dn, "read", attrs, "DENIED")


if __name__ == "__main__":
    main()
