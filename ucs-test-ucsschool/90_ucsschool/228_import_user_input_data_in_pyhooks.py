#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test if input_data is filled in legacy during pre_/post_delete hooks
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [46384, 46439]

import os
import os.path
import random
import shutil
import string
import subprocess
import sys
import tempfile

import pytest

import univention.testing.strings as uts
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
    usernames = [uts.random_username(), uts.random_username()]
    users = [
        dict(
            mode="A",
            username=username,
            lastname=uts.random_username(),
            firstname=uts.random_username(),
            ou=ou_name,
            scool_class="{}{}".format(uts.random_int(1, 13), random.choice(string.ascii_lowercase)),
            maildomain=ucr["domainname"],
        )
        for username in usernames
    ]
    line = (
        "{mode}	{username}	{lastname}	{firstname}	{ou}	{ou}-{scool_class}		"
        "{username}m@{maildomain}	0	1	0"
    )
    print("*** Creating users {!r}...".format(usernames))

    with tempfile.NamedTemporaryFile("w+") as csv_file:
        for user in users:
            csv_file.write("{}\n".format(line.format(**user)))
        csv_file.flush()

        cmd = ["/usr/share/ucs-school-import/scripts/import_user", csv_file.name]
        sys.stdout.flush()
        sys.stderr.flush()
        exitcode = subprocess.call(cmd)
        assert not exitcode, "Import failed with exit code {!r}".format(exitcode)
        print("Import process exited with exit code {!r}".format(exitcode))

    print("*** Deleting users {!r}...".format(usernames))

    with tempfile.NamedTemporaryFile("w+") as csv_file:
        for user in users:
            user["mode"] = "D"
            csv_file.write(line.format(**user))
        csv_file.flush()

        cmd = ["/usr/share/ucs-school-import/scripts/import_user", csv_file.name]
        sys.stdout.flush()
        sys.stderr.flush()
        exitcode = subprocess.call(cmd)
        assert not exitcode, "Import failed with exit code %r" % (exitcode,)
        print("Import process exited with exit code {!r}".format(exitcode))

    print("*** Trying non-legacy import - 1st to create users, 2nd to remove them.")

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

    print("*** Trying non-legacy import 2nd time - must fail.")

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
    print("*** OK: non-legacy import process fail (exit code {!r})".format(exitcode))

    logger.info("*** OK: Test was successful.\n\n\n")
