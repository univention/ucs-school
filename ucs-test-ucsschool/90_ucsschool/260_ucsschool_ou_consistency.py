#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Check ucsschool ou consistency diagnostic tool
## roles: [domaincontroller_master]
## tags: [ucsschool,diagnostic_test,apptest,ucsschool_base1]
## exposure: dangerous
## packages: []
## bugs: [50500]

from __future__ import absolute_import, print_function

from univention.management.console.modules.diagnostic import Critical, Instance
from univention.testing.ucsschool.ucs_test_school import AutoMultiSchoolEnv, logger

MODULE_NAME = "902_ucsschool_ou_consistency"


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
        expected_warnings.append("ucsschoolRole is not set")
        correct_role = self.lo.get(ou_b_dn, ["ucsschoolRole"], required=True)
        self.lo.modify(
            ou_b_dn,
            [
                (
                    "ucsschoolRole",
                    correct_role,
                    [b"non-existent"],
                )
            ],
        )
        expected_warnings.append('ucsschoolRole "school:school:schoolB" not found')

        self.lo.modify(
            ou_a_dn, [("displayName", self.lo.get(ou_a_dn, ["displayName"], required=True), [])]
        )
        expected_warnings.append("displayName is not set")

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
        expected_warnings.append("ucsschoolHomeShareFileServer is not set")
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
        expected_warnings.append("ucsschoolClassShareFileServer is not set")

        if not self.ucr.is_true("ucsschool/singlemaster", False):
            for attr in ("ucsschoolHomeShareFileServer", "ucsschoolClassShareFileServer"):
                self.lo.modify(
                    ou_c_dn,
                    [
                        (
                            attr,
                            self.lo.get(ou_c_dn, [attr]),
                            [self.ucr.get("ldap/hostdn").encode("UTF-8")],
                        )
                    ],
                )
                expected_warnings.append(
                    "{} is set to Primary Directory Node "
                    "in a UCS@school multi server environment".format(attr)
                )
        else:
            for attr in ("ucsschoolHomeShareFileServer", "ucsschoolClassShareFileServer"):
                self.lo.modify(
                    ou_c_dn,
                    [
                        (
                            attr,
                            self.lo.get(ou_c_dn, [attr], required=True),
                            [self.schoolB.winclient.dn.encode("UTF-8")],
                        )
                    ],
                )
                expected_warnings.append(
                    "{} is not set to Primary Directory Node in a UCS@school "
                    "single server environment".format(attr)
                )

        logger.info(
            "Run diagnostic tool {}, capture the stderr and test"
            " if the expected warnings were raised.".format(MODULE_NAME)
        )
        instance = Instance()
        instance.init()
        module = instance.get(MODULE_NAME)
        out = None
        try:
            out = module.execute(None)
        except Critical:
            pass

        assert out and out["success"] is False
        for warning in expected_warnings:
            if warning not in out["description"]:
                raise Exception(
                    "diagnostic tool {} did not raise warning {}!\n".format(MODULE_NAME, warning)
                )
        logger.info("Ran diagnostic tool {} successfully.".format(MODULE_NAME))


def test_ou_consistency():
    with UCSSchoolOuConsistencyCheck() as test_suite:
        test_suite.create_multi_env_school_objects()
        test_suite.run_all_tests()
