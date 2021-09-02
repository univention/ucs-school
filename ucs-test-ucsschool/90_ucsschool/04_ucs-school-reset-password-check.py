#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: ucs-school-reset-password-check
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-users]

from __future__ import print_function

from datetime import datetime, timedelta
import pytest

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm as udm_test
import univention.testing.utils as utils
from univention.lib.umc import Forbidden, HTTPError
from univention.testing.umc import Client

try:
    from univention.admin.syntax import ActivationDateTimeTimezone
    check_accountActivationDate = True
except ImportError:
    check_accountActivationDate = False

def auth(host, username, password):
    try:
        client = Client(host)
        return client.authenticate(username, password)
    except HTTPError as exc:
        return exc.response


def _test_pwd_reset(
    host,
    acting_user,
    flavor,
    target_user,
    target_userdn,
    chg_pwd_on_next_login,
    expected_reset_result,
    expected_auth_for_old_password,
    expected_auth_for_new_password,
    expect_password_expired=False,
):
    newpassword = uts.random_string()
    options = {"userDN": target_userdn, "newPassword": newpassword, "nextLogin": chg_pwd_on_next_login}
    client = Client(host, acting_user, "univention")

    def reset():
        try:
            return client.umc_command("schoolusers/password/reset", options, flavor).result
        finally:
            utils.wait_for_replication()
            utils.wait_for_connector_replication()

    if isinstance(expected_reset_result, type) and issubclass(expected_reset_result, Exception):
        with pytest.raises(expected_reset_result):
            reset()
    else:
        assert (
            reset() == expected_reset_result
        ), "umcp command schoolusers/password/reset was unexpectedly successful"

    # test if old password does NOT work
    auth_response = auth(host, target_user, "univention")
    if auth_response.status != expected_auth_for_old_password:
        utils.fail(
            "old password: unexpected authentication result=%s, expected=%s"
            % (auth_response.status, expected_auth_for_old_password)
        )

    # test if new password does work
    auth_response = auth(host, target_user, newpassword)
    if auth_response.status != expected_auth_for_new_password:
        utils.fail(
            "new password: unexpected authentication result=%s, expected=%s"
            % (auth_response.status, expected_auth_for_new_password)
        )

    if expect_password_expired:
        assert auth_response.result.get("password_expired"), "The password is not expired - as expected."


