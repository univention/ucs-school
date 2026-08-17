#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Activate groupmembers
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-groups,ucs-school-import,ucs-school-singleserver]

from __future__ import print_function

import csv
import itertools
import re
import subprocess

import univention.testing.strings as uts
from univention.lib.umc import Unauthorized
from univention.testing import utils
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client


class UnexpectedAuthenticationSuccess(Exception):
    pass


class UnexpectedUserStatus(Exception):
    pass


def activate_groupmembers(group_name, newStatus, change_passwd):
    # [0|1] optional: deactivate     | activate
    # [0|1] optional: keep passwords | set random passwords
    cmd = [
        "/usr/share/ucs-school-import/scripts/activate_groupmembers",
        group_name,
        newStatus,
        change_passwd,
    ]
    out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    out = out.decode("utf-8")
    print(out, err)
    outfile = re.search(r"outfile\sis\s:\s([^\n]+)", out)
    if outfile:
        return outfile.group(1)


def get_new_password(outfile, lastname):
    with open(outfile) as fi:
        for line in fi:
            if lastname in line:
                found = re.search(r"%s\t(\S+)" % lastname, line)
                if found:
                    return found.group(1)


def check_usernames_in_csv(outfile, usernames):
    """Check if all given usernames are found in specified CSV file. Bug #31187"""
    found_usernames = set()
    csvreader = csv.reader(open(outfile), dialect=csv.Dialect.delimiter, delimiter="\t")
    for row in csvreader:
        found_usernames.add(row[2])  # row 2 is username
    if not set(usernames).issubset(found_usernames):
        utils.fail(
            "Not all usernames found in CSV files - missing usernames: "
            + str(set(usernames) - found_usernames)
        )


def check_auth(username, passwd, should_pass=True):
    try:
        Client(None, username, passwd)
    except Unauthorized:
        if should_pass:
            raise
    else:
        if not should_pass:
            raise UnexpectedAuthenticationSuccess("Authentication succeeded while it should not")


def is_active(username):
    cmd = ["udm", "users/user", "list", "--filter", "uid=%s" % username]
    out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    out = out.decode("utf-8")
    found = re.search(r"disabled:\s(\d+)", out)
    if found:
        found = found.group(1)
        print("disabled = ", found)
        return found == "0"


def checK_status(username, should_pass):
    is_user_active = is_active(username)
    if should_pass != is_user_active:
        raise UnexpectedUserStatus(
            "UDM user status does not match expected value: "
            f"user.disabled={not is_user_active}  expected={not should_pass}"
        )


def test_activate_groupmembers(schoolenv, ucr):
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))

    tea_lastname = uts.random_name()
    tea_staff_lastname = uts.random_name()
    stu_lastname = uts.random_name()
    staff_lastname = uts.random_name()
    school_admin_lastname = uts.random_name()

    tea, tea_dn = schoolenv.create_user(school, is_teacher=True, lastname=tea_lastname)
    tea_staff, tea_staff_dn = schoolenv.create_user(
        school, is_teacher=True, is_staff=True, lastname=tea_staff_lastname
    )
    staff, staff_dn = schoolenv.create_user(school, is_staff=True, lastname=staff_lastname)
    stu, stu_dn = schoolenv.create_user(school, lastname=stu_lastname)
    school_admin, school_admin_dn = schoolenv.create_school_admin(school, lastname=school_admin_lastname)

    users_dn = [tea_dn, tea_staff_dn, staff_dn, stu_dn, school_admin_dn]
    users = [tea, tea_staff, staff, stu, school_admin]
    lastnames = [
        tea_lastname,
        tea_staff_lastname,
        staff_lastname,
        stu_lastname,
        school_admin_lastname,
    ]

    group = Workgroup(school=school, members=users_dn)
    account = utils.UCSTestDomainAdminCredentials()
    passwd = account.bindpw
    group.create()
    utils.wait_for_s4connector_replication()

    for change_passwd, newStatus in itertools.product(["0", "1"], ["0", "1"]):
        should_pass = newStatus == "1"

        print("Test case = active: %s, change_passwd: %s" % (newStatus, change_passwd))
        outfile = activate_groupmembers("%s-%s" % (school, group.name), newStatus, change_passwd)

        # Let the S4 connector finish the round trip of this test case before checking and
        # before the next case changes the same users again. The connector reads its own
        # UCS -> AD writes back afterwards, and the next case is only two seconds away, so
        # without this wait it applies the previous status on top of the new one. That is
        # permanent - no later change resets it - and the retries below cannot heal it:
        # Install Singleserver #646 lost the deactivation of the school admin this way.
        utils.wait_for_replication()
        utils.wait_for_s4connector_replication()

        def test_func(username, should_pass, passwd):
            checK_status(username, should_pass)
            check_auth(username, passwd, should_pass)

        for username, lastname in zip(users, lastnames):
            if change_passwd == "1":
                passwd = get_new_password(outfile, lastname)
            utils.retry_on_error(
                lambda: test_func(username, should_pass, passwd),
                exceptions=(UnexpectedUserStatus, UnexpectedAuthenticationSuccess, Unauthorized),
                retry_count=30,
                delay=2,
            )

        check_usernames_in_csv(outfile, users)
