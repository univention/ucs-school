#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Check roles through the python client
## tags: [apptest,ucsschool,ucsschool_import1,ucs-school-import]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import-http-api
##   - ucs-school-import-http-api-client
## bugs: [45749]

import pprint

from ldap.filter import filter_format

import univention.testing.strings as uts
from ucsschool.http_api.client import Client
from univention.testing.ucsschool.importusers_http import HttpApiImportTester


class Test(HttpApiImportTester):
    def test(self):
        ou = self.ou_A
        password = uts.random_string()

        available_roles = [
            "student",
            "teacher",
            "staff",
            "teacher_and_staff",
            "legal_guardian",
        ]

        self.log.info("*** Creating user...")
        username, user_dn = self.schoolenv.create_teacher(ou.name, password=password)

        self.log.info("*** Create import-permission groups...")
        for role in available_roles:
            group_dn, group_name = self.create_import_security_group(
                ou_dn=ou.dn, allowed_ou_names=[ou.name], roles=[role], user_dns=[user_dn]
            )
            for dn, obj in self.lo.search(
                filter_format("(&(objectClass=ucsschoolImportGroup)(memberUid=%s))", (username,))
            ):
                self.log.info("%s: %s", dn, pprint.pformat(obj))

            client = Client(username, password, log_level=Client.LOG_RESPONSE)

            self.log.info("*** Checking schools via Python-API...")
            schools = client.school.list()
            expected_schools = {ou.name}
            received_schools = {s.name for s in schools}
            self.log.info("Expected schools: %r", expected_schools)
            self.log.info("Received schools: %r", received_schools)
            assert expected_schools == received_schools

            self.log.info("*** Checking roles via Python-API...")
            expected_roles = {role}
            roles_from_api = client.school.get(ou.name).roles
            received_roles = {r.name for r in roles_from_api}
            self.log.info("Expected roles: %r", expected_roles)
            self.log.info("Received roles: %r", received_roles)
            assert expected_roles == received_roles

            self.udm.remove_object("groups/group", wait_for_replication=True, dn=group_dn)


if __name__ == "__main__":
    Test().run()
