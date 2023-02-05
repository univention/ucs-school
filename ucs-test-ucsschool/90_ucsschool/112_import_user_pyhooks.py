#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test modifications on user objects by python import hooks
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41572]
import os
import os.path
import shutil
import sys

import pytest

import univention.testing.strings as uts
from ucsschool.importer.utils.shell import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
    logger,
)

TESTHOOKSOURCE = CONFIG = os.path.join(os.path.dirname(__file__), "testpyhookpy")
TESTHOOKTARGET = "/usr/share/ucs-school-import/pyhooks/bdaytest.py"

logger.info("*** Copying %r to %r...", TESTHOOKSOURCE, TESTHOOKTARGET)
shutil.copy2(TESTHOOKSOURCE, TESTHOOKTARGET)
sys.path.append("/usr/share/ucs-school-import/pyhooks/")
from bdaytest import BIRTHDAYS, PRE_ACTION_BIRTHDAYS  # noqa: E402


@pytest.fixture
def cleanup_ext():
    yield
    for ext in ["", "c", "o"]:
        try:
            os.remove("{}{}".format(TESTHOOKTARGET, ext))
            logger.info("*** Deleted %s%s...", TESTHOOKTARGET, ext)
        except OSError:
            logger.warning("*** Could not delete %s%s.", TESTHOOKTARGET, ext)


def test_import_user_pyhooks(cleanup_ext, ucr, schoolenv):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(
        2, name_edudc=ucr.get("hostname")
    )
    lo = schoolenv.open_ldap_connection(admin=True)
    for kls in [ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff]:
        username = uts.random_username()
        kwargs = {
            "school": ou_name,
            "schools": [ou_name],
            "name": username,
            "firstname": uts.random_name(),
            "lastname": uts.random_name(),
            "school_classes": {},
            "record_uid": uts.random_name(),
        }
        logger.info("*** Creating %r in %r...", kls.__name__, ou_name)
        kwargs["birthday"] = PRE_ACTION_BIRTHDAYS["pre_create"]
        user = kls(**kwargs)
        user.prepare_all(True)
        user.create(lo)
        user = kls.get_all(lo, ou_name, "uid={}".format(username))[0]
        assert user.birthday == BIRTHDAYS["post_create"]

        logger.info("*** Modifying %r...", kls.__name__)
        user.birthday = PRE_ACTION_BIRTHDAYS["pre_modify"]
        user.modify(lo)
        user = kls.from_dn(user.dn, ou_name, lo)
        assert user.birthday == BIRTHDAYS["post_modify"]

        logger.info("*** Moving %r to %r...", kls.__name__, ou_name2)
        user.birthday = PRE_ACTION_BIRTHDAYS["pre_move"]
        user.change_school(ou_name2, lo)
        user = kls.from_dn(user.dn, ou_name2, lo)
        assert user.birthday == BIRTHDAYS["post_move"]

        logger.info("*** Deleting %r...", kls.__name__)
        user.birthday = PRE_ACTION_BIRTHDAYS["pre_remove"]
        user.remove(lo)
