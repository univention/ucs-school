#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Check ucschool ou consistency diagnostic tool
## roles: [domaincontroller_master]
## tags: [ucsschool,diagnostic_test]
## exposure: dangerous
## packages: []
## bugs: [50500]

from __future__ import absolute_import, print_function

from univention.management.console.modules.diagnostic import Critical, Instance
from univention.testing.ucsschool.ucs_test_school import AutoMultiSchoolEnv, logger


class UCSSchoolOuConsistencyCheck(AutoMultiSchoolEnv):
    def run_all_tests(self):  # type: () -> None

        ou_list = self.lo.search(
            filter="ou={}".format(self.schoolA.name), base=self.ucr.get("ldap/base"), scope="one"
        )
        ou_a_dn, ou_a_attrs = ou_list[0]
        ou_list = self.lo.search(
            filter="ou={}".format(self.schoolB.name), base=self.ucr.get("ldap/base"), scope="one"
        )
        ou_b_dn, ou_b_attrs = ou_list[0]
        ou_list = self.lo.search(
            filter="ou={}".format(self.schoolC.name), base=self.ucr.get("ldap/base"), scope="one"
        )
        ou_c_dn, ou_c_attrs = ou_list[0]
        assert b"ucsschoolOrganizationalUnit" in ou_a_attrs.get("objectClass", [])
        assert b"ucsschoolOrganizationalUnit" in ou_b_attrs.get("objectClass", [])
        assert b"ucsschoolOrganizationalUnit" in ou_c_attrs.get("objectClass", [])

        logger.info("Change ldap-values of A-C, such that the diagnostic tool should raise a warning.")
        expected_warnings = []
        self.lo.modify(
            ou_a_dn, [("ucsschoolRole", self.lo.get(ou_a_dn, ["ucsschoolRole"], required=True), [])]
        )
        expected_warnings.append("ucsschoolRole is not set\n")
        self.lo.modify(
            ou_b_dn,
            [
                (
                    "ucsschoolRole",
                    self.lo.get(ou_b_dn, ["ucsschoolRole"], required=True),
                    ["non-existent"],
                )
            ],
        )
        expected_warnings.append('ucsschoolRole "school:school:non-existent" not found\n')

        self.lo.modify(
            ou_a_dn, [("displayName", self.lo.get(ou_a_dn, ["displayName"], required=True), [])]
        )
        expected_warnings.append("displayName is not set\n")

        self.lo.modify(
            ou_a_dn,
            [
                (
                    "ucsschoolHomeShareFileServer",
                    self.lo.get(ou_a_dn, ["ucsschoolHomeShareFileServer"], required=True),
                    [],
                )
            ],
        )
        expected_warnings.append("ucsschoolHomeShareFileServer is not set\n")
        self.lo.modify(
            ou_a_dn,
            [
                (
                    "ucsschoolClassShareFileServer",
                    self.lo.get(ou_a_dn, ["ucsschoolClassShareFileServer"], required=True),
                    [],
                )
            ],
        )
        expected_warnings.append("ucsschoolClassShareFileServer is not set\n")

        if not self.ucr.is_true("ucsschool/singlemaster", False):
            self.lo.modify(
                ou_c_dn,
                [
                    (
                        "ucsschoolHomeShareFileServer",
                        self.lo.get(ou_c_dn, ["ucsschoolHomeShareFileServer"]),
                        [self.ucr.get("ldap/hostdn")],
                    )
                ],
            )
            expected_warnings.append(
                "ucsschoolHomeShareFileServer is set to Primary Directory Node in a UCS@school multi "
                "server environment\n"
            )
            self.lo.modify(
                ou_c_dn,
                [
                    (
                        "ucsschoolClassShareFileServer",
                        self.lo.get(ou_c_dn, ["ucsschoolClassShareFileServer"]),
                        [self.ucr.get("ldap/hostdn")],
                    )
                ],
            )
            expected_warnings.append(
                "ucsschoolClassShareFileServer is set to Primary Directory Node in a UCS@school multi "
                "server environment\n"
            )
        else:
            self.lo.modify(
                ou_b_dn,
                [
                    (
                        "ucsschoolHomeShareFileServer",
                        self.lo.get(ou_b_dn, ["ucsschoolHomeShareFileServer"], required=True),
                        [self.schoolB.winclient.dn],
                    )
                ],
            )
            expected_warnings.append(
                "ucsschoolHomeShareFileServer is not set to Primary Directory Node in a UCS@school "
                "single server environment\n"
            )
            self.lo.modify(
                ou_b_dn,
                [
                    (
                        "ucsschoolClassShareFileServer",
                        self.lo.get(ou_b_dn, ["ucsschoolClassShareFileServer"], required=True),
                        [self.schoolB.winclient.dn],
                    )
                ],
            )
            expected_warnings.append(
                "ucsschoolClassShareFileServer is not set to Primary Directory Node in a UCS@school "
                "single server environment\n"
            )

        logger.info(
            "Run diagnostic tool, capture the stderr and test if the expected warnings were raised."
        )
        module_name = "902_ucsschool_ou_consistency"
        instance = Instance()
        instance.init()
        module = instance.get(module_name)
        out = None
        try:
            out = module.execute(None)
        except Critical:
            pass

        assert out and out["success"] is False
        for warning in expected_warnings:
            if warning not in out["description"]:
                raise Exception(
                    "diagnostic tool {} did not raise warning {}!\n".format(module_name, warning)
                )
        logger.info("Ran diagnostic tool {} successfully.".format(module_name))


def test_ou_consistency():
    with UCSSchoolOuConsistencyCheck() as test_suite:
        test_suite.create_multi_env_school_objects()
        test_suite.run_all_tests()
