#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-reset-password-check
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1,ucs-school-umc-users]
## exposure: dangerous
## packages: [ucs-school-umc-users]

from __future__ import print_function

import contextlib
import time
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Generator, List

import pytest

import univention.testing.active_directory as ad
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
from univention.lib.umc import BadRequest, Forbidden, HTTPError
from univention.testing import utils
from univention.testing.umc import Client
from univention.testing.utils import package_installed

INIT_PASSWORD = "univention"
LOCKOUT_ATTEMPTS = 3


def random_password() -> str:
    return uts.random_string()


def simple_password() -> str:
    return "password123"


def auth(host, username, password):
    try:
        client = Client(host)
        return client.authenticate(username, password)
    except HTTPError as exc:
        return exc.response


@contextlib.contextmanager
def samba_account_lockout_policy(
    threshold: int = 3, duration: int = 30, reset_after: int = 30
) -> Generator[None, None, None]:
    """Enable Samba account-lockout policy for the duration of the with-block, then restore."""
    domain_pw = ad.DomainPasswordSettings(ad.ActiveDirectorySettings(is_local_connect=True))
    original = domain_pw.get()
    domain_pw.set(
        ad.DomainPasswordsettingsData(
            account_lockout_threshold=threshold,
            account_lockout_duration=duration,
            reset_account_lockout_after=reset_after,
        )
    )
    try:
        yield
    finally:
        try:
            domain_pw.set(original)
        except ad.SambaToolException as exc:
            msg = "Teardown failed while restoring Samba password policy: %s" % (exc,)
            warnings.warn(msg, RuntimeWarning, stacklevel=2)


