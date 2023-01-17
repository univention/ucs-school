#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## -*- coding: utf-8 -*-
## desc: check performance of GET /ucsschool/bff-users/v1/pageconf/addView
## tags: [ucsschool-bff-users, performance]
## exposure: dangerous
import copy
import os

import pytest
from conftest import (
    BFF_DEFAULT_HOST,
    ENV_LOCUST_DEFAULTS,
    LOCUST_FILES_DIR,
    RESULT_DIR,
    set_locust_environment_vars,
)

LOCUST_FILE = "generic_user_bff_users.py"
LOCUST_USER_CLASS = "GetPagesAddViewSettings"
RESULT_FILES_NAME = "bff-users-pages-addView-settings-get"
URL_NAME = "/ucsschool/bff-users/v1/pageconf/addView"
LOCUST_FILE_PATH = os.path.join(LOCUST_FILES_DIR, LOCUST_FILE)
RESULT_FILE_BASE_PATH = os.path.join(RESULT_DIR, RESULT_FILES_NAME)


@pytest.fixture(scope="module")
def create_result_dir():
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)


@pytest.fixture(scope="module")
def run_test(execute_test, verify_test_sent_requests, create_result_dir, sleep10):
    set_locust_environment_vars(LOCUST_ENV_VARIABLES)
    execute_test(LOCUST_FILE_PATH, LOCUST_USER_CLASS, RESULT_FILE_BASE_PATH, BFF_DEFAULT_HOST)
    # fail in fixture, so pytest prints the output of Locust,
    # regardless which test_*() function started Locust
    verify_test_sent_requests(RESULT_FILE_BASE_PATH)


# The only requirement from https://git.knut.univention.de/groups/univention/-/epics/379
# is: The time to get the addView must be below 2 seconds.
# At the time of writing, the number of concurrent users is still unknown.

LOCUST_ENV_VARIABLES = copy.deepcopy(ENV_LOCUST_DEFAULTS)
LOCUST_ENV_VARIABLES["LOCUST_RUN_TIME"] = "2m"
LOCUST_ENV_VARIABLES["LOCUST_SPAWN_RATE"] = "0.4"
LOCUST_ENV_VARIABLES["LOCUST_USERS"] = str(4 * 3 * 4)  # 4 parallel per CPU on 3 backups with 4 CPUs


def test_failure_count(check_failure_count, run_test):
    check_failure_count(RESULT_FILE_BASE_PATH)


def test_rps(check_rps, run_test):
    check_rps(RESULT_FILE_BASE_PATH, URL_NAME, 0.5)


def test_95_percentile(check_95_percentile, run_test):
    check_95_percentile(RESULT_FILE_BASE_PATH, URL_NAME, 2000)
