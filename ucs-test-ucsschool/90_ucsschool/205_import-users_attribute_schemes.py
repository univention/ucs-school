#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: create with attribute schemes
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41472]

import copy
import pprint

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formerly test_create_with_attribute_schemes()
        """
        Tests Bug #41472.
        Create a new user for each role:
        - use UDM template syntax (http://docs.software-univention.de/handbuch-4.1.html#users:templates)
          to define several custom values
        - employeeNumber is filled with a string consisting of first and last name and description
        - mailPrimaryAddress is also built from those attributes
        """
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry(
            "scheme:email",
            "<:umlauts><firstname:lower>[0:3].<lastname:lower>[2:5]@{}".format(self.maildomain),
        )
        config.update_entry(
            "scheme:employeeNumber", "The user's name is <firstname:upper> <lastname> <description>"
        )
        config.update_entry("user_role", None)
        config.update_entry(
            "scheme:username:default", "<:umlauts>user-<firstname>[0:2].<lastname>[0:2]-[ALWAYSCOUNTER]"
        )
        del config["csv"]["mapping"]["E-Mail"]

        self.log.info("*** Importing new single user of each role from templates...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(
                record_uid=uts.random_name(),
                source_uid=source_uid,
                username=None,
                mail=None,
                description=uts.random_name(),
            )
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config, "-i", fn_csv])
        self.check_new_and_removed_users(4, 0)

        self.log.info("Testing mailPrimaryAddress and description...")
        for person in person_list:
            person.update_from_ldap(self.lo, ["dn", "username"])
            mail = "%s.%s@%s" % (
                person.firstname[0:3].lower(),
                person.lastname[2:5].lower(),
                self.maildomain,
            )
            person.update(mail=mail)
            person.verify()

            username_prefix = "user%s.%s" % (person.firstname[0:2], person.lastname[0:2])
            if person.username != "{}1".format(username_prefix):
                self.fail(
                    "username %r is not expected string %r"
                    % (person.username, "{}1".format(username_prefix))
                )
            self.log.info(
                "Username %r is expected string %r", person.username, "{}1".format(username_prefix)
            )
            values = {
                "employeeNumber": [
                    "The user's name is %s %s %s"
                    % (person.firstname.upper(), person.lastname, person.description)
                ],
            }
            self.log.debug(
                "User object %r:\n%s",
                person.dn,
                pprint.PrettyPrinter(indent=2).pformat(self.lo.get(person.dn)),
            )
            utils.verify_ldap_object(person.dn, expected_attr=values, strict=True, should_exist=True)


if __name__ == "__main__":
    Test().run()
