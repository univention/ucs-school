#!/usr/share/ucs-test/runner python3
## desc: Test the Samba4 GPC objects and links replication from Replica Directory Node to Primary Directory Node OpenLDAP.  # noqa: E501
## bugs: [34214]
## roles: [domaincontroller_slave]
## packages: [univention-samba4, ucs-school-replica]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous

from __future__ import print_function

from re import search
from sys import exit
from time import sleep

import ldap
import workaround

import ucsschool.lib.models
import univention.admin.uexceptions
import univention.testing.utils as utils
from univention.admin.uldap import getMachineConnection
from univention.testing.strings import random_username
from univention.testing.ucsschool.test_samba4 import TestSamba4


class TestGPCReplicationOpenLDAP(TestSamba4):
    def main(self):
        """
        Tests the Samba4 GPC objects (and GPO links) replication from
        Replica Directory Node to Primary Directory Node OpenLDAP.
        """
        try:
            self.get_ucr_test_credentials()
            (self.ldap, _pos) = getMachineConnection(ldap_master=True)

            # Create GPO and check replication against Primary Directory Node:
            gpo_reference = self.create_gpo()
            self.check_gpo_replicated(gpo_reference)

            # Create GPO link to School OU and check replication against Primary Directory Node:
            school_ou_dn = self.find_school_ou()
            self.create_gpo_link(school_ou_dn, gpo_reference)
            self.check_gpo_link_replicated(school_ou_dn, gpo_reference)
        finally:
            if self.gpo_reference:
                sleep(30)  # wait before deleting (for LDAP entries)
                self.delete_samba_gpo()

    def create_gpo(self):
        """
        Using samba-tool creates a GPO.
        """
        display_name = "ucs_test_school_gpo_" + random_username(8)

        print(
            ("\nCreating a Group Policy Object (GPO) with a display name '%s' using 'samba-tool'")
            % display_name
        )

        stdout, stderr = self.samba_tool("gpo", "create", display_name)
        if workaround.filter_deprecated(stderr):
            print(
                ("\nAn error message while creating a GPO using 'samba-tool'. STDERR:\n%s") % (stderr,)
            )
        if not stdout:
            utils.fail(
                (
                    "The 'samba-tool' did not produce any output "
                    "to STDOUT, while a GPO reference was expected"
                )
            )

        stdout = stdout.rstrip()
        print("\nSamba-tool produced the following output:", stdout)

        try:
            # extracting the GPO reference from the stdout:
            return "{" + search("{(.+?)}", stdout).group(1) + "}"
        except AttributeError as exc:
            utils.fail(
                (
                    "Could not find the GPO reference in the STDOUT "
                    "'%s' of the 'samba-tool', error: '%s'"
                )
                % (stdout, exc)
            )

    def samba_tool(self, *args):
        """
        Call `samba-tool` with the given args, while ensuring the proper
        authentication arguments are passed.
        """
        auth_args = ("-k", "no", "--username", self.admin_username, "--password", self.admin_password)
        cmd = ("samba-tool",) + args + auth_args
        return self.create_and_run_process(cmd)

    def check_gpo_replicated(self, gpo_reference):
        """
        Check the Primary Directory Node OpenLDAP for a created GPO object.
        """
        gpo_search = ldap.filter.filter_format("(cn=%s)", (gpo_reference,))
        for _ in range(5):
            try:
                result = self.ldap.search(filter=gpo_search, attr=["cn"], required=True)
            except univention.admin.uexceptions.noObject:
                print("GPO not yet replicated, sleeping..")
                sleep(5)
            else:
                break
        else:
            utils.fail("GPO %s not replicated to Primary Directory Node LDAP" % gpo_reference)
        print("Found the created GPO: %s" % result)

    def find_school_ou(self):
        schools = ucsschool.lib.models.School.get_all(self.ldap)
        if not schools:
            utils.fail("Could not find the a School-OU")
        return schools[0].dn

    def create_gpo_link(self, container_dn, gpo_reference):
        """
        Creates a GPO link to a given 'container_dn' for 'gpo_reference'
         using 'samba-tool'.
        """
        print("\nLinking '%s' container and '%s' GPO using 'samba-tool'" % (container_dn, gpo_reference))

        stdout, stderr = self.samba_tool("gpo", "setlink", container_dn, gpo_reference)
        if workaround.filter_deprecated(stderr):
            print(
                ("\nAn error message while creating a GPO link using " "'samba-tool'. STDERR:\n%s")
                % stderr
            )

        if not stdout:
            utils.fail(
                (
                    "The 'samba-tool' did not produce any output to "
                    "STDOUT, while a GPO link confirmation was expected"
                )
            )
        if container_dn not in stdout:
            utils.fail(
                ("The linked School OU (Container) was not referenced " "in the 'samba-tool' output")
            )
        if self.gpo_reference not in stdout:
            utils.fail("The linked GPO was not referenced in the 'samba-tool' output")

        print("\nSamba-tool produced the following output:\n", stdout)

    def check_gpo_link_replicated(self, container_dn, gpo_reference):
        """
        Check the Primary Directory Node OpenLDAP for a created `msGPOLink` in the given
        `container_dn`.
        """
        for _ in range(5):
            try:
                gp_link = self.ldap.getAttr(container_dn, "msGPOLink", required=True)[0].decode("UTF-8")
            except ldap.NO_SUCH_OBJECT:
                print("GPO Link not yet replicated, sleeping..")
                sleep(5)
            else:
                gpo_dns = self.parse_gp_link_into_dns(gp_link)
                if not any(gpo_reference in dn for dn in gpo_dns):
                    print("GPO Link not yet replicated, sleeping..")
                    sleep(10)
                else:
                    break
        else:
            utils.fail(
                "GPO link %s -> %s not replicated to Primary Directory Node LDAP."
                % (container_dn, gpo_reference)
            )
        print("Found msGPOLink attribute: %s" % gp_link)

    def parse_gp_link_into_dns(self, gp_link):
        """
        Parse a given `gp_link` (`msGPOLink`) attribute into a list of
        referenced GPO-DNs.
        """
        # There seems to be no proper way to do this
        # https://github.com/samba-team/samba/blob/87afc3aee1ea/python/samba/netcmd/gpo.py#L86-L97

        # The first and last chars must be `[` and `]`, so strip them
        links = (g.rsplit(";", 1) for g in gp_link[1:-1].split("]["))
        return [dn[len("LDAP://") :] for (dn, _options) in links]


if __name__ == "__main__":
    TestGPCReplication = TestGPCReplicationOpenLDAP()
    exit(TestGPCReplication.main())
