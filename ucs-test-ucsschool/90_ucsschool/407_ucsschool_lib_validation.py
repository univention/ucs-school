#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: test general validation funcitonality
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python-ucsschool-lib

import os
import pwd
import subprocess
import sys
import tempfile

import pytest

TEST_MODULE = """
import os
import univention.admin.uldap
from ucsschool.lib.models.user import Student
lo = univention.admin.uldap.access(
    host="{hostname}",
    base="{ldap_base}",
    binddn="{binddn}",
    bindpw="{bindpw}"
)
print(lo.searchDn("{filter_s}"))
print(Student.from_dn("{dn}", None, lo))
"""


@pytest.fixture(scope="session")
def python_module_that_reads_a_student_from_ldap(machine_account_dn, machine_password, ucr):
    paths = []

    def _func(dn):  # type: (str) -> str
        fd, path = tempfile.mkstemp()
        os.write(
            fd,
            TEST_MODULE.format(
                dn=dn,
                filter_s=dn.split(",", 1)[0],
                hostname=ucr["hostname"],
                ldap_base=ucr["ldap/base"],
                binddn=machine_account_dn,
                bindpw=machine_password,
            ).encode("UTF-8"),
        )
        os.close(fd)
        print("Wrote test Python module to {!r}.".format(path))
        paths.append(path)
        return path

    yield _func

    for path in paths:
        try:
            os.unlink(path)
            pass
        except EnvironmentError:
            pass


def test_python_process_uid_zero(python_module_that_reads_a_student_from_ldap, schoolenv):
    assert os.getuid() == 0, "Test must be run as root."
    school, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    user_name, user_dn = schoolenv.create_student(ou_name=school)
    path = python_module_that_reads_a_student_from_ldap(user_dn)
    subprocess.check_call([sys.executable, path], stderr=sys.stderr, stdout=sys.stdout)


def test_python_process_uid_non_zero(python_module_that_reads_a_student_from_ldap, schoolenv):
    assert os.getuid() == 0, "Test must be run as root."
    school, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    user_name, user_dn = schoolenv.create_student(ou_name=school)
    path = python_module_that_reads_a_student_from_ldap(user_dn)
    uid = pwd.getpwnam(user_name).pw_uid
    os.chmod(path, 0o644)
    try:
        os.seteuid(uid)
        assert os.geteuid() == uid
        subprocess.check_call([sys.executable, path], stderr=sys.stderr, stdout=sys.stdout)
    finally:
        os.seteuid(0)
