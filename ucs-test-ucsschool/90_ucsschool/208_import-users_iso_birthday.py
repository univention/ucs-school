#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Set ISO birthday (2016-06-23) for new users (Bug 41642)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41642]

import copy
import pprint
import time

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formally test_iso_birthday()
        """
        Bug #41642: Create/modify a new user for each role:
        - set ISO birthday (2016-06-23) for each user type
        """
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:birthday", "birthday")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)

        self.log.info("*** Importing a new users of each role with ISO birthday...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            # create person with ISO birthday (today)
            person = Person(self.ou_A.name, role)
            person.update(
                record_uid=person.username, source_uid=source_uid, birthday=time.strftime("%Y-%m-%d")
            )
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        # start import
        self.run_import(["-c", fn_config, "-i", fn_csv])

        for person in person_list:
            self.log.debug(
                "User object %r:\n%s",
                person.dn,
                pprint.PrettyPrinter(indent=2).pformat(self.lo.get(person.dn)),
            )
            person.verify()

            # modify person and set birthday to new year's day
            person.update(birthday="2016-01-01")

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        # start import
        self.run_import(["-c", fn_config, "-i", fn_csv])

        for person in person_list:
            self.log.debug(
                "User object %r:\n%s",
                person.dn,
                pprint.PrettyPrinter(indent=2).pformat(self.lo.get(person.dn)),
            )
            person.verify()


if __name__ == "__main__":
    Test().run()
