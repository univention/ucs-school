#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: Test the Samba4 GPO link replication between DC-Slaves.
## bugs: [45992]
## roles: [domaincontroller_slave]
## packages: [univention-samba4]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous

from __future__ import print_function

from re import search
from subprocess import check_call, check_output

import univention.testing.ucr as ucr_test
import univention.testing.utils as utils


class GPO(object):
    def __init__(self, dn_school):
        self.dn_school = dn_school
        self.ucr = ucr_test.UCSTestConfigRegistry()
        self.ucr.load()
        self.account = utils.UCSTestDomainAdminCredentials()
        self.display_name = "UCSTEST_91c_samba4_gpo_link_replication"
        self._create_gpo()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        check_call(
            [
                "samba-tool",
                "gpo",
                "del",
                self.gpo_reference,
                "--username={}".format(self.account.username),
                "--password={}".format(self.account.bindpw),
            ]
        )

    def _create_gpo(self):
        stdout = check_output(
            [
                "samba-tool",
                "gpo",
                "create",
                self.display_name,
                "--username={}".format(self.account.username),
                "--password={}".format(self.account.bindpw),
            ]
        )
        stdout = stdout.decode("UTF-8").rstrip()
        print("\nSamba-tool produced the following output:", stdout)

        try:
            # extracting the GPO reference from the stdout:
            self.gpo_reference = "{" + search("{(.+?)}", stdout).group(1) + "}"
        except AttributeError as exc:
            utils.fail(
                "Could not find the GPO reference in the STDOUT '%s' of the 'samba-tool', error: '%s'"
                % (stdout, exc)
            )
        utils.wait_for_replication_and_postrun()

    def set_gpo_link_on_slave_via_s4connector(self):
        check_call(
            [
                "/usr/share/univention-s4-connector/msgpo.py",
                "--write2ucs",
                "--binddn",
                self.account.binddn,
                "--bindpwd",
                self.account.bindpw,
            ]
        )
        utils.wait_for_replication_and_postrun()

    def set_gpo_link_on_slave_via_sambatool(self):
        # It should not be possible to set GPO links for other OUs
        check_call(
            [
                "samba-tool",
                "gpo",
                "setlink",
                self.dn_school,
                self.gpo_reference,
                "--username={}".format(self.account.username),
                "--password={}".format(self.account.bindpw),
            ]
        )
        utils.wait_for_replication_and_postrun()


def check_local_LDAP_for_GPO_link(gpo_reference, oudn):
    stdout = check_output(["univention-ldapsearch", oudn.split(",", 1)[0]])
    stdout = stdout.decode("UTF-8")
    print(stdout)
    return gpo_reference.lower() in stdout.lower()


def test_samba4_gpo_link_replication(schoolenv):
    # create new OU the current DC slave is NOT resposible for
    schoolName, oudn = schoolenv.create_ou(use_cache=False)
    utils.wait_for_replication_and_postrun()
    # create a new GPO
    with GPO(oudn) as gpo:
        # connect the GPO to the new OU (oudn) via samba-tool in local S4
        # due to LDAP ACLs, the local S4 connector should not be able to
        # replicate the gPOlink to the UCS master.
        gpo.set_gpo_link_on_slave_via_sambatool()
        # the local LDAP contains the GPO link at oudn but should not:
        assert not check_local_LDAP_for_GPO_link(
            gpo.gpo_reference, oudn
        ), "A school DC can set GPO links for another OU"
        gpo.set_gpo_link_on_slave_via_s4connector()
        # the local LDAP should contains the GPO link at oudn:
        assert check_local_LDAP_for_GPO_link(
            gpo.gpo_reference, oudn
        ), "A school DC cannot read GPO links from other OUs"
