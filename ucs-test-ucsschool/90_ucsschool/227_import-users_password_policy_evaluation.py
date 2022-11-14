#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test that password policies get evaluated if ucr is set
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import

import copy

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def import_raises_exception(self, fn_config):
        try:
            self.run_import(["-c", fn_config])
            return False
        except Exception:
            return True

    def test(self):
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:password", "password")
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)
        config.update_entry(
            "mandatory_attributes",
            ["firstname", "lastname", "name", "record_uid", "school", "source_uid"],
        )
        self.log.info("*** Importing users of all roles...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(
                record_uid="record_uid-{}".format(uts.random_string()),
                source_uid=source_uid,
                password="t",
                description="test description",
            )
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        config.update_entry("evaluate_password_policies", True)
        fn_config = self.create_config_json(values=config)
        # create new users while evaluating password policies
        assert self.import_raises_exception(fn_config)
        config.update_entry("evaluate_password_policies", False)
        fn_config = self.create_config_json(values=config)
        # default behaviour: no password policy evaluation (default=false)
        assert not self.import_raises_exception(fn_config)
        # import should fail when modifying users while evaluating password policies
        # (policies are always evaluated on modify)
        assert self.import_raises_exception(fn_config)


if __name__ == "__main__":
    Test().run()
