#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-reset-password-check
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-users]
## timeout: 14400

from __future__ import print_function

import sys
from pprint import pprint

from ldap.filter import filter_format

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
from univention.testing import utils
from univention.lib.umc import Forbidden, HTTPError
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.umc import Client

EXPECT_OK = 1
EXPECT_DISALLOW = 2
EXPECT_LOGIN_FAIL = 3

ucr = ucr_test.UCSTestConfigRegistry()
ucr.load()
is_domaincontroller_slave = ucr.get("server/role") == "domaincontroller_slave"


class PasswordReset(object):
    connections = {}

    def __init__(self, host, flavor, username, password="univention"):
        self.host = host
        self.flavor = flavor
        self.username = username
        self.password = password
        if self.username not in self.connections:  # caching :)
            self.connections[self.username] = Client(self.host, self.username, self.password)
        self.connection = self.connections[self.username]

    def __repr__(self):
        return "PasswordReset(%r, %r, %r, %r)" % (self.host, self.flavor, self.username, self.password)

    def test_login(self, user, password):
        print("%r.test_login(%r, %r)" % (self, user, password))
        try:
            client = Client(self.host)
            return client.authenticate(user, password)
        except HTTPError as exc:
            return exc.response

    def change_password(self, target_user, new_password, change_password_on_next_login):
        print(
            "%r.change_password(%r, %r, %r)"
            % (
                self,
                target_user,
                new_password,
                change_password_on_next_login,
            )
        )
        options = {
            "userDN": target_user[1],
            "newPassword": new_password,
            "nextLogin": change_password_on_next_login,
        }
        return self.connection.umc_command("schoolusers/password/reset", options, self.flavor).result

    def assert_password_change(self, user, new_password, change_password_on_next_login):
        print("%r.assert_password_change(%r, %r)" % (self, user, change_password_on_next_login))
        try:
            response = self.change_password(
                user, new_password, change_password_on_next_login=change_password_on_next_login
            )
        except HTTPError as exc:
            assert False, "Could not change password: %s" % (exc,)
        assert isinstance(response, bool) and response is True, "Failed to reset password: %r" % (
            response,
        )

    def assert_login(self, user, old_password, new_password, change_password_on_next_login):
        print(
            "%s.assert_login(%r, old_password=%r, new_password=%r, "
            "change_password_on_next_login=%r)"
            % (self, user, old_password, new_password, change_password_on_next_login)
        )
        login = self.test_login(user, old_password)
        assert 401 == login.status, "The user could login with the old password: status=%r" % (
            login.status,
        )

        login = self.test_login(user, new_password)
        if change_password_on_next_login:
            assert (
                login.status == 401
            ), "The user could login with new password and chgPwdNextLogin=True: status=%r" % (
                login.status,
            )
            assert login.result and login.result.get(
                "password_expired"
            ), "The password is not expired - as expected"
        else:
            assert (
                login.status == 200
            ), "The user could not login with new password and chgPwdNextLogin=False: status=%r" % (
                login.status,
            )

    def assert_password_change_fails(self, user):
        print("%r.assert_password_change_fails(%r)" % (self, user))
        new_password = uts.random_string()
        try:
            response = self.change_password(user, new_password, change_password_on_next_login=True)
        except Forbidden:
            pass  # no permissions to open the UMC module at all :-)
        except HTTPError as exc:
            # LDAP ACL's don't allow password change of that user
            assert (
                "permission denied" in str(exc).lower()
            ), 'Exception did not contain "permission denied": %s' % (exc,)
        else:
            assert False, "did not fail: %r" % (response,)


class Error(Exception):
    pass


class _TestPasswordResetStaff:
    def __init__(self, schoolenv, school, host):
        self.schoolenv = schoolenv
        self.school = school
        self.host = host

    def run_test(self):
        staff_user = self.schoolenv.create_staff(self.school)
        ou_admin_name, ou_admin_dn = self.schoolenv.create_school_admin(self.school)
        teacher_name, teacher_dn = self.schoolenv.create_teacher(self.school)
        admin_pw_reset = PasswordReset(self.host, "staff", ou_admin_name)
        teacher_pw_reset = PasswordReset(self.host, "staff", teacher_name)
        teacher_pw_reset.assert_password_change_fails(staff_user)
        admin_pw_reset.assert_password_change(staff_user, "jksdhgf983048ghsd", False)