@pytest.fixture(scope="session")
def school_environment():
    ucr = ucr_test.UCSTestConfigRegistry()
    ucr.load()
    host = ucr.get("hostname")

    now = datetime.now()
    with open("/etc/timezone", "r") as tzfile:
        timezone = tzfile.read().strip()
    ts_later = (now + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M " + timezone)

    with utu.UCSTestSchool() as schoolenv, udm_test.UCSTestUDM() as udm:
        schoolName, oudn = schoolenv.create_ou(name_edudc=host)
        teachers = []
        teachersDn = []
        students = []
        studentsDn = []
        admins = []
        adminsDn = []
        for i in range(5 if check_accountActivationDate else 3):
            tea, teadn = schoolenv.create_user(schoolName, is_teacher=True)
            teachers.append(tea)
            teachersDn.append(teadn)
            stu, studn = schoolenv.create_user(schoolName)
            students.append(stu)
            studentsDn.append(studn)
            is_teacher = True if ucr.get("server/role") == "domaincontroller_slave" else None
            admin, admin_dn = schoolenv.create_school_admin(schoolName, is_teacher=is_teacher)
            admins.append(admin)
            adminsDn.append(admin_dn)

        if check_accountActivationDate:
            # workaround 1:
            # Can't monkeypatch ucsschool.lib.models.user.User.do_create to pass accountActivationDate directly,
            # so modify via udm
            utils.wait_for_replication_and_postrun()
            for i in range(3, 5):
                dn = studentsDn[i]
                # Workaround 2:
                # UCSTestUDM raises UCSTestUDM_CannotModifyExistingObject as it didn't create the object
                udm._cleanup.setdefault("users/user", []).append(dn)
                udm.modify_object("users/user", dn=dn, accountActivationDate=ts_later)
                udm._cleanup["users/user"].remove(dn)

        utils.wait_for_replication_and_postrun()
        yield teachers, teachersDn, students, studentsDn, admins, adminsDn


@pytest.mark.parametrize(
    "acting_user,flavor,target,target_num,chg_pwd_on_next_login,expected_reset_result,expected_auth_for_old_password,expected_auth_for_new_password,expect_password_expired",
    [
        # #1 test if teacher is unable to reset teacher password (chgPwdNextLogin=False),
        ("teachers", "teacher", "teachers", 1, False, Forbidden, 200, 401, False),

        # #2 test if teacher is unable to reset teacher password (chgPwdNextLogin=True),
        ("teachers", "teacher", "teachers", 1, True, Forbidden, 200, 401, False),

        # #3 test if student is unable to reset teacher password (chgPwdNextLogin=False),
        ("students", "teacher", "teachers", 1, False, Forbidden, 200, 401, False),

        # #4 test if student is unable to reset teacher password (chgPwdNextLogin=True),
        ("students", "teacher", "teachers", 1, True, Forbidden, 200, 401, False),

        # #5 test if student is unable to reset student password (chgPwdNextLogin=False),
        ("students", "student", "students", 1, False, Forbidden, 200, 401, False),

        # #6 test if student is unable to reset student password (chgPwdNextLogin=True),
        ("students", "student", "students", 1, True, Forbidden, 200, 401, False),

        # #7 test if teacher is able to reset student password (chgPwdNextLogin=False),
        ("teachers", "student", "students", 0, False, True, 401, 200, False),

        # #8 test if teacher is able to reset student password (chgPwdNextLogin=True),
        ("teachers", "student", "students", 1, True, True, 401, 401, True),

        # #15 test if teacher is able to reset student password (chgPwdNextLogin=False, still disabled with accountActivationDate),
        ("teachers", "student", "students", 3, False, True, 401, 401 if check_accountActivationDate else 200, False),

        # #16 test if teacher is able to reset student password (chgPwdNextLogin=True, still disabled with accountActivationDate),
        ("teachers", "student", "students", 4, True, True, 401, 401, True),

        # #9 test if schooladmin is able to reset student password (chgPwdNextLogin=False),
        ("admins", "student", "students", 0, False, True, 401, 200, False),

        # #10 test if schooladmin is able to reset student password (chgPwdNextLogin=True),
        ("admins", "student", "students", 2, True, True, 401, 401, False),

        # #19 test if schooladmin is able to reset student password (chgPwdNextLogin=False, still disabled with accountActivationDate),
        ("admins", "student", "students", 3, False, True, 401, 401 if check_accountActivationDate else 200, False),

        # #20 test if schooladmin is able to reset student password (chgPwdNextLogin=True, still disabled with accountActivationDate),
        ("admins", "student", "students", 4, True, True, 401, 401, False),

        # #11 test if schooladmin is able to reset teacher password (chgPwdNextLogin=False),
        ("admins", "student", "teachers", 0, False, True, 401, 200, False),

        # #12 test if schooladmin is able to reset teacher password (chgPwdNextLogin=True),
        ("admins", "student", "teachers", 1, True, True, 401, 401, False),

        # DISABLED DUE TO BUG 35447:
        # #13 test if schooladmin is able to reset admin password (chgPwdNextLogin=False),
        # pytest.param(
        #     "admins",
        #     "student",
        #     "admins",
        #     1,
        #     False,
        #     Forbidden,
        #     200,
        #     401,
        #     False,
        #     marks=pytest.mark.xfail(reason="Bug #35447"),
        # ),
        # # #14 test if schooladmin is able to reset admin password (chgPwdNextLogin=True)
        # pytest.param(
        #     "admins",
        #     "student",
        #     "admins",
        #     2,
        #     True,
        #     Forbidden,
        #     200,
        #     401,
        #     False,
        #     marks=pytest.mark.xfail(reason="Bug #35447"),
        # ),
    ],
)
def test_password_reset(
    ucr,
    school_environment,
    acting_user,
    flavor,
    target,
    target_num,
    chg_pwd_on_next_login,
    expected_reset_result,
    expected_auth_for_new_password,
    expected_auth_for_old_password,
    expect_password_expired,
):
    host = ucr.get("hostname")
    teachers, teachersDn, students, studentsDn, admins, adminsDn = school_environment
    users = {"teachers": teachers, "students": students, "admins": admins}
    dns = {"teachers": teachersDn, "students": studentsDn, "admins": adminsDn}
    ("teachers", "teacher", "teachers", 1, True, Forbidden, 200, 401)
    _test_pwd_reset(
        host,
        users[acting_user][0],
        flavor,
        users[target][target_num],
        dns[target][target_num],
        chg_pwd_on_next_login,
        expected_reset_result,
        expected_auth_for_old_password,
        expected_auth_for_new_password,
        expect_password_expired=False,
    )
