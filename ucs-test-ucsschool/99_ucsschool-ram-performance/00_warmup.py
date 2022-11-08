#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## -*- coding: utf-8 -*-
## desc: warmup backends with route POST /ucsschool/bff-users/v1/users/
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
LOCUST_USER_CLASS = "CreateUser"
RESULT_FILES_NAME = "warmup"
URL_NAME = "/ucsschool/bff-users/v1/users/"
LOCUST_FILE_PATH = os.path.join(LOCUST_FILES_DIR, LOCUST_FILE)
RESULT_FILE_BASE_PATH = os.path.join(RESULT_DIR, RESULT_FILES_NAME)


@pytest.fixture(scope="module")
def create_result_dir():
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)


@pytest.fixture(scope="module")
def run_test(execute_test, verify_test_sent_requests, create_result_dir):
    set_locust_environment_vars(LOCUST_ENV_VARIABLES)
    execute_test(LOCUST_FILE_PATH, LOCUST_USER_CLASS, RESULT_FILE_BASE_PATH, BFF_DEFAULT_HOST)
    # fail in fixture, so pytest prints the output of Locust,
    # regardless which test_*() function started Locust
    verify_test_sent_requests(RESULT_FILE_BASE_PATH)


LOCUST_ENV_VARIABLES = copy.deepcopy(ENV_LOCUST_DEFAULTS)
LOCUST_ENV_VARIABLES["LOCUST_RUN_TIME"] = "1m30s"
LOCUST_ENV_VARIABLES["LOCUST_SPAWN_RATE"] = "4"
LOCUST_ENV_VARIABLES["LOCUST_USERS"] = "4"
LOCUST_ENV_VARIABLES["LOCUST_STOP_TIMEOUT"] = "30"

# As this is only a warmup, the test passes when run_test finishes without exceptions
# note that failing requests do not make this test fail


def test_warmup(run_test):
    pass