class _TestPasswordReset(object):
    def __init__(self, schoolenv, school, host):
        self.schoolenv = schoolenv
        self.school = school
        self.host = host
        self.errors = []
        testdata = list(self.get_testdata())
        self.changed_password = []
        utils.wait_for_replication_and_postrun()

        # change all passwords
        for test in testdata:
            try:
                if self.test_password_changing(**test):
                    self.changed_password.append(test)
            except Error as exc:
                self.errors.append(dict(test, ERROR=str(exc)))

        # wait for all new passwords to be replicated
        utils.wait_for_replication_and_postrun()
        error_message = "Pre-Errors: errors=%d changed_passwords=%d" % (
            len(self.errors),
            len(self.changed_password),
        )

        # check if login succeeds with new password and not anymore with old password
        for test in self.changed_password:
            try:
                self.test_umc_authentication(**test)
            except Error as exc:
                self.errors.append(dict(test, ERROR=str(exc)))

        if self.errors:
            pprint(self.errors, sys.stderr, width=120)
            utils.fail(
                "%s. %d of %d errors occurred." % (error_message, len(self.errors), len(testdata))
            )

    def get_testdata(self):
        for flavor in ("teacher", "student"):
            for change_password_on_next_login in (True, False):
                for identification, expected_result, actor, target in self.create_test_users(flavor):
                    yield {
                        "identification": identification,
                        "old_password": "univention",
                        "new_password": uts.random_string(),
                        "expected_result": expected_result,
                        "actor": actor,
                        "target": target,
                        "change_password_on_next_login": change_password_on_next_login,
                        "flavor": flavor,
                    }

    def create_test_users(self, flavor):
        # expect_flavor_student_disallow = EXPECT_DISALLOW
        # expect_flavor_teacher_allow = EXPECT_OK if flavor == 'teacher' else EXPECT_DISALLOW
        # expect_flavor_teacher_disallow = EXPECT_DISALLOW
        expect_flavor_student_allow = EXPECT_OK if flavor == "student" else EXPECT_DISALLOW
        schoolenv, school = self.schoolenv, self.school
        kw = dict(wait_for_replication=False)
        # create_school_admin() creates a new teacher, teacher_and_staff or staff user and converts
        # it to a school admin. Since staff users are not replicated to Replica Directory Nodes, we
        # have to assure on Replica Directory Nodes, that only teachers are used for school admins.
        is_teacher = True if is_domaincontroller_slave else None
        # we have the following roles:
        # global user, domain admin, school admin, teacher, staff, teacher+staff, student
        domain_admin = schoolenv.create_domain_admin(school)
        school_admin = schoolenv.create_school_admin(school, is_teacher=is_teacher, **kw)
        teacher = schoolenv.create_teacher(school, **kw)
        teacher_and_staff = schoolenv.create_teacher_and_staff(school, **kw)

        # school admins, domain admins, teachers, teachers and staff should ...
        for i, actor in enumerate([domain_admin, school_admin, teacher, teacher_and_staff]):
            # TODO: add another user at a different school but with the local school as 'schools'
            # TODO: should a teacher be allowed to reset another's teacher password?

            # ... reset password of students
            expect = expect_flavor_student_allow if actor in (teacher, teacher_and_staff) else EXPECT_OK
            yield "%d-a" % i, expect, actor, schoolenv.create_student(school, **kw)

            # school admins, domain admins should be able to reset the other roles
            # teachers, teachers and staff should not be able to reset passwords of other roles
            expect = EXPECT_OK if actor not in (teacher, teacher_and_staff) else EXPECT_DISALLOW
            yield "%s-b" % i, expect, actor, schoolenv.create_teacher(school, **kw)
            yield "%s-c" % i, expect, actor, schoolenv.create_teacher_and_staff(school, **kw)
            if not is_domaincontroller_slave:
                # staff users are never replicated to educational school Replica Nodes - skip test
                yield "%s-d" % i, expect, actor, schoolenv.create_staff(school, **kw)
            expect = EXPECT_OK if actor in (domain_admin,) else EXPECT_DISALLOW
            yield "%s-e" % i, expect, actor, schoolenv.create_school_admin(school, is_teacher=is_teacher)
            yield "%s-f" % i, expect, actor, schoolenv.create_domain_admin(school)

            # ... not be able to reset a global user
            expect = EXPECT_DISALLOW if actor != domain_admin else EXPECT_OK
            yield "%s-g" % i, expect, actor, schoolenv.create_global_user()

        # students and staff users should not be able to change passwords
        student = schoolenv.create_student(school)
        tasks = [(student, EXPECT_DISALLOW)]
        if (
            not is_domaincontroller_slave
        ):  # staff users are never replicated to educational school Replica Nodes - skip test
            staff = schoolenv.create_staff(school)
            tasks.append((staff, EXPECT_DISALLOW))
        for i, (actor, expect) in enumerate(tasks):
            yield "%s-h" % i, expect, actor, schoolenv.create_teacher(school, **kw)
            yield "%s-i" % i, expect, actor, schoolenv.create_teacher_and_staff(school, **kw)
            if not is_domaincontroller_slave:
                # staff users are never replicated to educational school Replica Nodes - skip test
                yield "%s-j" % i, expect, actor, schoolenv.create_staff(school, **kw)
            yield "%s-k" % i, expect, actor, schoolenv.create_school_admin(
                school, is_teacher=is_teacher, **kw
            )
            yield "%s-l" % i, expect, actor, schoolenv.create_domain_admin(school)
            yield "%s-m" % i, expect, actor, schoolenv.create_global_user()

    def test_password_changing(
        self,
        expected_result,
        actor,
        target,
        change_password_on_next_login,
        flavor,
        new_password,
        old_password,
        **_
    ):
        try:
            password_reset = PasswordReset(self.host, flavor, actor[0])
        except HTTPError:
            if expected_result == EXPECT_LOGIN_FAIL:
                return False
            raise Error("Authenticating failed")

        try:
            if expected_result == EXPECT_OK:
                print("Assert %s can change %s password" % (actor[1], target[1]))
                password_reset.assert_password_change(
                    target, new_password, change_password_on_next_login
                )
            elif expected_result == EXPECT_DISALLOW:
                print("Assert %s can not change %s password" % (actor[1], target[1]))
                password_reset.assert_password_change_fails(target)
        except AssertionError as exc:
            raise Error("Changing password: %s" % (exc,))
        else:
            return True

    def test_umc_authentication(
        self,
        expected_result,
        actor,
        target,
        change_password_on_next_login,
        flavor,
        new_password,
        old_password,
        **_
    ):
        # test login with the new password
        password_reset = PasswordReset(self.host, flavor, actor[0])
        try:
            wait_for_drs_replication(filter_format("(sAMAccountName=%s)", [target[0]]))
            password_reset.assert_login(
                target[0], old_password, new_password, change_password_on_next_login
            )
        except AssertionError as exc:
            if expected_result != EXPECT_OK:
                # the password change was disallowed to the actor. So the target still has the old
                # password
                return
            raise Error("Login after password change: %s" % (exc,))
        if expected_result != EXPECT_OK:
            raise Error(
                "Login with new password works while the password change should have been disallowed!"
            )


def test_password_reset(ucr, schoolenv):
    host = ucr.get("hostname")
    school, oudn = schoolenv.create_ou(name_edudc=host)
    if not is_domaincontroller_slave:  # Staff is not replicated to replication nodes
        _TestPasswordReset(schoolenv, school, host)
        pw_reset_staff = _TestPasswordResetStaff(schoolenv, school, host)
        pw_reset_staff.run_test()
