#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: import users with an empty class name (Bug 41847)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41847]

import copy

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formally test_create_with_empty_class_name()
        """Bug #41847: import users with an empty class name"""
        config = copy.deepcopy(self.default_config)
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)

        self.log.info("*** Importing a new user of each role role and empty class name.")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(school_classes={})
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config, "-i", fn_csv])
        self.check_new_and_removed_users(4, 0)
        self.log.info("OK, all users could be imported with an empty CSV class column.")


if __name__ == "__main__":
    Test().run()
