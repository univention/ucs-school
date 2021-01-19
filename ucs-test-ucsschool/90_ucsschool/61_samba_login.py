#!/usr/share/ucs-test/runner python3
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

import univention.config_registry as config_registry
import univention.testing.strings as uts
import univention.testing.udm as udm_test


class SambaLoginFailed(Exception):
    pass


if __name__ == "__main__":
    ucr = config_registry.ConfigRegistry()
    ucr.load()

    with udm_test.UCSTestUDM() as udm:
        username = uts.random_username()
        password = uts.random_string()

        user = udm.create_user(username=username, password=password)

        cmd = (
            "/usr/bin/smbclient",
            "-U%s%%%s" % (username, password),
            "//%s/netlogon" % ucr.get("hostname"),
            "-c",
            "ls",
        )
        retcode = subprocess.call(cmd, shell=False)
        if retcode:
            raise SambaLoginFailed()
