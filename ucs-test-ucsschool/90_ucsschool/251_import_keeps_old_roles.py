#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: The importer should not remove existing admin roles or non ucsschool roles
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [53203]

import copy

from ldap.filter import filter_format

import univention.testing.strings as uts
from ucsschool.lib.models.user import User
from ucsschool.lib.roles import create_ucsschool_role_string, role_school_admin
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    def test(self):
        # import a teacher
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        self.log.info("*** 1. Importing (create in %r) new user with teacher role....", self.ou_A.name)
        person_list = []
        person = Person(self.ou_A.name, "teacher")
        person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
        person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])

        for person in person_list:
            person.verify()
        self.log.info("OK: import (create) succeeded.")

        # add admin role to teacher
        admin_role = create_ucsschool_role_string(role_school_admin, self.ou_A.name)
        admin_group = "cn=admins-{},cn=ouadmins,cn=groups,{}".format(
            self.ou_A.name, self.ucr["ldap/base"]
        )

        # TODO: use udm.modify_object instead (requires caching of udm object in TestUDM!)
        # admin_modifications = {"ucsschoolRole": [admin_role], "groups": [admin_group]}
        # self.udm.modify_object("users/user", dn=person.dn, append=admin_modifications)
        self.schoolenv.lo.modify(admin_group, [("uniqueMember", b"", person.dn.encode("UTF-8"))])
        self.schoolenv.lo.modify(person.dn, [("ucsschoolRole", b"", admin_role.encode("UTF-8"))])
        self.schoolenv.lo.modify(person.dn, [("objectClass", b"", b"ucsschoolAdministrator")])
        wait_for_drs_replication(filter_format("cn=%s", (person.username,)))

        # run same import again
        self.run_import(["-c", fn_config, "-i", fn_csv])
        self.log.info("OK: import (modify) succeeded.")

        # check if admin properties still exist
        user = User.from_dn(person.dn, person.school, self.lo).get_udm_object(self.lo)
        assert admin_role in user["ucsschoolRole"]
        assert admin_group in user["groups"]


if __name__ == "__main__":
    Test().run()