@pytest.fixture(autouse=True)
def _samba_lockout_policy_for_test(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Wrap tests that set `lock_target_user_before_reset` with the Samba lockout policy.

    The policy is restored after the test regardless of pass or failure.
    """
    callspec = getattr(request.node, "callspec", None)
    params: TestCaseData | None = callspec.params.get("params") if callspec else None
    if params and params.lock_target_user_before_reset:
        with samba_account_lockout_policy(threshold=LOCKOUT_ATTEMPTS):
            yield
    else:
        yield


@pytest.fixture(autouse=True)
def _eventually_skip_samba_lockout_tests(request: pytest.FixtureRequest) -> None:
    """Skip Samba lockout test cases when `univention-samba4` not installed."""
    callspec = getattr(request.node, "callspec", None)
    params: TestCaseData | None = callspec.params.get("params") if callspec else None
    if params and params.lock_target_user_before_reset:
        if not package_installed("univention-samba4"):
            pytest.skip("Samba lockout reset cases require univention-samba4")


def wait_for_lockout_in_ldap(userdn: str, timeout: int = 120, delay: float = 1.0) -> None:
    """
    Wait until the Samba lockout of `userdn` has arrived in OpenLDAP.

    The failed logins lock the account in the Samba SAM only. UDM derives its `locked`
    property from `sambaAcctFlags` in OpenLDAP, so a password reset only resets the bad
    password counters - and with them the lockout in Samba - once the S4 connector has
    back-synced `lockoutTime`. Resetting before that leaves the account locked out in
    Samba although the reset itself succeeds.
    """
    utils.wait_for_replication_from_local_samba_to_local_openldap()

    # The waits above only warn when the S4 connector does not catch up in time, so poll
    # for the lock flag instead of relying on them.
    lo = utils.get_ldap_connection()
    deadline = time.monotonic() + timeout
    while True:
        flags = lo.getAttr(userdn, "sambaAcctFlags")
        if flags and b"L" in flags[0]:
            return
        if time.monotonic() >= deadline:
            utils.fail(
                "sambaAcctFlags of %s still lacks the lock flag %r after %d seconds"
                % (userdn, flags, timeout)
            )
        time.sleep(delay)


def lock_user_with_wrong_samba_password(username: str, userdn: str, attempts: int) -> None:
    """Lock the given user by attempting to authenticate with a wrong password repeatedly."""
    shares = ad.Shares(settings=ad.ActiveDirectorySettings(is_local_connect=True))
    for _ in range(attempts):
        # We intentionally expect authentication failures here to trigger lockout.
        with contextlib.suppress(
            ad.LogonFailureException,
            ad.AccountLockedOutException,
            ad.SmbClientException,
        ):
            shares.list(username, "wrong_pwd")

    # verify that the account is actually locked
    with pytest.raises((ad.AccountLockedOutException)):
        ad.Shares(settings=ad.ActiveDirectorySettings(is_local_connect=True)).list(
            username, INIT_PASSWORD
        )

    wait_for_lockout_in_ldap(userdn)


def validate_samba_login(target_user: str, new_password: str) -> None:
    samba_login_error = None
    try:
        ad.Shares(settings=ad.ActiveDirectorySettings(is_local_connect=True)).list(
            target_user, new_password
        )
    except (
        ad.AccountLockedOutException,
        ad.LogonFailureException,
        ad.SmbClientException,
    ) as exc:
        samba_login_error = exc
    assert samba_login_error is None, (
        "Samba login with new password failed after reset: %s" % samba_login_error
    )


class Entity(Enum):
    TEACHER = "teacher"
    STUDENT = "student"
    ADMIN = "admin"


@dataclass
class TestCaseData:
    acting_user: Entity
    flavor: str
    target: Entity
    chg_pwd_on_next_login: bool
    expected_reset_result: Exception | bool
    expected_auth_for_old_password: int
    expected_auth_for_new_password: int
    expect_password_expired: bool
    password_generator: Callable[[], str]
    lock_target_user_before_reset: bool = False


@dataclass
class UserStack:
    """
    User stack for a test run

    Motivation: Create users only once per test module, because user creation is
    time-consuming. If a test modifies the state (like changing passwords), a
    new stack must be created for the next test. Thus we can save execution time
    by reusing a stack as long as it is not modified.
    """

    host: str
    users: Dict[Entity, str]
    dns: Dict[Entity, str]

    _modified: bool = False

    def set_modified(self) -> None:
        self._modified = True


InfixtureType = Callable[[], UserStack]


@pytest.fixture(scope="module")
def school_environment() -> Generator[InfixtureType, None, None]:
    ucr = ucr_test.UCSTestConfigRegistry()
    ucr.load()
    host = ucr.get("hostname")
    with utu.UCSTestSchool() as schoolenv:
        schoolName, _ = schoolenv.create_ou(name_edudc=host)
        policy_dn = schoolenv.create_password_policy(schoolName)
        stacks: List[UserStack] = []

        def make_test_data_stack() -> UserStack:
            if stacks and not stacks[-1]._modified:
                return stacks[-1]

            # create new stack
            teacher, teacherDn = schoolenv.create_user(schoolName, is_teacher=True)
            schoolenv.modify_object_add_policy(teacherDn, policy_dn)
            student, studentDn = schoolenv.create_user(schoolName)
            schoolenv.modify_object_add_policy(studentDn, policy_dn)
            is_teacher = True if ucr.get("server/role") == "domaincontroller_slave" else None
            admin, adminDn = schoolenv.create_school_admin(schoolName, is_teacher=is_teacher)
            schoolenv.modify_object_add_policy(adminDn, policy_dn)

            utils.wait_for_replication()

            stacks.append(
                UserStack(
                    host,
                    users={Entity.TEACHER: teacher, Entity.STUDENT: student, Entity.ADMIN: admin},
                    dns={Entity.TEACHER: teacherDn, Entity.STUDENT: studentDn, Entity.ADMIN: adminDn},
                )
            )
            return stacks[-1]

        yield make_test_data_stack


@pytest.mark.parametrize(
    "params",
    [
        pytest.param(
            TestCaseData(
                acting_user=Entity.TEACHER,
                flavor="teacher",
                target=Entity.TEACHER,
                chg_pwd_on_next_login=True,
                expected_reset_result=Forbidden,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#1: Teacher is unable to reset teacher password (chgPwdNextLogin=True)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.STUDENT,
                flavor="teacher",
                target=Entity.TEACHER,
                chg_pwd_on_next_login=True,
                expected_reset_result=Forbidden,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#2: Student is unable to reset teacher password (chgPwdNextLogin=True)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.STUDENT,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=True,
                expected_reset_result=Forbidden,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#3: Student is unable to reset student password (chgPwdNextLogin=True)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.TEACHER,
                flavor="teacher",
                target=Entity.TEACHER,
                chg_pwd_on_next_login=False,
                expected_reset_result=Forbidden,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#4: Teacher is unable to reset teacher password (chgPwdNextLogin=False)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.STUDENT,
                flavor="teacher",
                target=Entity.TEACHER,
                chg_pwd_on_next_login=False,
                expected_reset_result=Forbidden,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#5: Student is unable to reset teacher password (chgPwdNextLogin=False)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.STUDENT,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=False,
                expected_reset_result=Forbidden,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#6: Student is unable to reset student password (chgPwdNextLogin=False)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.TEACHER,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=True,
                expected_reset_result=True,
                expected_auth_for_old_password=401,
                expected_auth_for_new_password=401,
                expect_password_expired=True,
                password_generator=random_password,
            ),
            id="#7: Teacher is able to reset student password (chgPwdNextLogin=True)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.TEACHER,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=False,
                expected_reset_result=True,
                expected_auth_for_old_password=401,
                expected_auth_for_new_password=200,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#8: Teacher is able to reset student password (chgPwdNextLogin=False)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.ADMIN,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=False,
                expected_reset_result=True,
                expected_auth_for_old_password=401,
                expected_auth_for_new_password=200,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#9: Schooladmin is able to reset student password (chgPwdNextLogin=False)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.ADMIN,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=True,
                expected_reset_result=True,
                expected_auth_for_old_password=401,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#10: Schooladmin is able to reset student password (chgPwdNextLogin=True)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.ADMIN,
                flavor="student",
                target=Entity.TEACHER,
                chg_pwd_on_next_login=False,
                expected_reset_result=True,
                expected_auth_for_old_password=401,
                expected_auth_for_new_password=200,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#11: Schooladmin is able to reset teacher password (chgPwdNextLogin=False)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.ADMIN,
                flavor="student",
                target=Entity.TEACHER,
                chg_pwd_on_next_login=True,
                expected_reset_result=True,
                expected_auth_for_old_password=401,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#12: Schooladmin is able to reset teacher password (chgPwdNextLogin=True)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.ADMIN,
                flavor="student",
                target=Entity.ADMIN,
                chg_pwd_on_next_login=False,
                expected_reset_result=Forbidden,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#13: Schooladmin is able to reset admin password (chgPwdNextLogin=False)",
            marks=pytest.mark.xfail(reason="Bug #35447"),
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.ADMIN,
                flavor="student",
                target=Entity.ADMIN,
                chg_pwd_on_next_login=True,
                expected_reset_result=Forbidden,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=random_password,
            ),
            id="#14: Schooladmin is able to reset admin password (chgPwdNextLogin=True)",
            marks=pytest.mark.xfail(reason="Bug #35447"),
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.TEACHER,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=False,
                expected_reset_result=BadRequest,
                expected_auth_for_old_password=200,
                expected_auth_for_new_password=401,
                expect_password_expired=False,
                password_generator=simple_password,
            ),
            id="#15: Teacher fails to reset student password to simple password (chgPwdNextLogin=False)",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.TEACHER,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=False,
                expected_reset_result=True,
                expected_auth_for_old_password=401,
                expected_auth_for_new_password=200,
                expect_password_expired=False,
                password_generator=random_password,
                lock_target_user_before_reset=True,
            ),
            id="#16: Teacher resets password of Samba-locked student",
        ),
        pytest.param(
            TestCaseData(
                acting_user=Entity.ADMIN,
                flavor="student",
                target=Entity.STUDENT,
                chg_pwd_on_next_login=False,
                expected_reset_result=True,
                expected_auth_for_old_password=401,
                expected_auth_for_new_password=200,
                expect_password_expired=False,
                password_generator=random_password,
                lock_target_user_before_reset=True,
            ),
            id="#17: Schooladmin resets password of Samba-locked student",
        ),
    ],
)
def test_password_reset(
    school_environment: InfixtureType,
    params: TestCaseData,
):
    # generates a new data stack if previous one was modified
    stack = school_environment()

    acting_user = stack.users[params.acting_user]
    target_user = stack.users[params.target]
    target_userdn = stack.dns[params.target]
    new_password = params.password_generator()
    options = {
        "userDN": target_userdn,
        "newPassword": new_password,
        "nextLogin": params.chg_pwd_on_next_login,
    }

    client = Client(stack.host, acting_user, INIT_PASSWORD)

    if params.lock_target_user_before_reset:
        lock_user_with_wrong_samba_password(target_user, target_userdn, attempts=LOCKOUT_ATTEMPTS)

    def reset():
        try:
            result = client.umc_command("schoolusers/password/reset", options, params.flavor).result
            if result is True:
                stack.set_modified()
            return result
        finally:
            utils.wait_for_replication()
            utils.wait_for_connector_replication()

    if isinstance(params.expected_reset_result, type) and issubclass(
        params.expected_reset_result, Exception
    ):
        with pytest.raises(params.expected_reset_result):
            reset()
    else:
        assert reset() == params.expected_reset_result, (
            "umcp command schoolusers/password/reset was unexpectedly successful"
        )

    if params.lock_target_user_before_reset and params.expected_reset_result is True:
        validate_samba_login(target_user, new_password)

    # test if old password does NOT work
    auth_response = auth(stack.host, target_user, INIT_PASSWORD)
    if auth_response.status != params.expected_auth_for_old_password:
        utils.fail(
            "old password: unexpected authentication result=%s, expected=%s"
            % (auth_response.status, params.expected_auth_for_old_password)
        )

    # test if new password does work
    auth_response = auth(stack.host, target_user, new_password)
    if auth_response.status != params.expected_auth_for_new_password:
        utils.fail(
            "new password: unexpected authentication result=%s, expected=%s"
            % (auth_response.status, params.expected_auth_for_new_password)
        )

    if params.expect_password_expired:
        assert auth_response.result.get("password_expired"), "The password is not expired - as expected."
