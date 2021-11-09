#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test if input_data is filled in during pre_/post_delete hooks
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [46384, 46439]

import os
import os.path
import shutil
import subprocess
import sys

import pytest

from univention.testing.ucsschool.ucs_test_school import get_ucsschool_logger

TESTHOOKSOURCE = os.path.join(os.path.dirname(__file__), "test228_input_data_pyhookpy")
TESTHOOKTARGET = "/usr/share/ucs-school-import/pyhooks/test228_input_data_pyhook.py"

logger = get_ucsschool_logger()
logger.info("*** Copying %r to %r...", TESTHOOKSOURCE, TESTHOOKTARGET)
shutil.copy2(TESTHOOKSOURCE, TESTHOOKTARGET)


@pytest.fixture
def cleanup():
    yield
    for ext in ["", "c", "o"]:
        try:
            os.remove("{}{}".format(TESTHOOKTARGET, ext))
            logger.info("*** Deleted %s%s...", TESTHOOKTARGET, ext)
        except OSError:
            logger.warning("*** Could not delete %s%s.", TESTHOOKTARGET, ext)


def test_import_user_input_data_in_pyhooks(ucr, schoolenv, cleanup):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))

    print("*** Running import - 1st to create users, 2nd to remove them.")

    cmd = [
        "/usr/share/ucs-school-import/scripts/ucs-school-testuser-import",
        "-v",
        "--create-email-addresses",
        "--classes",
        "1",
        "--students",
        "2",
        ou_name,
    ]
    sys.stdout.flush()
    sys.stderr.flush()
    exitcode = subprocess.call(cmd)
    print("*** Ignoring result of 1st import (exit code {!r})".format(exitcode))

    print("*** Running import 2nd time - must fail.")

    cmd = [
        "/usr/share/ucs-school-import/scripts/ucs-school-testuser-import",
        "-v",
        "--create-email-addresses",
        "--classes",
        "1",
        "--students",
        "2",
        ou_name,
    ]
    sys.stdout.flush()
    sys.stderr.flush()
    exitcode = subprocess.call(cmd)
    assert exitcode != 0, "Import did not fail, although it should."
    print("*** OK: import process fail (exit code {!r})".format(exitcode))

    logger.info("*** OK: Test was successful.\n\n\n")
