#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: check if staff users can optionally be replicated to edu Replica Directory Nodes
## roles: [domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## timeout: 3600
## exposure: dangerous
## packages: [ucs-school-replica]
## bugs: [50274]


from __future__ import absolute_import, print_function

import subprocess
from typing import Tuple

import univention.admin.uldap as udm_uldap
import univention.testing.utils as utils
from univention.testing.ucsschool.ucs_test_school import NameDnObj, UCSTestSchool, logger


class LDAPACLCheck(UCSTestSchool):
    def __init__(self, *args, **kwargs):
        super(LDAPACLCheck, self).__init__(*args, **kwargs)
        account = utils.UCSTestDomainAdminCredentials()
        self.admin_username = account.username
        self.admin_password = account.bindpw
        self.ldap_upstream_servers = [self.ucr.get("ldap/master")] + self.ucr.get(
            "ldap/backup", ""
        ).split()

    def setup(self):  # type: () -> None
        self.school = NameDnObj()
        self.school.name, self.school.dn = self.create_ou(name_edudc=self.ucr.get("hostname"))
        self.teacher_user = NameDnObj(*self.create_user(self.school.name, is_teacher=True))
        logger.debug("TEACHER DN: %s", self.teacher_user.dn)
        logger.debug("TEACHER NAME: %s", self.teacher_user.name)
        self.staff_user = NameDnObj()

    def run_on_ldap_upstream_servers(self, command_line):  # type: (str) -> Tuple[str, str]
        ucr_value = None
        for ldap_upstream_server in self.ldap_upstream_servers:
            cmd = (
                "univention-ssh",
                "-timeout",
                "120",
                "/dev/stdin",
                "root@{}".format(ldap_upstream_server),
                command_line,
            )
            logger.info("CMD: %s", " ".join(cmd))
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate(self.admin_password.encode("UTF-8"))
            logger.debug("STDOUT:\n%s", stdout)
            logger.debug("STDERR:\n%s", stderr)
            if ldap_upstream_server == self.ucr.get("ldap/master"):
                ucr_value = stdout.strip()
        return ucr_value

    def run_test(self):  # type: () -> None
        # ssh to Primary Directory Node ==> get UCR + set to OFF
        old_value = self.run_on_ldap_upstream_servers(
            "/usr/sbin/ucr get ucsschool/ldap/replicate_staff_to_edu"
        )

        try:
            # HINT:
            # the case ucsschool/ldap/replicate_staff_to_edu=no is not tested, because this is currently
            # the default case and it is difficult to test e.g. via verify_ldap_object() since it does
            # not use the machine account

            # ssh to Primary Directory Node ==> set UCRV to ON and create Staff2 in test OU
            self.run_on_ldap_upstream_servers(
                "/usr/sbin/ucr set ucsschool/ldap/replicate_staff_to_edu=yes ; "
                "/usr/sbin/ucr commit /etc/ldap/slapd.conf ; "
                "/usr/sbin/service slapd restart"
            )

            # create Staff in test OU
            # check if staff is locally available
            self.staff_user = NameDnObj(*self.create_user(self.school.name, is_staff=True))

            # test with Administrator account
            utils.verify_ldap_object(
                self.staff_user.dn,
                {"uid": [self.staff_user.name]},
                should_exist=True,
                retry_count=10,
                delay=3,
            )

            # test with teacher account
            lo = udm_uldap.access(
                host=self.ucr.get("ldap/server/name"),
                port=7389,
                base=self.ucr.get("ldap/base"),
                binddn=self.teacher_user.dn,
                bindpw="univention",
                start_tls=2,
            )
            assert lo.search(
                base=self.staff_user.dn, scope="base"
            ), "teacher is unable to find staff user"

            # test with machine account
            lo = self.open_ldap_connection(machine=True, ldap_server=self.ucr.get("ldap/server/name"))
            assert lo.search(
                base=self.staff_user.dn, scope="base"
            ), "machine account is unable to find staff user"
        finally:
            cmd_list = [
                "/usr/sbin/ucr set ucsschool/ldap/replicate_staff_to_edu={}".format(old_value),
                "/usr/sbin/ucr commit /etc/ldap/slapd.conf",
                "/usr/sbin/service slapd restart",
            ]
            if not old_value:
                cmd_list[0] = "/usr/sbin/ucr unset ucsschool/ldap/replicate_staff_to_edu"
            self.run_on_ldap_upstream_servers(" ; ".join(cmd_list))


def test_ldap_acls_staff_on_edu_servers():
    with LDAPACLCheck() as test_suite:
        test_suite.setup()
        test_suite.run_test()
