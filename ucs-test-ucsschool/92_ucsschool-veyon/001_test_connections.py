#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## desc: test veyon connection management
## tags: [ucs_school_veyon]
## exposure: dangerous
## packages: [ucs-school-veyon-client, python3-molotov]
## bugs: [53558]

from subprocess import check_call

import pytest

_APP = "ucsschool-veyon-proxy"
_MOLOTOV_FILE = "molotov_veyon_connections.py"


@pytest.fixture()
def molotov():
    def _run_molotov(scenario, processes):
        check_call(
            [
                "molotov",
                _MOLOTOV_FILE,
                "-f",
                "1",
                "-s",
                scenario,
                "-p",
                str(processes),
                "-r" "1",
            ]
        )

    return _run_molotov


@pytest.fixture(autouse=True)
def run_around_tests():
    check_call(["univention-app", "restart", _APP])
    yield
    check_call(["univention-app", "restart", _APP])


def test_unauthenticated_to_invalid_host(molotov):
    molotov("unauthenticated_not_exists", 250)


def test_unauthenticated_to_valid_host(molotov):
    molotov("unauthenticated_exists", 1000)


def test_with_authenticated_existing_session(molotov):
    molotov("authenticated_existing_session", 1000)


def test_with_authenticated_new_session(molotov):
    molotov("authenticated_new_session", 40)
