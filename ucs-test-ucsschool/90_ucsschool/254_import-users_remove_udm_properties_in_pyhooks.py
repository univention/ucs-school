#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test that users which will be deleted get udm_properties loaded
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [53649]

import copy
import os
import random
import shutil
import time

from ldap.filter import filter_format

import univention.testing.strings as uts
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester

TESTHOOKSOURCE = os.path.join(os.path.dirname(__file__), "test254_udm_properties_remove_pyhook")
TESTHOOKTARGET = "/usr/share/ucs-school-import/pyhooks/test254_udm_properties_remove_pyhook.py"


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

    def test(self):  # formally test_delete_variants()
        """Bug #53649: Test that udm_properties are loaded for users that are marked for deletion"""
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("csv:mapping:description", "description")
        config.update_entry("user_role", None)

        self.log.info("*** delete immediately ***")
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config.update_entry("source_uid", source_uid)
        # deletion_grace_period:deactivation should not matter if deletion_grace_period:deletion=0
        exp_days = random.randint(1, 20)
        config.update_entry("deletion_grace_period:deactivation", exp_days)
        config.update_entry("deletion_grace_period:deletion", 0)
        self.log.info("*** Importing a new single user of each role...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(
                record_uid="record_uid-{}".format(uts.random_string()),
                source_uid=source_uid,
                description="test description",
            )
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)

        self.save_ldap_status()  # save ldap state for later comparison
        self.run_import(["-c", fn_config])  # start import
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        ldap_diff = self.diff_ldap_status()
        if len([x for x in ldap_diff.new if x.startswith("uid=")]) > 4:
            # On single-server s4-all-components previously removed users
            # get resurrected. Try waiting some more for connector.
            time.sleep(30)
        self.check_new_and_removed_users(4, 0)  # check for new users in LDAP
        for person in person_list:
            person.verify()  # verify LDAP attributes

        self.log.info("*** Removing users...")
        self.create_csv_file(person_list=[], fn_csv=fn_csv, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.log.info("Adding remove hooks %r...", TESTHOOKTARGET)
        shutil.copy(TESTHOOKSOURCE, TESTHOOKTARGET)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        self.check_new_and_removed_users(0, 4)
        for person in person_list:
            person.set_mode_to_delete()  # mark person as removed
            person.verify()


if __name__ == "__main__":
    Test().run()
