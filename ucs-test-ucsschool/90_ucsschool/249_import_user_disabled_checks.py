#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Test 'disabled_checks' feature
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [50406]

import copy

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):
        source_uid = "source_uid-{}".format(uts.random_string())
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)
        config.update_entry("source_uid", source_uid)

        # config errors:
        config.update_entry("username:max_length:default", 40)
        config.update_entry("user_deletion", 0)

        self.log.info('*** 1/2 Starting import without "disabled_checks" set...')

        person_list = list()
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(
                record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid,
            )
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        try:
            self.run_import(["-c", fn_config])
            self.fail("Import ran with bad settings.")
        except ImportException:
            self.log.info("*** OK - import stopped.")

        self.log.info('*** 2/2 Starting import with "disabled_checks" set...')

        self.run_import(
            [
                "-c",
                fn_config,
                "--set",
                "disabled_checks=test_username_max_length,test_deprecated_user_deletion",
            ]
        )
        self.log.info("OK: Import ran with bad (but ignored) settings.")


if __name__ == "__main__":
    Test().run()
