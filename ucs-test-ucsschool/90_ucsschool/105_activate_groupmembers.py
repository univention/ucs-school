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
            utils.fail("Authentication succeeded while it should not")


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
    return should_pass == is_active(username)


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
    for change_passwd, newStatus in itertools.product(["0", "1"], ["0", "1"]):
        should_pass = newStatus == "1"

        print("Test case = active: %s, change_passwd: %s" % (newStatus, change_passwd))
        outfile = activate_groupmembers("%s-%s" % (school, group.name), newStatus, change_passwd)
        utils.wait_for_replication_and_postrun()

        for username, lastname in zip(users, lastnames):
            checK_status(username, should_pass)
            if change_passwd == "1":
                passwd = get_new_password(outfile, lastname)
            check_auth(username, passwd, should_pass)

        check_usernames_in_csv(outfile, users)
