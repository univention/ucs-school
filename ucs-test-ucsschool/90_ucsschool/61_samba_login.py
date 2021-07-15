#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Create an user and check the samba4 login
## roles:
##  - domaincontroller_master
##  - domaincontroller_backup
##  - domaincontroller_slave
## packages:
##  - univention-samba
## exposure: dangerous
## tags:
##  - ucsschool
##  - apptest

import subprocess

import univention.testing.strings as uts


def test_samba_login(ucr, udm):
        password = uts.random_string()

        username = udm.create_user(password=password)[0]

        subprocess.check_call((
            "/usr/bin/smbclient",
            "-U%s%%%s" % (username, password),
            "//%s/netlogon" % ucr.get("hostname"),
            "-c",
            "ls",
        ))
