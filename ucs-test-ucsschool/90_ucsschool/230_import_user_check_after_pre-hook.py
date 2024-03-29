#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test if pre_* hooks are executed
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [46384, 46439]

import copy
import os
import os.path
import random

import pytest
from ldap.filter import escape_filter_chars

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException

TESTHOOKSOURCE = os.path.join(os.path.dirname(__file__), "test230_check_after_pyhookpy")
TESTHOOKTARGET = "/usr/share/ucs-school-import/pyhooks/test230_check_after_pyhook.py"


class Test(CLI_Import_v2_Tester):
    ou_C = None

    def pyhook_cleanup(self):
        for ext in ["", "c", "o"]:
            path = "{}{}".format(TESTHOOKTARGET, ext)
            try:
                os.remove(path)
                self.log.info("*** Deleted %s.", path)
            except OSError:
                self.log.warning("*** Could not delete %s.", path)

    def cleanup(self):
        self.pyhook_cleanup()
        super(Test, self).cleanup()

    def create_pyhook(self, action, code):
        self.log.info("*** Creating PyHook for action %r (%r)...", action, TESTHOOKTARGET)
        with open(TESTHOOKSOURCE) as fp:
            text = fp.read()
        with open(TESTHOOKTARGET, "w") as fp:
            fp.write(text.replace("%ACTION%", action).replace("%CODE%", code))

    def test(self):
        source_uid = "source_uid-{}".format(uts.random_string())
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        self.log.info("*** 1/6 Importing a user from each role, pre_create without error...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.create_pyhook("create", 'user.birthday = "1907-06-05"')
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                expected_attr={"univentionBirthday": ["1907-06-05"]},
                strict=False,
                should_exist=True,
            )

        self.log.info("*** 2/6 Importing a user from each role, pre_modify without error...")
        self.create_pyhook("modify", 'user.birthday = "1908-07-06"')
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                expected_attr={"univentionBirthday": ["1908-07-06"]},
                strict=False,
                should_exist=True,
            )

        self.log.info(
            "*** 3/6 Importing a user from each role, pre_move (%r -> %r) without error...",
            self.ou_A.name,
            self.ou_B.name,
        )
        self.create_pyhook("move", 'user.birthday = "1910-09-08"')
        for person in person_list:
            person.update(school=self.ou_B.name)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            #
            # The birthday will not change, because the move() is followed by a
            # modify() for which there is no pyhook anymore.
            #
            utils.verify_ldap_object(
                person.dn,
                expected_attr={"univentionBirthday": ["1908-07-06"]},
                strict=False,
                should_exist=True,
            )

        self.log.info("*** 4/6 Importing a user from each role, pre_create with error...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            person_list.append(person)
        random.shuffle(person_list)
        self.log.info("*** First user: %s", person_list[0])
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.create_pyhook("create", 'user.birthday = "190706-05"')
        with pytest.raises(ImportException):
            self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        self.log.info("OK: import failed.")
        for person in person_list:
            utils.verify_ldap_object(person.dn, strict=False, should_exist=False)

        self.log.info("*** 5/6 Importing a user from each role, pre_modify with error...")
        self.log.info(
            "*** 5/6 But first importing a user from each role without error, so we can modify it..."
        )
        self.create_pyhook("create", 'user.birthday = "1910-11-12"')
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                expected_attr={"univentionBirthday": ["1910-11-12"]},
                strict=False,
                should_exist=True,
            )
        self.log.info("*** 5/6 Now importing again for pre_modify with error...")
        self.create_pyhook("modify", 'user.birthday = "1908-0706"')
        with pytest.raises(ImportException):
            self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        self.log.info("OK: import failed.")
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                expected_attr={"univentionBirthday": ["1910-11-12"]},
                strict=False,
                should_exist=True,
            )

        self.log.info(
            "*** 6/6 Importing a user from each role (reusing users from 5/6), pre_move (%r -> %r) with "
            "error...",
            self.ou_A.name,
            self.ou_B.name,
        )
        self.log.info(
            '*** 6/6 pre_move hook will rewrite user.school to "NoSchool" instead of %r, so error is '
            "found in move()-checks, not in the following modify()-checks",
            self.ou_B.name,
        )
        self.create_pyhook("move", 'user.school = "NoSchool"')
        for person in person_list:
            person.update(school=self.ou_B.name)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        with pytest.raises(ImportException):
            self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        self.log.info("OK: import failed.")
        # check they have not been moved
        for person in person_list:
            utils.verify_ldap_object(person.dn, strict=False, should_exist=False)
        for person in person_list:
            person.update(school=self.ou_A.name)
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                expected_attr={"univentionBirthday": ["1910-11-12"]},
                strict=False,
                should_exist=True,
            )


if __name__ == "__main__":
    Test().run()
