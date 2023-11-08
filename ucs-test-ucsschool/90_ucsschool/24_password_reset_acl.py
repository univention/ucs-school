#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test password reset ACLs
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-users]
## timeout: 14400

from __future__ import print_function

import sys
import time

import passlib.hash
import pytest

import univention.admin.uldap as udm_uldap
import univention.testing.strings as uts
from univention.testing import utils


class MyObj(object):
    def __init__(self, name, dn):
        self.name = name
        self.dn = dn


class MySchool(MyObj):
    pass


class MyStudent(MyObj):
    pass


class MyTeacher(MyObj):
    pass


class MyAdmin(MyObj):
    pass


RESULT_FAIL = "FAIL"
RESULT_OK = "OK"


class _TestCases(object):
    def __init__(self, ucr, schoolenv):
        self.ucr = ucr
        self.schoolenv = schoolenv

        print("---[START /etc/ldap/slapd.conf]---", file=sys.stderr)
        print(open("/etc/ldap/slapd.conf").read(), file=sys.stderr)
        print("---[END /etc/ldap/slapd.conf]---", file=sys.stderr)
        sys.stderr.flush()

        host = self.ucr.get("hostname")
        # create 2 schools
        self.school1 = MySchool(*self.schoolenv.create_ou(name_edudc=host, wait_for_replication=False))
        self.school2 = MySchool(
            *self.schoolenv.create_ou(name_edudc="dcschool2", wait_for_replication=False)
        )

        print("School 1 = {!r}".format(self.school1.name))
        print("School 2 = {!r}\n".format(self.school2.name))

        # "${type}2" is located at second school but member of both schools, so teachers/admins of
        # school1 should be able to reset passwords of "${type}1" and "${type}2"
        self.student0 = MyStudent(
            *self.schoolenv.create_student(self.school1.name, wait_for_replication=False)
        )
        self.student1 = MyStudent(
            *self.schoolenv.create_student(self.school1.name, wait_for_replication=False)
        )
        self.student2 = MyStudent(
            *self.schoolenv.create_student(
                self.school2.name,
                schools=[self.school1.name, self.school2.name],
                wait_for_replication=False,
            )
        )
        self.teacher0 = MyTeacher(
            *self.schoolenv.create_teacher(self.school1.name, wait_for_replication=False)
        )
        self.teacher1 = MyTeacher(
            *self.schoolenv.create_teacher(self.school1.name, wait_for_replication=False)
        )
        self.teacher2 = MyTeacher(
            *self.schoolenv.create_teacher(
                self.school2.name,
                schools=[self.school1.name, self.school2.name],
                wait_for_replication=False,
            )
        )
        is_teacher = True if self.ucr.get("server/role") == "domaincontroller_slave" else None
        self.admin0 = MyAdmin(
            *self.schoolenv.create_school_admin(
                self.school1.name, is_teacher=is_teacher, wait_for_replication=False
            )
        )
        self.admin1 = MyAdmin(
            *self.schoolenv.create_school_admin(
                self.school1.name, is_teacher=is_teacher, wait_for_replication=False
            )
        )

        # verify users
        assert self.student1.dn.endswith(self.school1.dn)
        assert self.student2.dn.endswith(self.school2.dn)
        assert self.teacher1.dn.endswith(self.school1.dn)
        assert self.teacher2.dn.endswith(self.school2.dn)
        utils.verify_ldap_object(
            self.student2.dn,
            expected_attr={"ucsschoolSchool": [self.school1.name, self.school2.name]},
            strict=True,
            should_exist=True,
        )
        utils.verify_ldap_object(
            self.teacher2.dn,
            expected_attr={"ucsschoolSchool": [self.school1.name, self.school2.name]},
            strict=True,
            should_exist=True,
        )

    def test_pw_reset(self, actor, target, expected_result):
        print("\nTEST: {} ==> {}  (expected: {})".format(actor.dn, target.dn, expected_result))
        lo = udm_uldap.access(
            host=self.ucr.get("ldap/master"),
            port=7389,
            base=self.ucr.get("ldap/base"),
            binddn=actor.dn,
            bindpw="univention",
            start_tls=2,
        )
        old_values = lo.get(target.dn)
        print("target.ucsschoolSchool: {}".format(old_values.get("ucsschoolSchool")))
        for attr_name, val in (
            ("sambaNTPassword", passlib.hash.nthash.hash(uts.random_string(20)).upper().encode()),
            ("userPassword", str(time.time()).encode()),
            ("pwhistory", str(time.time()).encode()),
        ):  # "krb5key" has no eq matching rule, so lo.modify fails
            if expected_result == RESULT_OK:
                lo.modify(target.dn, [[attr_name, old_values.get(attr_name), [val]]])
            else:
                with pytest.raises(Exception):  # noqa: B017
                    lo.modify(target.dn, [[attr_name, old_values.get(attr_name), [val]]])
        print("OK: result as expected")


@pytest.mark.parametrize(
    "actor,target,expected_result",
    [
        ("student0", "student1", RESULT_FAIL),
        ("student0", "student2", RESULT_FAIL),
        ("teacher0", "student1", RESULT_OK),
        ("teacher0", "student2", RESULT_OK),
        ("teacher0", "teacher1", RESULT_FAIL),
        ("teacher0", "teacher2", RESULT_FAIL),
        ("admin0", "student1", RESULT_OK),
        ("admin0", "student2", RESULT_OK),
        ("admin0", "teacher1", RESULT_OK),
        ("admin0", "teacher2", RESULT_OK),
        # the following test is disabled because it will currently fail
        pytest.param("admin0", "admin1", RESULT_FAIL, marks=pytest.mark.xfail(reason="TODO: blame why")),
    ],
)
def test_password_reset_acl(ucr, schoolenv, actor, target, expected_result):
    tc = _TestCases(ucr, schoolenv)
    tc.test_pw_reset(getattr(tc, actor), getattr(tc, target), expected_result)
