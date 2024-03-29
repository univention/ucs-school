#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test PostReadPyHook functionality
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [47221]

import copy
import os
import os.path
import shutil

from ldap.filter import escape_filter_chars

import univention.testing.strings as uts
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester

TESTHOOKSOURCE = os.path.join(os.path.dirname(__file__), "test237_post_read_pyhookpy")
TESTHOOKTARGET = "/usr/share/ucs-school-import/pyhooks/test237_post_read_pyhook.py"


class Test(CLI_Import_v2_Tester):
    ou_B = None
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

    def test(self):
        source_uid = "source_uid-{}".format(uts.random_string())
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        self.log.info("Creating PyHook %r...", TESTHOOKTARGET)
        shutil.copy(TESTHOOKSOURCE, TESTHOOKTARGET)

        self.log.info("*** Importing a user from each role, PostReadPyHook will:")
        self.log.info(
            "*** a) switch firstname and lastname b) add a birthday c) raise & test a class level "
            "variable..."
        )
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            person.update(firstname=person.lastname, lastname=person.firstname, birthday="2018-08-27")
            person.verify()


if __name__ == "__main__":
    Test().run()
