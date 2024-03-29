#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test UCRV ucsschool/ldap/replicate_staff_to_edu and LDAP ACLs
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## timeout: 14400

"""
Up to UCS@school 4.3v6, school servers (Replica Directory Nodes) could only read student,
teacher and admin objects from the OU structures with their machine account.
With the introduction of the UCR variable ucsschool/ldap/replicate_staff_to_edu,
it is also possible to replicate staff objects to the educational Replica Directory Nodes.
This is checked by this test. Depending on the status of the UCR variable, read
access to the staff objects is possible or not. The config of the slapd is
adjusted automatically and the slapd is restarted.

In addition, cross-school user accounts are checked. While student1 is directly
below the OU of slave1, student2 is below another OU, where student2 is a member
of both schools (1+2). It is therefore actively checked whether these user
objects can also be read by the Replica Directory Node. This also applies to the other user roles.
"""

import subprocess
import time

from ldap.filter import filter_format

import univention.admin.uldap as udm_uldap
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
from univention.config_registry import handler_set
from univention.testing import utils


class MyObj(object):
    def __init__(self, name, dn):
        self.name = name
        self.dn = dn


class UnexpectedLDAPAccess(Exception):
    pass


ACCESS_READ = "READ"
ACCESS_NONE = "NO ACCESS"


