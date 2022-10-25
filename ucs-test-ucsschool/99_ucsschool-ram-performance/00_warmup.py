#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## -*- coding: utf-8 -*-
## desc: check performance of POST /ucsschool/bff-users/v1/users/
## tags: [ucsschool-bff-users, performance]
## exposure: dangerous
## packages: []
## bugs: []

import os

import pytest
from conftest import BFF_DEFAULT_HOST, set_locust_environment_vars

BASE_DIR = "/var/lib/ram-performance-tests/"
LOCUST_FILES_DIRNAME = "locustfiles"
LOCUST_FILE = "locust_users_post.py"
RESULT_FILES_NAME = "warmup"


RESULT_DIR = os.path.join(BASE_DIR, "warmup_results")
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
LOCUST_FILES_DIR = os.path.join(TEST_DIR, LOCUST_FILES_DIRNAME)
LOCUST_FILE_PATH = os.path.join(LOCUST_FILES_DIR, LOCUST_FILE)

RESULT_FILE_BASE_PATH = os.path.join(RESULT_DIR, RESULT_FILES_NAME)
BFF_USERS_HOST = BFF_DEFAULT_HOST
URL_NAME = "/ucsschool/bff-users/v1/users/"


@pytest.fixture(scope="module")
def create_result_dir():
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)


@pytest.fixture(scope="module")
def run_test(execute_test, verify_test_sent_requests, create_result_dir):
    set_locust_environment_vars(LOCUST_ENV_VARIABLES)
    execute_test(LOCUST_FILE_PATH, RESULT_FILE_BASE_PATH, BFF_USERS_HOST)
    # fail in fixture, so pytest prints the output of Locust,
    # regardless which test_*() function started Locust
    verify_test_sent_requests(RESULT_FILE_BASE_PATH)


LOCUST_ENV_VARIABLES = {
    "LOCUST_RUN_TIME": "1m30s",
    "LOCUST_SPAWN_RATE": "4",
    "LOCUST_STOP_TIMEOUT": "30",
    "LOCUST_USERS": "4",
}

# As this is only a warmup, the test passes when run_test finishes without exceptions
# note that failing requests do not make this test fail


def test_warmup(run_test):
    pass
