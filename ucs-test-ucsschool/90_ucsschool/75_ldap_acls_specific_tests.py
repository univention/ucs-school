#!/usr/share/ucs-test/runner python
# coding=utf-8
## desc: check specific LDAP access permissions
## roles: [domaincontroller_master]
## tags: [apptest, ucsschool,ucsschool_base1]
## timeout: 3600
## exposure: dangerous
## packages: [ucs-school-ldap-acls-master]
## bugs: [35447]

# This test creates 3 school OUs containing users, groups and computers:
# 1) "schoolA", whose user members are single-school users in "schoolA"
# 2) "schoolB", whose user members are multi-school users in "schoolA" AND "schoolB"
# 3) "schoolC", whose user members are single-school users in "schoolC"
# and additionally some central/global users/computers are also created.
#
# WARNING: ACL tests are run by actively modifying the LDAP directory!
#
# For debugging purposes, you can create /tmp/75_ldap_acls_specific_tests.debug before
# starting the test. Then, the environment is set up, and the script waits for the
# existance of /tmp/75_ldap_acls_specific_tests.continue before the actual tests and
# cleanup tasks are performed.


from __future__ import absolute_import, print_function

import os
import random
import time
import uuid

import univention.admin.uldap
import univention.testing.strings as uts
import univention.testing.udm
from univention.testing.ucsschool.ucs_test_school import AutoMultiSchoolEnv, logger

try:
    from typing import List, Union
except ImportError:
    pass

ATTR2TYPE = {
    "krb5KeyVersionNumber": "str_int",
    "sambaPwdLastSet": "str_int",
    "shadowLastChange": "str_int",
    "shadowMax": "str_int",
    "sambaBadPasswordCount": "str_int",
    "ucsschoolUsernameNextNumber": "str_int",
}

PASSWORD_ATTRIBUTES = [
    "krb5KeyVersionNumber",
    # 	'krb5KDCFlags',
    "krb5Key",
    # 	'krb5PasswordEnd',
    # 	'sambaAcctFlags',
    "sambaPwdLastSet",
    "sambaLMPassword",
    "sambaNTPassword",
    # 	'shadowLastChange',
    "shadowMax",
    "userPassword",
    "pwhistory",
    # 	'sambaPwdCanChange',
    # 	'sambaPwdMustChange',
    "sambaPasswordHistory",
    # 	'sambaBadPasswordCount',
]


