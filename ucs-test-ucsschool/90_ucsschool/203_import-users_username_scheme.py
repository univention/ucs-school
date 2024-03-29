#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test creation of usernames from a special username scheme (Bug #41243, #41244)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41243, 41244]

import copy

from ldap.filter import filter_format

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import UniqueObjectTester


class Test(UniqueObjectTester):
    def __init__(self):
        super(Test, self).__init__()
        self.ou_B = None
        self.ou_C = None

    def test(self):  # formerly test_create_with_username_scheme()
        """Test creation of usernames from a special username scheme (Bug #41243, #41244)."""
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)

        for scheme in ["ALWAYSCOUNTER", "COUNTER2"]:
            source_uid = "source_uid-%s" % (uts.random_string(),)
            config.update_entry("source_uid", source_uid)
            config.update_entry(
                "scheme:username:default",
                "<:umlauts>user-<firstname>[0:2].<lastname>[0:2]-[{}]".format(scheme),
            )
            self.log.info("*** Importing a user of each role and username scheme %r - 1. time", scheme)
            person_list = []
            for role in ("student", "teacher", "staff", "teacher_and_staff"):
                person = Person(self.ou_A.name, role)
                person.update(record_uid=uts.random_name(), source_uid=source_uid, username=None)
                person.username_prefix = None
                person_list.append(person)

            fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
            config.update_entry("input:filename", fn_csv)
            fn_config = self.create_config_json(config=config)
            self.save_ldap_status()
            self.run_import(["-c", fn_config, "-i", fn_csv])
            self.check_new_and_removed_users(4, 0)

            for person in person_list:
                person.update_from_ldap(self.lo, ["dn", "username"])
                wait_for_drs_replication(filter_format("cn=%s", (person.username,)))
                person.verify()

                person.username_prefix = "user%s.%s" % (person.firstname[0:2], person.lastname[0:2])
                self.log.info("Calculated person.username_prefix is %r.", person.username_prefix)
                self.unique_basenames_to_remove.append(person.username_prefix)
                if person.username != "{}{}".format(
                    person.username_prefix, "1" if scheme == "ALWAYSCOUNTER" else ""
                ):
                    self.fail(
                        'username %r is not expected string "%s%s"'
                        % (
                            person.username,
                            person.username_prefix,
                            "1" if scheme == "ALWAYSCOUNTER" else "",
                        )
                    )
                self.log.info(
                    'Username %r is expected with string "%s%s"',
                    person.username,
                    person.username_prefix,
                    "1" if scheme == "ALWAYSCOUNTER" else "",
                )
                self.check_unique_obj("unique-usernames", person.username_prefix, "2")

            for ext in [2, 3]:
                self.log.info("*** Deleting users - %d. time", ext - 1)
                fn_csv = self.create_csv_file(person_list=[], mapping=config["csv"]["mapping"])
                config.update_entry("input:filename", fn_csv)
                fn_config = self.create_config_json(config=config)
                self.save_ldap_status()
                self.run_import(["-c", fn_config, "-i", fn_csv])
                utils.wait_for_replication()
                self.check_new_and_removed_users(0, 4)
                for person in person_list:
                    person.set_mode_to_delete()
                    person.verify()

                self.log.info("*** Importing same users - %d. time", ext)
                for person in person_list:
                    person.update(username=None, mode="A")
                fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
                config.update_entry("input:filename", fn_csv)
                fn_config = self.create_config_json(config=config)
                self.save_ldap_status()
                self.run_import(["-c", fn_config, "-i", fn_csv])
                utils.wait_for_replication()
                self.check_new_and_removed_users(4, 0)
                for person in person_list:
                    person.update_from_ldap(self.lo, ["dn", "username"])
                    wait_for_drs_replication(filter_format("cn=%s", (person.username,)))
                    person.verify()
                    if person.username != "{}{}".format(person.username_prefix, ext):
                        self.fail(
                            'username %r is not expected string "%s%d"'
                            % (person.username, person.username_prefix, ext)
                        )
                    self.log.info(
                        'Username %r is expected with string "%s%d',
                        person.username,
                        person.username_prefix,
                        ext,
                    )
                    self.check_unique_obj("unique-usernames", person.username_prefix, str(ext + 1))


if __name__ == "__main__":
    Test().run()
