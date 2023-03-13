#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test that multiple output arguments can be passed via the --set argument
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [53632]

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
        self.summary_fd = tempfile.NamedTemporaryFile(delete=False, mode="w+")
        self.passwords_fd = tempfile.NamedTemporaryFile(delete=False, mode="w+")

    def cleanup(self):
        super(Test, self).cleanup()
        os.remove(self.summary_fd.name)
        os.remove(self.passwords_fd.name)

    def test(self):
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("dry_run", True)
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)
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
        config.update_entry("dry_run", True)
        args = [
            "--set",
            f"output:user_import_summary={self.summary_fd.name}",
            f"output:new_user_passwords={self.passwords_fd.name}",
        ]
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config] + args)  # start import (dry-run)

        # check that both summary & password file were used.
        self.summary_fd.seek(os.SEEK_SET)
        reader = csv.DictReader(self.summary_fd)
        count = 0
        for index, row in enumerate(reader):
            count += 1
            assert row["firstname"] == person_list[index].firstname
            assert row["lastname"] == person_list[index].lastname
        assert count, "Empty user import summary file."

        self.passwords_fd.seek(os.SEEK_SET)
        reader = csv.DictReader(self.passwords_fd)
        assert list(reader), "Empty new user passwords file."


if __name__ == "__main__":
    Test().run()
