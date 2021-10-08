#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Test that the csv summary contains the changed user dta also in dry-run
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [53841]

import copy
import csv
import os
import tempfile

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def __init__(self):
        super(Test, self).__init__()
        self.summary_fd = tempfile.NamedTemporaryFile(delete=False)

    def cleanup(self):
        super(Test, self).cleanup()
        os.remove(self.summary_fd.name)

    def test(self):
        source_uid = "source_uid-%s" % (uts.random_string(),)

        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("dry_run", False)
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        self.log.info("*** Importing a new single user of each role...")
        person_list = [
            Person(
                self.ou_A.name,
                role,
                record_uid="record_uid-{}".format(uts.random_string()),
                source_uid=source_uid,
            )
            for role in ("student", "teacher", "staff", "teacher_and_staff")
        ]
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config])  # start import (real run)

        config.update_entry("dry_run", True)
        config.update_entry("output:user_import_summary", self.summary_fd.name)
        for person in person_list:
            person.firstname = uts.random_name()
            person.lastname = uts.random_name()
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config])  # start import (dry-run)

        self.summary_fd.seek(os.SEEK_SET)
        reader = csv.DictReader(self.summary_fd)
        for index, row in enumerate(reader):
            assert row["firstname"] == person_list[index].firstname
            assert row["lastname"] == person_list[index].lastname


if __name__ == "__main__":
    Test().run()
