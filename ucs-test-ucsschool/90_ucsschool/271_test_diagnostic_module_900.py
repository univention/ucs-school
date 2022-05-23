#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Check diagnostic tool UCS@school Replica Directory Node groupmemberships
## roles: [domaincontroller_master]
## tags: [ucsschool,diagnostic_test]
## exposure: dangerous
## packages: [ucs-school-import]


from __future__ import absolute_import, print_function

import re
from typing import List # noqa: F401

from univention.admin.uexceptions import ldapError
from univention.management.console.modules.diagnostic import Critical, Instance
from univention.testing.ucsschool.ucs_test_school import AutoMultiSchoolEnv, logger


class UCSSchoolSlaveGroupMemberships(AutoMultiSchoolEnv):
    def unique_members(self, grp_dn):  # type: () -> List[bytes]
        res = self.lo.get(grp_dn, ["uniqueMember"], required=True)
        if "uniqueMember" in res:
            return res["uniqueMember"]
        else:
            return []

    def run_all_tests(self):  # type: () -> None
        expected_warnings_slave = []
        expected_warnings_member = []

        slave_list = self.lo.searchDn(filter="(univentionObjectType=computers/domaincontroller_slave)")
        member_list = self.lo.searchDn(filter="(univentionObjectType=computers/memberserver)")
        slave_dn = slave_list[0]
        member_dn = member_list[0]

        # Remove a Replica Directory Node from DC-Edukativnetz
        grp_dn = "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(self.ucr.get("ldap/base"))
        try:
            self.lo.modify(grp_dn, [("uniqueMember", slave_dn, None)])
        except ldapError:
            # makes running subsequent running of the script easier.
            logger.debug("{} already removed from group {}.".format(slave_dn, grp_dn))
        expected_warnings_slave.append(
            "Host object is member of global edu group but not in OU specific Replica Directory Node "
            "group (or the other way around)"
        )

        # Add Replica Directory Node to OUschoola-DC-Verwaltungsnetz
        grp_dn = "cn=OU{}-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(
            self.schoolA.name, self.ucr.get("ldap/base")
        )
        unique_members = self.unique_members(grp_dn)
        unique_members.append(slave_dn.encode("UTF-8"))
        self.lo.modify(grp_dn, [("uniqueMember", self.unique_members(grp_dn), unique_members)])
        expected_warnings_slave.append(
            "Host object is member of global admin group but not in OU specific Replica Directory Node "
            "group (or the other way around)"
        )

        # Add Replica Directory Node to Member-Edukativnetz
        grp_dn = "cn=Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(self.ucr.get("ldap/base"))
        unique_members = self.unique_members(grp_dn)
        unique_members.append(slave_dn.encode("UTF-8"))
        self.lo.modify(grp_dn, [("uniqueMember", self.unique_members(grp_dn), unique_members)])
        expected_warnings_slave.append("Replica Directory Node object is member of Managed Node groups")
        expected_warnings_slave.append(
            "Host object is member of global edu group but not of OU specific Managed Node group (or "
            "the other way around)"
        )

        # Add slave_dn to OU{}-Member-Verwaltungsnetz
        grp_dn = "cn=OU{}-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(
            self.schoolA.name, self.ucr.get("ldap/base")
        )
        unique_members = self.unique_members(grp_dn)
        unique_members.append(slave_dn.encode("UTF-8"))
        self.lo.modify(grp_dn, [("uniqueMember", self.unique_members(grp_dn), unique_members)])
        expected_warnings_slave.append(
            "Host object is member of edu groups AND in admin groups which is not allowed"
        )

        # Add the Managed Node to DC-Edukativnetz
        grp_dn = "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(self.ucr.get("ldap/base"))
        unique_members = self.unique_members(grp_dn)
        unique_members.append(slave_dn.encode("UTF-8"))
        self.lo.modify(grp_dn, [["uniqueMember", self.unique_members(grp_dn), unique_members]])
        expected_warnings_member.append("Managed Node object is member of Replica Directory Node groups")

        logger.info(
            "Run diagnostic tool, capture and test if warnings were raised. The dns of the client "
            "computers should appear be in the warnings."
        )
        module_name = "900_ucsschool_slave_groupmemberships"
        instance = Instance()
        instance.init()
        module = instance.get(module_name)
        out = None
        try:
            out = module.execute(None)
        except Critical:
            pass

        assert out and out["success"] is False
        # Split by computer dn and save in dict (first element is empty)
        warnings = re.split(r"([^\s]+?cn=computers.+?)\n", out["description"])[1:]
        warnings = dict(zip(warnings[::2], warnings[1::2]))

        for warning in expected_warnings_slave:
            if warning not in warnings[slave_dn]:
                raise Exception(
                    "diagnostic tool {} did not raise warning for {}!\n".format(module_name, warning)
                )
        for warning in expected_warnings_member:
            if warning not in warnings[member_dn]:
                raise Exception(
                    "diagnostic tool {} did not raise warning for {}!\n".format(module_name, warning)
                )

        logger.info("Ran diagnostic tool {} successfully.".format(module_name))


def test_diagnostic_module_090():
    with UCSSchoolSlaveGroupMemberships() as test_suite:
        test_suite.create_multi_env_global_objects()
        test_suite.create_multi_env_school_objects()
        test_suite.run_all_tests()
