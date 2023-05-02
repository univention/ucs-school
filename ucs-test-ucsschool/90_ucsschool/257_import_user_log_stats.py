#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test import statistics log config
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [53734]

import random
import re
import subprocess
from copy import deepcopy
from math import ceil

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):
        number_of_users = 20
        self.log.info(f"*** Import {number_of_users} new users...")

        columns = random.randint(1, number_of_users)
        lines = random.randint(ceil(number_of_users / columns), number_of_users)

        # configure through UCR
        self.ucr.handler_set([f"ucsschool/import/log_stats/columns={columns}"])
        self.ucr.handler_set([f"ucsschool/import/log_stats/lines={lines}"])

        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = deepcopy(self.default_config)
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        role = random.choice(["student", "teacher", "staff", "teacher_and_staff"])
        person_list = []
        for _ in range(number_of_users):
            person = Person(
                self.ou_A.name,
                role,
            )
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        args = ["-c", fn_config]
        cmd = ["/usr/share/ucs-school-import/scripts/ucs-school-user-import", "-v"] + args
        proc = subprocess.run(cmd, capture_output=True, text=True)

        stats = re.search(
            "------ User import statistics ------\n(.*)------ End of user import statistics ------",
            proc.stderr,
            re.DOTALL,
        )

        assert (
            stats is not None
        ), "No statistics found in stderr, probably the import failed for another reason"
        assert " Errors: 0" in stats.group(1), "Errors found in statistics: %s" % (stats.group(1),)

        count = 0
        max_users_in_line = 0
        for line in stats.group(1).split("\n"):
            match = re.search(r"\[(.*)\]", line)
            if match:
                usernames = match.group(1).count("', '") + 1
                count += usernames
                if usernames > max_users_in_line:
                    max_users_in_line = usernames
                assert (
                    usernames <= columns
                ), f"Too many usernames in one line: {usernames} (should be {columns})"
        assert count == number_of_users, f"Not all users were shown: {count} out of {number_of_users}"
        if number_of_users > columns:
            assert (
                max_users_in_line == columns
            ), f"Columns setting not respected: {max_users_in_line} (should be {columns})"


if __name__ == "__main__":
    Test().run()
