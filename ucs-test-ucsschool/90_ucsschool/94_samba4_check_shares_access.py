#!/usr/share/ucs-test/runner python3
## desc: Test the Locator Primary Directory Node shares access from Replica Directory Node.
## bugs: [34224, 37977]
## roles:
## - domaincontroller_slave
## packages: [univention-samba4]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: careful

from __future__ import print_function

from sys import exit

from dns import resolver
from ldap.filter import escape_filter_chars

import univention.testing.utils as utils
from univention.testing.strings import random_username
from univention.testing.ucs_samba import wait_for_drs_replication, wait_for_s4connector
from univention.testing.ucsschool.test_samba4 import TestSamba4
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool


class TestS4DCLocatorSharesAccess(TestSamba4):
    def __init__(self):
        """Test class constructor."""
        super(TestS4DCLocatorSharesAccess, self).__init__()
        self.TestSchool = UCSTestSchool()

    def connect_to_master_sysvol_share(self, username, password, use_kerberos=False):
        """
        Using 'smbclient' and given credentials executes the 'cmd' to list
        the sysvol contents on the Primary Directory Node. Tries to use Kerberos if
        respective kwarg 'use_kerberos'==True.
        """
        domain_name = self.UCR.get("domainname")
        ldap_master = self.UCR.get("ldap/master")

        if use_kerberos:
            cmd = (
                "smbclient",
                "//" + ldap_master + "/sysvol",
                "--user=" + username + "%" + password,
                "--timeout=120",
                "--workgroup=" + domain_name.upper(),
                "--command=ls",
            )
            print("\nKerberos authentication will be used:")
            cmd = cmd + ("-k",)
        else:
            ldap_master_ip = resolver.query(ldap_master)[0].address
            cmd = (
                "smbclient",
                "//" + ldap_master_ip + "/sysvol",
                "--user=" + username + "%" + password,
                "--timeout=120",
                "--workgroup=" + domain_name.upper(),
                "--command=ls",
            )

        print(
            "\nTrying to connect to Sysvol on Primary Directory Node and list the contents using Samba "
            "client:"
        )
        print(cmd)

        stdout, stderr = self.create_and_run_process(cmd)
        if stderr:
            print("\nThe Samba client produced the following output to STDERR:\n%s" % stderr)

        if not stdout.strip():
            utils.fail(
                "The Samba client did not produce any output to STDOUT, while Primary Directory Node "
                "Sysvol contents were expected"
            )
        print("The Samba client produced the following output to STDOUT:\n%s" % stdout)

        connection_errors = ("NT_STATUS_CONNECTION_REFUSED", "failed", "Error")
        if any(err_string in stdout for err_string in connection_errors):
            utils.fail("\nThe connection with Primary Directory Node failed. See the stdout.")
        if domain_name not in stdout:
            utils.fail(
                "The Samba client output of Primary Directory Node Sysvol contents does not include "
                "folder with the domain name."
            )

    def create_student(self):
        """Creates a student and returns username, dn and password used."""
        student_name = "ucs_test_school_user_" + random_username(8)
        student_password = "Foo3" + random_username(8)

        print(
            "\nCreating a student for the test with a name '%s' and a password '%s'"
            % (student_name, student_password)
        )

        student_dn = self.TestSchool.create_user(
            self.select_school_ou(True), username=student_name, password=student_password
        )[1]

        wait_for_drs_replication(
            "(sAMAccountName=%s)" % escape_filter_chars(student_name), attrs="objectSid"
        )
        wait_for_s4connector()
        return student_name, student_dn, student_password

    def main(self):
        """
        Creates a user and tries to list the Primary Directory Node Sysvol using smbclient.
        (First with NTLM and after with Kerberos).
        """
        self.get_ucr_test_credentials()

        # skip the test if Primary Directory Node has no S4:
        if not self.dc_master_has_samba4():
            print("\nThe Primary Directory Node has no S4, skipping test...")
            self.return_code_result_skip()

        try:
            student_dn = ""
            student_name, student_dn, student_password = self.create_student()

            self.connect_to_master_sysvol_share(student_name, student_password)
            # Kerberos case disabled, as will work only for local DC share
            # Probably, due to Bug #31919:
            # self.connect_to_master_sysvol_share(student_name, student_password, True)
        finally:
            if student_dn:
                print("\nRemoving the test student user '%s':" % student_name)
                self.TestSchool._remove_udm_object("users/user", student_dn)


if __name__ == "__main__":
    TestDCLocatorShares = TestS4DCLocatorSharesAccess()
    exit(TestDCLocatorShares.main())