class ACLTester(object):
    def __init__(self, ucr, actor_dn):
        self.actor_dn = actor_dn
        logger.info("ACTOR: %s", self.actor_dn)
        self.lo = univention.admin.uldap.access(
            host=ucr["ldap/master"],
            port=int(ucr.get("ldap/master/port", "7389")),
            base=ucr["ldap/base"],
            binddn=actor_dn,
            bindpw="univention",
        )
        self.errors = []  # type: List[str]

    def test_object(self, dn, permission):
        logger.info("test_object(%r, %r)", dn, permission)
        assert permission in ("none", "read")
        try:
            result = self.lo.get(dn)
            if result and permission == "none":
                self.errors.append(
                    "Expected that {!r} has NO permission to read object  {!r} but is able to "
                    "read".format(self.actor_dn, dn)
                )
            if not result and permission == "read":
                self.errors.append(
                    "Expected that {!r} has permission to read object {!r} but object has not been "
                    "found".format(self.actor_dn, dn)
                )
        except univention.admin.uexceptions.noObject:
            if permission == "read":
                self.errors.append(
                    "Expected that {!r} has permission to read object {!r} but object has not been "
                    "found".format(self.actor_dn, dn)
                )

    def test_attribute(self, dn, attribute, permission):
        """
        Checks if self.actor_dn is able to read/modify the list of given attributes at specified dn.
        Valid permissions are 'none', 'read' and 'write'.
        """
        logger.info("test_attribute(%r, %r, %r)", dn, attribute, permission)
        assert permission in ("none", "read", "write")

        attr_type = ATTR2TYPE.get(attribute, "str")
        if attr_type == "str":
            value = [uts.random_string()]  # type: Union[str, List[str]]
        elif attr_type == "str_int":
            value = str(random.randint(100000, 999999))
        else:
            raise Exception("Unknown attribute type: {}".format(attr_type))

        if permission == "none":
            result = self.lo.get(dn)
            try:
                self.lo.modify(dn, [[attribute, result.get(attribute), value]])
                self.lo.modify(dn, [[attribute, value, result.get(attribute)]])
                self.errors.append(
                    "Expected that {!r} has NO permission to read attribute {!r} from {!r} but is also "
                    "able to write".format(self.actor_dn, attribute, dn)
                )
            except univention.admin.uexceptions.noObject:
                logger.info(
                    "Expected that {!r} has NO permission to read attribute {!r} from {!r}: object is "
                    "not readable at all".format(self.actor_dn, attribute, dn)
                )
            except univention.admin.uexceptions.permissionDenied:
                if result.get(attribute) is not None:
                    self.errors.append(
                        "Expected that {!r} has NO permission to read attribute {!r} from {!r}: "
                        "result={!r}".format(self.actor_dn, attribute, dn, result.get(attribute))
                    )

        elif permission == "read":
            result = self.lo.get(dn)
            # Disabled on purpose: object attributes may be empty
            # 			if result.get(attribute) is None:
            # 				self.errors.append('Expected that {!r} has permission to read attribute {!r}
            # 				from {!r}: result={!r}'.format(self.actor_dn, attribute, dn,
            # 				result.get(attribute)))
            try:
                self.lo.modify(dn, [[attribute, result.get(attribute), value]])
                self.lo.modify(dn, [[attribute, value, result.get(attribute)]])
                self.errors.append(
                    "Expected that {!r} has only permission to read attribute {!r} from {!r} but is also"
                    " able to write".format(self.actor_dn, attribute, dn)
                )
            except univention.admin.uexceptions.noObject:
                self.errors.append(
                    "Expected that {!r} has permission to modify {!r} of {!r} but object is not "
                    "readable/does not exist".format(self.actor_dn, attribute, dn)
                )
            except univention.admin.uexceptions.permissionDenied:
                pass

        elif permission == "write":
            result = self.lo.get(dn)
            try:
                self.lo.modify(dn, [[attribute, result.get(attribute), value]])
                self.lo.modify(dn, [[attribute, value, result.get(attribute)]])
            except univention.admin.uexceptions.noObject:
                self.errors.append(
                    "Expected that {!r} has permission to modify {!r} of {!r} but object is not "
                    "readable/does not exist".format(self.actor_dn, attribute, dn)
                )
            except univention.admin.uexceptions.permissionDenied:
                self.errors.append(
                    "Expected that {!r} has permission to modify {!r} of {!r} but can only read: "
                    "result={!r}".format(self.actor_dn, attribute, dn, result.get(attribute))
                )

    def raise_on_error(self):
        """
        Raises an exception with detailed information, if there was at least one error during previous
        checks.
        """
        if not self.errors:
            return
        all_msgs = []
        for i, msg in enumerate(self.errors):
            all_msgs.append("ERROR {}) {}".format(i, msg))
        raise Exception(
            "There were {} ACL errors with {!r}:\n{}".format(
                len(self.errors), self.actor_dn, "\n".join(all_msgs)
            )
        )


