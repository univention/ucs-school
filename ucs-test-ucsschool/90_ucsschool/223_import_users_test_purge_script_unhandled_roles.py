#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test that the purge script ignores unhandled ucsschool roles
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [55179]

import subprocess
import sys
from datetime import datetime

import pytest

from ucsschool.lib.models.user import User


@pytest.fixture()
def run_purge_script():
    def _run_purge_script():
        cmd = ["/usr/share/ucs-school-import/scripts/ucs-school-purge-expired-users", "-v"]
        sys.stdout.flush()
        sys.stderr.flush()
        exitcode = subprocess.call(cmd)
        return exitcode

    return _run_purge_script


def test_purge_script_ignores_unhandled_roles(
    schoolenv, ucr, udm_session, run_purge_script, lo, create_ou
):
    if ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = ucr.get("hostname")
    school, oudn = schoolenv.create_ou(name_edudc=edudc)
    school_admin, school_admin_dn = schoolenv.create_school_admin(
        school, is_teacher=False, is_staff=False
    )
    user_obj = User.from_dn(school_admin_dn, school, lo)
    user_udm = user_obj.get_udm_object(lo)
    user_udm["ucsschoolPurgeTimestamp"] = datetime.today().strftime("%Y-%m-%d")
    user_udm.modify()
    run_purge_script()
    assert len(lo.search(f"(uid={school_admin})")) > 0