class TestCases(object):
    def __init__(self, ucr, schoolenv):
        self.ucr = ucr
        self.schoolenv = schoolenv

        # create 2 schools
        self.slave1 = MyObj("dc81acltest1", None)
        self.slave2 = MyObj("dc81acltest2", None)
        self.school1 = MyObj(
            *self.schoolenv.create_ou(name_edudc=self.slave1.name, wait_for_replication=False)
        )
        self.school2 = MyObj(
            *self.schoolenv.create_ou(name_edudc=self.slave2.name, wait_for_replication=False)
        )

        print("----------------------- created OUs: -----------------------")
        print("School 1 = {!r}".format(self.school1.name))
        print("School 2 = {!r}".format(self.school2.name))

        print("----------------------- creating Users... -----------------------")
        # "${type}2" is located at second school but is member of both schools
        self.student1 = MyObj(
            *self.schoolenv.create_student(self.school1.name, wait_for_replication=False)
        )
        self.student2 = MyObj(
            *self.schoolenv.create_student(
                self.school2.name,
                schools=[self.school1.name, self.school2.name],
                wait_for_replication=False,
            )
        )
        self.teacher1 = MyObj(
            *self.schoolenv.create_teacher(self.school1.name, wait_for_replication=False)
        )
        self.teacher2 = MyObj(
            *self.schoolenv.create_teacher(
                self.school2.name,
                schools=[self.school1.name, self.school2.name],
                wait_for_replication=False,
            )
        )
        self.staff1 = MyObj(*self.schoolenv.create_staff(self.school1.name, wait_for_replication=False))
        self.staff2 = MyObj(
            *self.schoolenv.create_staff(
                self.school2.name,
                schools=[self.school1.name, self.school2.name],
                wait_for_replication=False,
            )
        )
        self.teacher_and_staff1 = MyObj(
            *self.schoolenv.create_teacher_and_staff(self.school1.name, wait_for_replication=False)
        )
        self.teacher_and_staff2 = MyObj(
            *self.schoolenv.create_teacher_and_staff(
                self.school2.name,
                schools=[self.school1.name, self.school2.name],
                wait_for_replication=False,
            )
        )
        self.admin1 = MyObj(
            *self.schoolenv.create_school_admin(
                self.school1.name, is_teacher=True, wait_for_replication=False
            )
        )
        self.admin2 = MyObj(
            *self.schoolenv.create_school_admin(
                self.school2.name,
                schools=[self.school1.name, self.school2.name],
                is_teacher=True,
                wait_for_replication=False,
            )
        )
        # TODO: create staff-only admins and check their replication
        # currently we are lacking a concept for this
        print("----------------------- setting host account password... -----------------------")

        # locate DN of Replica Directory Node for OU school1
        lo = udm_uldap.getAdminConnection()[0]
        filter_s = filter_format(
            "(&(cn=%s)(univentionObjectType=computers/domaincontroller_slave))", (self.slave1.name,)
        )
        self.slave1.dn = lo.searchDn(filter=filter_s)[0]
        subprocess.check_call(
            [
                "/usr/sbin/udm-test",
                "computers/domaincontroller_slave",
                "modify",
                "--dn",
                self.slave1.dn,
                "--set",
                "password=univention",
            ]
        )
        self.lo = None
        print("----------------------------------------------")

    def test_access(self, target, expected_result):
        print("\nTEST: {}  (expected: {})".format(target.dn, expected_result))
        old_values = self.lo.get(target.dn)
        for attr_name in (
            "uid",
            "ucsschoolSchool",
            "userPassword",
        ):
            print("target.{}: {}".format(attr_name, old_values.get(attr_name)))
            if expected_result == ACCESS_READ and old_values.get(attr_name) is None:
                print("ERROR: WAITING")
                time.sleep(10)
                raise UnexpectedLDAPAccess(
                    "Cannot read attribute {} from {}".format(attr_name, target.dn)
                )
            elif expected_result == ACCESS_NONE and old_values.get(attr_name) is not None:
                raise UnexpectedLDAPAccess(
                    "Unexpectedly a value has been returned while reading attribute {} from {}".format(
                        attr_name, target.dn
                    )
                )
        print("OK: result as expected")

    def run(self):
        # test both scenarios of ucsschool/ldap/replicate_staff_to_edu=yes/no
        for ucr_value in ("no", "yes"):
            # set UCR variable and restart slapd
            print("Setting UCR variable ucsschool/ldap/replicate_staff_to_edu={}".format(ucr_value))
            handler_set(["ucsschool/ldap/replicate_staff_to_edu={}".format(ucr_value)])
            subprocess.call(["/usr/sbin/ucr", "commit", "/etc/ldap/slapd.conf"])
            subprocess.call(["/bin/systemctl", "restart", "slapd.service"])
            time.sleep(3)
            print("----------------------------------------------")

            # get fresh LDAP connection
            self.lo = udm_uldap.access(
                host=self.ucr.get("ldap/master"),
                port=7389,
                base=self.ucr.get("ldap/base"),
                binddn=self.slave1.dn,
                bindpw="univention",
                start_tls=2,
            )

            # check read access for all user types (in same and another OU)
            print("----- students... ------")
            self.test_access(self.student1, ACCESS_READ)
            self.test_access(self.student2, ACCESS_READ)
            print("----- teachers... ------")
            self.test_access(self.teacher1, ACCESS_READ)
            self.test_access(self.teacher2, ACCESS_READ)
            print("----- teacher_and_staffs... ------")
            self.test_access(self.teacher_and_staff1, ACCESS_READ)
            self.test_access(self.teacher_and_staff2, ACCESS_READ)
            print("----- staffs... ------")
            self.test_access(self.staff1, ACCESS_READ if ucr_value == "yes" else ACCESS_NONE)
            self.test_access(self.staff2, ACCESS_READ if ucr_value == "yes" else ACCESS_NONE)
            print("----- admins... ------")
            self.test_access(self.admin1, ACCESS_READ)
            self.test_access(self.admin2, ACCESS_READ)
            print("----- success ------")


def test_ldap_acl_staff2edu():
    # when exiting the 3 with statements, the following steps are achieved:
    # - UCR variables are cleaned up
    # - slapd.conf is committed/recreated
    # - slapd is restarted (with original config)
    with utils.AutoCallCommand(exit_cmd=["/bin/systemctl", "restart", "slapd.service"]):
        with utils.AutoCallCommand(exit_cmd=["/usr/sbin/ucr", "commit", "/etc/ldap/slapd.conf"]):
            with ucr_test.UCSTestConfigRegistry() as ucr:
                with utu.UCSTestSchool() as schoolenv:
                    testcases = TestCases(ucr, schoolenv)
                    testcases.run()