class LDAPACLCheck(AutoMultiSchoolEnv):
    def create_counter_object(self, counter_type):
        cn = str(uuid.uuid4()).replace("-", "")
        dn = "cn={},cn=unique-{},cn=ucsschool,cn=univention,{}".format(
            cn, counter_type, self.ucr.get("ldap/base")
        )
        logger.info("Creating {}".format(dn))
        logger.info(
            self.lo.add(
                dn,
                [
                    ("objectClass", "ucsschoolUsername"),
                    ("ucsschoolUsernameNextNumber", "2"),
                    ("cn", cn),
                ],
            )
        )
        self._ldap_objects_in_test_ous.setdefault(dn, set()).update(self.get_ldap_status(self.lo, dn))
        return dn

    def run_all_tests(self):  # type: () -> None
        self.test_schooladmin_base_dn()
        self.test_schooladmin_pw_reset()
        self.test_import_counter_objects()

    def test_schooladmin_base_dn(self):  # type: () -> None
        """
        Check if school admin is able to modify a selected list of attributes
        at LDAP base dn.
        """
        acl_tester = ACLTester(self.ucr, self.schoolA.admin1.dn)
        for attr_name in [
            "univentionObjectType",
            "univentionPolicyReference",
            "krb5RealmName",
            "msGPOLink",
        ]:
            acl_tester.test_attribute(self.ucr.get("ldap/base"), attr_name, "read")

    def test_schooladmin_pw_reset(self):  # type: () -> None
        """
        Bug #35447:
        Check if schooladmins are able to reset passwords of
        - students
        - teachers
        - teachers and staff
        - staff
        But not
        - other schooladmins of same/other OU
        - domain admins
        - global users
        """

        acl_tester = ACLTester(self.ucr, self.schoolA.admin1.dn)
        for permission, dn in [
            # generic
            ("none", self.generic.domain_admin.dn),
            ("none", self.generic.domain_user.dn),
            # school A
            ("write", self.schoolA.student.dn),
            ("write", self.schoolA.teacher.dn),
            ("write", self.schoolA.teacher_staff.dn),
            ("write", self.schoolA.staff.dn),
            ("read", self.schoolA.admin1.dn),
            ("read", self.schoolA.admin2.dn),
            # school B
            ("write", self.schoolB.student.dn),
            ("write", self.schoolB.teacher.dn),
            ("write", self.schoolB.teacher_staff.dn),
            ("write", self.schoolB.staff.dn),
            ("read", self.schoolB.admin1.dn),
            ("read", self.schoolB.admin2.dn),
            # school C
            ("none", self.schoolC.student.dn),
            ("none", self.schoolC.teacher.dn),
            ("none", self.schoolC.teacher_staff.dn),
            ("none", self.schoolC.staff.dn),
            ("none", self.schoolC.admin1.dn),
            ("none", self.schoolC.admin2.dn),
        ]:
            for attr_name in PASSWORD_ATTRIBUTES:
                acl_tester.test_attribute(dn, attr_name, permission)
        acl_tester.raise_on_error()

        acl_tester = ACLTester(self.ucr, self.schoolB.admin1.dn)
        for permission, dn in [
            # generic
            ("none", self.generic.domain_admin.dn),
            ("none", self.generic.domain_user.dn),
            # school A
            ("write", self.schoolA.student.dn),
            ("write", self.schoolA.teacher.dn),
            ("write", self.schoolA.teacher_staff.dn),
            ("write", self.schoolA.staff.dn),
            ("read", self.schoolA.admin1.dn),
            ("read", self.schoolA.admin2.dn),
            # school B
            ("write", self.schoolB.student.dn),
            ("write", self.schoolB.teacher.dn),
            ("write", self.schoolB.teacher_staff.dn),
            ("write", self.schoolB.staff.dn),
            ("read", self.schoolB.admin1.dn),
            ("read", self.schoolB.admin2.dn),
            # school C
            ("none", self.schoolC.student.dn),
            ("none", self.schoolC.teacher.dn),
            ("none", self.schoolC.teacher_staff.dn),
            ("none", self.schoolC.staff.dn),
            ("none", self.schoolC.admin1.dn),
            ("none", self.schoolC.admin2.dn),
        ]:
            for attr_name in PASSWORD_ATTRIBUTES:
                acl_tester.test_attribute(dn, attr_name, permission)
        acl_tester.raise_on_error()

        acl_tester = ACLTester(self.ucr, self.schoolC.admin1.dn)
        for permission, dn in [
            # generic
            ("none", self.generic.domain_admin.dn),
            ("none", self.generic.domain_user.dn),
            # school A
            ("none", self.schoolA.student.dn),
            ("none", self.schoolA.teacher.dn),
            ("none", self.schoolA.teacher_staff.dn),
            ("none", self.schoolA.staff.dn),
            ("none", self.schoolA.admin1.dn),
            ("none", self.schoolA.admin2.dn),
            # school B
            ("none", self.schoolB.student.dn),
            ("none", self.schoolB.teacher.dn),
            ("none", self.schoolB.teacher_staff.dn),
            ("none", self.schoolB.staff.dn),
            ("none", self.schoolB.admin1.dn),
            ("none", self.schoolB.admin2.dn),
            # school C
            ("write", self.schoolC.student.dn),
            ("write", self.schoolC.teacher.dn),
            ("write", self.schoolC.teacher_staff.dn),
            ("write", self.schoolC.staff.dn),
            ("read", self.schoolC.admin1.dn),
            ("read", self.schoolC.admin2.dn),
        ]:
            for attr_name in PASSWORD_ATTRIBUTES:
                acl_tester.test_attribute(dn, attr_name, permission)
        acl_tester.raise_on_error()

    def test_import_counter_objects(self):  # type: () -> None
        """
        Check if the UCS@school import counter objects are not readable
        for school servers.
        """
        for permission, actor_dn in [
            # generic
            ("read", self.generic.domain_admin.dn),
            ("read", self.generic.domain_user.dn),
            # 				('read', self.generic.master.dn),  # disabled due to unknown password
            ("read", self.generic.backup.dn),
            ("none", self.generic.slave.dn),
            ("none", self.generic.member.dn),
            # school A
            ("read", self.schoolA.student.dn),
            ("read", self.schoolA.teacher.dn),
            ("read", self.schoolA.teacher_staff.dn),
            ("read", self.schoolA.staff.dn),
            ("read", self.schoolA.admin1.dn),
            ("read", self.schoolA.admin2.dn),
            ("none", self.schoolA.schoolserver.dn),
            # school B
            ("read", self.schoolB.student.dn),
            ("read", self.schoolB.teacher.dn),
            ("read", self.schoolB.teacher_staff.dn),
            ("read", self.schoolB.staff.dn),
            ("read", self.schoolB.admin1.dn),
            ("read", self.schoolB.admin2.dn),
            ("none", self.schoolB.schoolserver.dn),
            # school C
            ("read", self.schoolC.student.dn),
            ("read", self.schoolC.teacher.dn),
            ("read", self.schoolC.teacher_staff.dn),
            ("read", self.schoolC.staff.dn),
            ("read", self.schoolC.admin1.dn),
            ("read", self.schoolC.admin2.dn),
            ("none", self.schoolC.schoolserver.dn),
        ]:
            acl_tester = ACLTester(self.ucr, str(actor_dn))
            for counter_dn in self.counter_dn_list:
                acl_tester.test_object(str(counter_dn), permission)
        acl_tester.raise_on_error()


def main():
    with LDAPACLCheck() as test_suite:
        test_suite.create_multi_env_global_objects()
        test_suite.create_multi_env_school_objects()
        test_suite.counter_dn_list = [
            test_suite.create_counter_object("usernames"),
            test_suite.create_counter_object("email"),
        ]

        # for debugging purposes
        if os.path.exists("/tmp/75_ldap_acls_specific_tests.debug"):
            fn = "/tmp/75_ldap_acls_specific_tests.continue"
            logger.info("=== DEBUGGING MODE ===")
            logger.info("Waiting for cleanup until %r exists...", fn)
            while not os.path.exists(fn):
                time.sleep(1)

        test_suite.run_all_tests()


if __name__ == "__main__":
    main()
