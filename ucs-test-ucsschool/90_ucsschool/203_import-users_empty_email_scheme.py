#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test creation of email addresses from an empty scheme (Bug #45972)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [45972]

import copy

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import UniqueObjectTester


class Test(UniqueObjectTester):
    def __init__(self):
        super(Test, self).__init__()
        self.ou_B = None
        self.ou_C = None

    def test(self):
        source_uid = "source_uid-{}".format(uts.random_string())
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)
        del config["csv"]["mapping"]["E-Mail"]
        del config["scheme"]["email"]

        self.log.info(
            "*** 1/2 Importing a user of each role without email in input and without email in scheme..."
        )

        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            record_uid = "record_uid-%s" % (uts.random_string(),)
            person.update(record_uid=record_uid, source_uid=source_uid, mail=None)
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(4, 0)

        for person in person_list:
            person.verify()

        self.log.info("*** OK 1/2 All %r users were created correctly.", len(person_list))
        self.log.info(
            "*** 2/2 Importing a user of each role with email in input and without email in scheme..."
        )

        source_uid = "source_uid-{}".format(uts.random_string())
        config.update_entry("source_uid", source_uid)
        config["csv"]["mapping"]["E-Mail"] = self.default_config["csv"]["mapping"]["E-Mail"]
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            record_uid = "record_uid-%s" % (uts.random_string(),)
            person.update(record_uid=record_uid, source_uid=source_uid)
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(4, 0)

        for person in person_list:
            person.verify()

        self.log.info("*** OK 2/2 All %r users were created correctly.", len(person_list))
        self.log.info("*** OK 2/2 All users were created correctly.")


def main():
    tester = Test()
    try:
        tester.run()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
