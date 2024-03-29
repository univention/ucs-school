#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test username scheme with <:lower> and [COUNTER2] (Bug 41645)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41645]

import copy
import pprint

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formally test_lowercase_username_with_counter()
        """Bug #41645: a username scheme with <:lower> and [COUNTER2]"""
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:DBID", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry(
            "scheme:email", "<:umlauts><firstname:lower>.<lastname:lower>@{}".format(self.maildomain)
        )
        config.update_entry(
            "scheme:employeeNumber", "The user's name is <firstname:upper> <lastname> <description>"
        )
        config.update_entry("user_role", None)
        del config["csv"]["mapping"]["E-Mail"]

        for scheme in ["ALWAYSCOUNTER", "COUNTER2"]:
            source_uid = "source_uid-%s" % (uts.random_string(),)
            config.update_entry("source_uid", source_uid)
            config.update_entry(
                "scheme:username:default",
                "<:lower><:umlauts><firstname>[0:6].<lastname>[0:3]a[{}]".format(scheme),
            )
            self.log.info("*** Importing a new user of eaach role from templates with scheme %r", scheme)
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

            for person in person_list:
                # update dn+username of person and verify LDAP attributes
                person.update_from_ldap(self.lo, ["dn", "username"])
                mail = "%s.%s@%s" % (person.firstname.lower(), person.lastname.lower(), self.maildomain)
                person.update(mail=mail)
                person.verify()

                username_prefix = "%s.%sa" % (person.firstname[0:6], person.lastname[0:3])
                if person.username != "{}{}".format(
                    username_prefix, "1" if scheme == "ALWAYSCOUNTER" else ""
                ):
                    self.fail(
                        "username %r is not expected string %r."
                        % (
                            person.username,
                            "{}{}".format(username_prefix, "1" if scheme == "ALWAYSCOUNTER" else ""),
                        )
                    )
                self.log.info(
                    "Username %r is not expected with string %r.",
                    person.username,
                    "{}{}".format(username_prefix, "1" if scheme == "ALWAYSCOUNTER" else ""),
                )

                self.log.info("Testing mailPrimaryAddress and description...")
                values = {
                    "employeeNumber": [
                        "The user's name is %s %s %s"
                        % (person.firstname.upper(), person.lastname, person.description)
                    ],
                }
                utils.verify_ldap_object(person.dn, expected_attr=values, strict=True, should_exist=True)
                self.log.debug(
                    "User object %r:\n%s",
                    person.dn,
                    pprint.PrettyPrinter(indent=2).pformat(self.lo.get(person.dn)),
                )


if __name__ == "__main__":
    Test().run()
