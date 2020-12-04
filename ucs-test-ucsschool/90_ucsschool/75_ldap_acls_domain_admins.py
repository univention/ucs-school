#!/usr/share/ucs-test/runner python
# coding=utf-8
## desc: users in domain admin group & OC ucsschoolAdministrator can create school & non-school users
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-ldap-acls-master]


import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
from univention.testing.ucsschool.acl import Acl


class MyAcl(Acl):
    def __init__(self, school, auth_dn, access_allowance):
        super(MyAcl, self).__init__(school, auth_dn, access_allowance)

    def assert_user(self, user_dn, access):
        attrs = ["sambaNTPassword", "userPassword", "krb5Key", "sambaPasswordHistory", "pwhistory"]
        self.assert_acl(user_dn, access, attrs)


def main():
    with utu.UCSTestSchool() as schoolenv:
        with ucr_test.UCSTestConfigRegistry() as ucr:
            school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
            tea, tea_dn = schoolenv.create_teacher(school)
            non_school_admin_dn, nonschool_admin = schoolenv.udm.create_user(
                password=uts.random_string(),
                groups=["cn=Domain Admins,cn=groups,%s" % (schoolenv.ucr.get("ldap/base"))],
            )
            schoolenv.lo.modify(non_school_admin_dn, [("objectClass", "", "ucsschoolAdministrator")])
            acl2 = MyAcl(school, non_school_admin_dn, "ALLOWED")
            non_school_user_dn, nonschool_username = schoolenv.udm.create_user(
                password=uts.random_string()
            )
            acl2.assert_user(non_school_user_dn, "write")
            acl2.assert_user(tea_dn, "write")


if __name__ == "__main__":
    main()
