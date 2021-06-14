#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: smbstatus parser
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [univention-samba4]

from __future__ import print_function

import socket
import subprocess
import time

import univention.testing.utils as utils
from ucsschool.lib.smbstatus import SMB_Status


def test_smbstatus_parser(ucr):
        account = utils.UCSTestDomainAdminCredentials()
        admin = account.username
        passwd = account.bindpw
        host = ucr.get("hostname")

        # build up smb connections
        pop1 = subprocess.Popen(
            ["smbclient", "-U", "%s%%%s" % (admin, passwd), "//%s/netlogon" % host],
            stdin=subprocess.PIPE,
            shell=False,
        )
        pop2 = subprocess.Popen(
            ["smbclient", "-U", "%s%%%s" % (admin, passwd), "//%s/sysvol" % host],
            stdin=subprocess.PIPE,
            shell=False,
        )
        pop3 = subprocess.Popen(
            ["smbclient", "-U", "%s%%%s" % (admin, passwd), "//%s/IPC$" % host],
            stdin=subprocess.PIPE,
            shell=False,
        )

        # wait for the connections to establish
        time.sleep(10)

        status = SMB_Status()
        print("smbstatus = ", status)
        assert status, "smbclient was not able to open any connection to host (%s)" % host

        def get_proccess_by_services(services):
            for process in status:
                if set(process.services) == set(services):
                    return process

        ipaddress = get_ipaddress()
        expected_process_values = [
            {"services": ["netlogon"]},
            {"services": ["sysvol"]},
            {"services": ["IPC$"]},
        ]
        for expected_values in expected_process_values:
            expected_values.update({"username": admin, "ipaddress": ipaddress})
            process = get_proccess_by_services(expected_values["services"])
            assert process, "The process with services %s was not recognized by smbstatus" % (expected_values["services"],)
            check_attributes(process, expected_values)
        pop1.terminate()
        pop2.terminate()
        pop3.terminate()


def get_ipaddress():
    return socket.gethostbyname(socket.gethostname())


def check_attributes(process, expected_values):
    _attrs = [
        "pid",
        "username",
        "group",
        "machine",
        "services",
        "ipaddress",
    ]
    for attr in _attrs:
        try:
            value = getattr(process, attr)
        except AttributeError:
            value = process.get(attr)
            assert value, "Could not fetch the attribute %s" % (attr,)
        if attr in expected_values:
            if attr == "ipaddress":
                value = value.rsplit(":", 1)[0]
            assert value == expected_values[attr], "Attribute (%s) is parsed wrong as (%s), expected in (%r)" % (attr, value, expected_values[attr])
