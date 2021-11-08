#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check diagnostic tool 904_ucsschool_remove_from_school_consistenceny
## tags: [ucsschool, diagnostic_test]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages: [ucs-school-import]
## bugs: [50795]

from __future__ import absolute_import, print_function

from ldap.filter import filter_format

from univention.management.console.modules.diagnostic import Instance
from univention.testing.ucsschool.ucs_test_school import AutoMultiSchoolEnv, logger


class UCSSchoolSchoolConsistency(AutoMultiSchoolEnv):
    def __init__(self):
        super(UCSSchoolSchoolConsistency, self).__init__()
        self.client_computers = []

    def get_diagnostic_module(self):  # type: () -> Instance
        logger.info("Run diagnostic tool, capture and test if warnings were raised.")
        module_name = "904_ucsschool_remove_from_school_consistenceny"
        instance = Instance()
        instance.init()
        module = instance.get(module_name)
        return module

    def run_all_tests(self):  # type: () -> None
        module = self.get_diagnostic_module()
        logger.info("*** Perform test run with correct LDAP state")
        out = module.execute(None)
        assert out and (out["success"] is True), "unexpected result from test: out={!r}".format(out)

        class_name = "{}-class1".format(self.schoolC.name)
        filter_str = filter_format("(&(univentionObjectType=groups/group)(cn=%s))", (class_name,))
        class_dn = self.lo.searchDn(filter=filter_str)[0]
        for user in (self.schoolA.teacher, self.schoolA.student):
            logger.info("*** Add {} to group {}".format(user.dn, class_dn))
            self.lo.modify(class_dn, [["uniqueMember", None, user.dn.encode("UTF-8")], ["memberUid", None, user.name.encode("UTF-8")]])

        try:
            module = self.get_diagnostic_module()
            logger.info("*** Perform test run with broken group memberships")
            out = module.execute(None)
            assert (
                out and (out["success"] is False) and (out["type"] == "warning")
            ), "unexpected result from test: out={!r}".format(out)
            logger.info(
                "Diagnostic module returned the following error message:\n%s", out["description"]
            )

        finally:
            for user in (self.schoolA.teacher, self.schoolA.student):
                logger.info("*** Remove {} from group {}".format(user.dn, class_dn))
                try:
                    self.lo.modify(
                        class_dn, [["uniqueMember", user.dn.encode("UTF-8"), None], ["memberUid", user.name.encode("UTF-8"), None]]
                    )
                except Exception as exc:
                    logger.error("Failed to remove %r from %r: %r", user.dn, class_dn, exc)


def test_diagnostics_module_all_tests():
    with UCSSchoolSchoolConsistency() as test_suite:
        test_suite.create_multi_env_school_objects()
        test_suite.run_all_tests()
