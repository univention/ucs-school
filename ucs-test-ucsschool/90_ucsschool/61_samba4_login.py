#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Create an user and check the samba login
## roles:
##  - domaincontroller_master
##  - domaincontroller_backup
##  - domaincontroller_slave
## packages:
##  - univention-samba4
## exposure: dangerous
## tags:
##  - ucsschool
##  - apptest

from __future__ import print_function

import subprocess

from ldap.filter import escape_filter_chars

import univention.testing.strings as uts
from univention.testing.ucs_samba import wait_for_drs_replication, wait_for_s4connector


def test_samba4_login(udm_session, ucr):
    password = uts.random_string()

    username = udm_session.create_user(password=password)[1]

    print("Waiting for DRS replication...")
    wait_for_drs_replication("(sAMAccountName=%s)" % (escape_filter_chars(username),), attrs="objectSid")
    wait_for_s4connector()

    subprocess.check_call(
        (
            "/usr/bin/smbclient",
            "-U%s%%%s" % (username, password),
            "//%s/sysvol" % ucr.get("hostname"),
            "-c",
            "ls",
        )
    )
