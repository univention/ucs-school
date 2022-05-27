#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check diagnostic tool 903_ucsschool_schoolcomputers
## tags: [ucsschool, diganostic_test, apptest,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages: []
## bugs: [50500]

from __future__ import absolute_import, print_function

from typing import List  # noqa: F401

import univention.testing.strings as uts
from univention.management.console.modules.diagnostic import Critical, Instance, ProblemFixed
from univention.testing.ucsschool.ucs_test_school import AutoMultiSchoolEnv, NameDnObj, logger


class UCSSchoolSchoolComputers(AutoMultiSchoolEnv):
    def __init__(self):
        super(UCSSchoolSchoolComputers, self).__init__()
        self.client_computers = []

    def create_client_computers(self):  # type: () -> List
        client_computers = [self.schoolA.winclient, self.schoolB.winclient]
        computer_types = ["macos", "ipmanagedclient", "linux", "ubuntu"]
        for suffix in ("A", "B"):
            if suffix == "A":
                school_dn = self.schoolA.dn
            else:
                school_dn = self.schoolB.dn
            for c_type in computer_types:
                client_computers.append(
                    NameDnObj(
                        "school{}{}".format(c_type, suffix),
                        self.udm.create_object(
                            "computers/{}".format(c_type),
                            name="school{}{}".format(c_type, suffix),
                            position="cn=computers,{}".format(school_dn),
                            mac=uts.random_mac(),
                            ip=uts.random_ip(),
                        ),
                    )
                )
        return client_computers

    def mess_up_clients(self):  # type: () -> List
        self.client_computers = self.create_client_computers()
        assert len(self.client_computers) == 10
        computer_dns = []
        num_computers = len(self.client_computers)
        for i, computer in enumerate(self.client_computers):
            self.lo.modify(
                computer.dn,
                [("ucsschoolRole", self.lo.get(computer.dn, ["ucsschoolRole"], required=True), [])],
            )
            if i > num_computers // 2:
                objectClass = self.lo.get(computer.dn, ["objectClass"], required=True)
                if b"ucsschoolComputer" in objectClass["objectClass"]:
                    objectClass["objectClass"].remove(b"ucsschoolComputer")
                    assert b"ucsschoolComputer" not in self.lo.get(computer.dn, ["objectClass"])
                self.lo.modify(
                    computer.dn,
                    [
                        (
                            "objectClass",
                            self.lo.get(computer.dn, ["objectClass"], required=True),
                            objectClass,
                        )
                    ],
                )
            computer_dns.append("{}".format(computer.dn))
        return computer_dns

    def run_all_tests(self):  # type: () -> None
        logger.info("Messed up the client computers.")
        computer_dns = self.mess_up_clients()

        logger.info(
            "Run diagnostic tool, capture and test if warnings were raised. The dns of the client "
            "computers should appear be in the warnings."
        )
        module_name = "903_ucsschool_schoolcomputers"
        instance = Instance()
        instance.init()
        module = instance.get(module_name)
        out = None
        try:
            out = module.execute(None)
        except Critical:
            pass

        assert out and out["success"] is False
        for dn in computer_dns:
            if dn not in out["description"]:
                raise Exception(
                    "diagnostic tool {} did not raise warning for {}!\n".format(module_name, dn)
                )
        logger.info("Ran diagnostic tool {} successfully.".format(module_name))

        try:
            out = module.actions["fix_computers"](None)
        except ProblemFixed:
            assert out["success"] is False
            logger.info("Successfully fixed client computers.")
        except Critical as exc:
            raise Exception("diagnostic tool (fix) {} failed: {}".format(module_name, exc))


def test_diagnostic_module_903():
    with UCSSchoolSchoolComputers() as test_suite:
        test_suite.create_multi_env_school_objects()
        test_suite.run_all_tests()
