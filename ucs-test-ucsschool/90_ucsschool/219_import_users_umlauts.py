#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Make sure :umlauts work as expected
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [44370, 47304, 48650, 47351]

import copy
import random

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formerly test_create_modify_delete_user()
        """
        for role in ('student', 'teacher', 'staff', 'teacher_and_staff'):
            import user with role <role>
            modify user with role <role> → changing group memberships
            remove user with role <role>
        """
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("source_uid", source_uid)
        config.update_entry("scheme:username:default", "<:umlauts><firstname>[0].<lastname><:lower>")
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)

        roles = ("student", "teacher", "staff", "teacher_and_staff")
        names = [
            {
                "firstname": "Ýlang",
                "lastname": "Müstèrmánn",
                "expected": {
                    "username": "y.muestermann",
                    "firstname": "Ýlang",
                    "lastname": "Müstèrmánn",
                },
            },
            {
                "firstname": "Öle",
                "lastname": "Mästèrmànn",
                "expected": {"username": "oe.maestermann", "firstname": "Öle", "lastname": "Mästèrmànn"},
            },
            {
                "firstname": "Nînä",
                "lastname": "Müstèrfräú",
                "expected": {
                    "username": "n.muesterfraeu",
                    "firstname": "Nînä",
                    "lastname": "Müstèrfräú",
                },
            },
            {
                "firstname": "Ǹanâ",
                "lastname": "Mästérfrâü",
                "expected": {
                    "username": "n.maesterfraue",
                    "firstname": "Ǹanâ",
                    "lastname": "Mästérfrâü",
                },
            },
        ]
        random.shuffle(names)
        person_list = []
        for role, name in zip(roles, names):
            person = Person(self.ou_A.name, role)
            person.update(username=None, firstname=name["firstname"], lastname=name["lastname"])
            person._expected_names = name["expected"]
            person_list.append(person)

        self.log.info("*** Importing users (normalize=False): %r", zip(roles, names))
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(4, 0)
        for person in person_list:
            person.update(
                username=person._expected_names["username"],
                record_uid=str("%s;%s;%s" % (person.firstname, person.lastname, person.mail)),
                source_uid=source_uid,
                firstname=person._expected_names["firstname"],
                lastname=person._expected_names["lastname"],
            )
            person.verify()


if __name__ == "__main__":
    Test().run()
