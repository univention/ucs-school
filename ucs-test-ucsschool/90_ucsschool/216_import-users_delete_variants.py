#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: support deletion of users in different ways
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41344, 42913, 45467]

import copy
import datetime
import random
import time

from ldap.filter import filter_format

import univention.admin.uldap
import univention.testing.strings as uts
from ucsschool.lib.models.user import User
from univention.admin.uexceptions import authFail
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester
from univention.testing.ucsschool.ucs_test_school import udm_formula_for_shadowExpire


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formally test_delete_variants()
        """
        Bug #41344: support deletion of users in different ways
        Bug #45467: user deletion rewritten

        * simply delete: deletion_grace_period={"deactivation": X, "deletion": 0}
        * delete later, deactivate now: deletion_grace_period={"deactivation": 0, "deletion": Y}
          + creating a user with the deactived users SUID+RUID -> reactivate account
        * delete later, deactivate with an expiration date: deletion_grace_period={"deactivation":
            Z, "deletion": Z+1}
        """
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("csv:mapping:override_pw_history", "overridePWHistory")
        config.update_entry("user_role", None)

        self.log.info("*** 1/3: delete immediately ***")
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config.update_entry("source_uid", source_uid)
        # deletion_grace_period:deactivation should not matter if deletion_grace_period:deletion=0
        exp_days = random.randint(1, 20)
        config.update_entry("deletion_grace_period:deactivation", exp_days)
        config.update_entry("deletion_grace_period:deletion", 0)
        self.log.info("*** (1/3) Importing a new single user of each role...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(
                record_uid="record_uid-{}".format(uts.random_string()),
                source_uid=source_uid,
                override_pw_history="1",
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

        self.log.info("*** (1/3) Removing users...")
        self.create_csv_file(person_list=[], fn_csv=fn_csv, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(0, 4)
        for person in person_list:
            person.set_mode_to_delete()  # mark person as removed
            person.verify()

        self.log.info("*** 2/3: delete later, deactivate now ***")
        exp_days = random.randint(1, 20)
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:password", "password")
        config.update_entry("csv:mapping:override_pw_history", "overridePWHistory")
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)
        config.update_entry("deletion_grace_period:deactivation", 0)
        config.update_entry("deletion_grace_period:deletion", exp_days)
        self.log.info("*** (2/3) Importing users of all roles...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(
                record_uid="record_uid-{}".format(uts.random_string()),
                source_uid=source_uid,
                password=uts.random_string(20),
                override_pw_history="1",
            )
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()  # save ldap state for later comparison
        self.run_import(["-c", fn_config])  # start import
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        self.check_new_and_removed_users(4, 0)  # check for new users in LDAP
        for person in person_list:
            person.verify()  # verify LDAP attributes

            # Bug #42913: check if LDAP bind is possible
            try:
                univention.admin.uldap.access(binddn=person.dn, bindpw=person.password)
                self.log.info("OK: user can bind to LDAP server.")
            except authFail:
                self.fail(
                    "User could not bind to LDAP server with binddn={!r} bindpw={!r}".format(
                        person.dn, person.password
                    )
                )

        self.log.info("*** (2/3) Removing users...")
        self.create_csv_file(person_list=[], fn_csv=fn_csv, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.log.info("Sleeping 60s for s4 sync...")
        time.sleep(60)
        for person in person_list:
            wait_for_drs_replication(filter_format("cn=%s", (person.username,)))
        self.check_new_and_removed_users(0, 0)
        # check exp. date
        exp_date = (datetime.datetime.now() + datetime.timedelta(days=exp_days)).strftime("%Y-%m-%d")
        ldap_exp_date = self.pugre_timestamp_udm2ldap(exp_date)
        self.log.debug("Account deletion timestamp should be %r -> %r.", exp_date, ldap_exp_date)
        for person in person_list:
            person.set_inactive()  # mark person as disabled
            utils.verify_ldap_object(
                person.dn,
                expected_attr={
                    # DISABLED DUE TO BUG #41574
                    # "shadowExpire": [udm_value],
                    "krb5KDCFlags": ["254"],
                    "sambaAcctFlags": ["[UD         ]"],
                    "ucsschoolPurgeTimestamp": [ldap_exp_date],
                },
                strict=False,
                should_exist=True,
            )

            # Bug #42913: check if LDAP bind is still possible
            try:
                univention.admin.uldap.access(binddn=person.dn, bindpw=person.password)
                udm_user = User.from_dn(person.dn, None, self.lo).get_udm_object(self.lo)
                self.log.error("disabled: %r", udm_user.get("disabled"))
                self.log.error("locked: %r", udm_user.get("locked"))
                self.log.error("userexpiry: %r", udm_user.get("userexpiry"))
                self.log.error("ucsschoolPurgeTimestamp: %r", udm_user.get("ucsschoolPurgeTimestamp"))
                # Bug #24185: Konto-Deaktivierung wird beim Setzen des Konto-Ablaufdatum falsch gesetzt
                self.log.error("Deactivated user can still bind to LDAP server.")
                self.log.error("Continuing despite error (Bug #24185)...")
            # self.fail('Deactivated user can still bind to LDAP server.')
            except authFail:
                self.log.info("OK: user cannot bind to LDAP server anymore.")

        self.log.info('*** (2/3) Reactivating previously "deleted" users...')
        for person in person_list:
            person.set_active()
        self.create_csv_file(person_list=person_list, fn_csv=fn_csv, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        self.check_new_and_removed_users(0, 0)
        for person in person_list:
            person.verify()
            utils.verify_ldap_object(
                person.dn,
                expected_attr={
                    "shadowExpire": [],
                    "krb5KDCFlags": ["126"],
                    "sambaAcctFlags": ["[U          ]"],
                    "ucsschoolPurgeTimestamp": [],
                },
                strict=False,
                should_exist=True,
            )

        self.log.info("*** 3/3: delete later, deactivate with an expiration date ***")
        self.log.info("*** (3/3) Importing user of each role...")
        exp_days = random.randint(1, 20)
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:override_pw_history", "overridePWHistory")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)
        config.update_entry("deletion_grace_period:deactivation", exp_days)
        config.update_entry("deletion_grace_period:deletion", exp_days + 1)
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(
                record_uid="record_uid-{}".format(uts.random_string()),
                source_uid=source_uid,
                override_pw_history="1",
            )
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()  # save ldap state for later comparison
        self.run_import(["-c", fn_config])  # start import
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        self.check_new_and_removed_users(4, 0)  # check for new users in LDAP
        for person in person_list:
            person.verify()  # verify LDAP attributes

        self.log.info("*** (3/3) Removing users...")
        self.create_csv_file(person_list=[], fn_csv=fn_csv, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        self.check_new_and_removed_users(0, 0)
        # check exp. date
        exp_date = (datetime.datetime.now() + datetime.timedelta(days=exp_days)).strftime("%Y-%m-%d")
        purge_date = (datetime.datetime.now() + datetime.timedelta(days=exp_days + 1)).strftime(
            "%Y-%m-%d"
        )
        ldap_purge_date = self.pugre_timestamp_udm2ldap(purge_date)
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                expected_attr={
                    "shadowExpire": [udm_formula_for_shadowExpire(exp_date)],
                    "krb5KDCFlags": ["126"],
                    "sambaAcctFlags": ["[U          ]"],
                    "ucsschoolPurgeTimestamp": [ldap_purge_date],
                },
                strict=False,
                should_exist=True,
            )


if __name__ == "__main__":
    Test().run()
