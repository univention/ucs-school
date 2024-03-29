#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test if in dry-run pyhooks with dry-run support run and those without don't
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [45715]

import copy
import os
import os.path

from ldap.filter import escape_filter_chars

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester

TESTHOOKSOURCE = os.path.join(os.path.dirname(__file__), "test235_hook_dryrun_support.pyhook")
TESTHOOKTARGETWITHSUPPORT = "/usr/share/ucs-school-import/pyhooks/test235_with_dryrun_support.py"
TESTHOOKTARGETWITHOUTSUPPORT = "/usr/share/ucs-school-import/pyhooks/test235_without_dryrun_support.py"
LOG_PATH_WITH_SUPPORT = "/tmp/test235_HookSupportsDryRun"
LOG_PATH_WITHOUT_SUPPORT = "/tmp/test235_HookNoDryRun"


class Test(CLI_Import_v2_Tester):
    ou_C = None

    def pyhook_cleanup(self):
        for ext in ["", "c", "o"]:
            for target in (TESTHOOKTARGETWITHSUPPORT, TESTHOOKTARGETWITHOUTSUPPORT):
                path = "{}{}".format(target, ext)
                try:
                    os.remove(path)
                    self.log.info("*** Deleted %s.", path)
                except OSError:
                    self.log.warning("*** Could not delete %s.", path)

    def cleanup(self):
        self.pyhook_cleanup()
        self.purge_hook_logs()
        self.remove_log_dirs()
        super(Test, self).cleanup()

    def create_pyhooks(self):
        with open(TESTHOOKSOURCE, "rb") as fp:
            text = fp.read()
        self.log.info("*** Creating PyHook with dry-run support (%r)...", TESTHOOKTARGETWITHSUPPORT)
        with open(TESTHOOKTARGETWITHSUPPORT, "wb") as fp:
            fp.write(
                text.replace(b"%CLASSNAME%", b"HookSupportsDryRun").replace(
                    b"%DRYRUNSUPPORT%", b"supports_dry_run = True"
                )
            )
        self.log.info(
            "*** Creating PyHook without dry-run support (%r)...", TESTHOOKTARGETWITHOUTSUPPORT
        )
        with open(TESTHOOKTARGETWITHOUTSUPPORT, "wb") as fp:
            fp.write(text.replace(b"%CLASSNAME%", b"HookNoDryRun").replace(b"%DRYRUNSUPPORT%", b""))

    @staticmethod
    def get_path(has_support, dry_run, hook_name):
        if has_support:
            base_path = LOG_PATH_WITH_SUPPORT
        else:
            base_path = LOG_PATH_WITHOUT_SUPPORT
        return os.path.join(base_path, "dryrun" if dry_run else "real", hook_name)

    @classmethod
    def get_log_dirs(cls):
        return [
            cls.get_path(True, True, "").rstrip("/"),
            cls.get_path(True, False, "").rstrip("/"),
            cls.get_path(False, True, "").rstrip("/"),
            cls.get_path(False, False, "").rstrip("/"),
        ]

    def create_log_dirs(self):
        for log_dir in self.get_log_dirs():
            parent_path = os.path.dirname(log_dir)  # one level up is enough
            if not os.path.exists(parent_path):
                os.mkdir(parent_path)
                self.log.info("*** Created diretory %s.", parent_path)
            os.mkdir(log_dir)
            self.log.info("*** Created diretory %s.", log_dir)

    def remove_log_dirs(self):
        for log_dir in self.get_log_dirs():
            try:
                os.rmdir(log_dir)
                self.log.info("*** Deleted %s.", log_dir)
            except OSError:
                self.log.warning("*** Could not delete %s.", log_dir)
            parent_path = os.path.dirname(log_dir)
            try:
                os.rmdir(parent_path)
                self.log.info("*** Deleted %s.", parent_path)
            except OSError:
                self.log.warning("*** Could not delete %s.", parent_path)

    def check_hook_log_exists(self, with_support, no_support, dry_run, hooks_expected_to_run):
        for hook_expected_to_run in hooks_expected_to_run:
            # check HookSupportsDryRun
            path = self.get_path(True, dry_run, hook_expected_to_run)
            if with_support:
                assert os.path.exists(path)
            else:
                assert not os.path.exists(path)
            # check HookNoDryRun
            path = self.get_path(False, dry_run, hook_expected_to_run)
            if no_support:
                assert os.path.exists(path)
            else:
                assert not os.path.exists(path)

    def purge_hook_logs(self):
        for log_dir in self.get_log_dirs():
            try:
                for f in os.listdir(log_dir):
                    file_path = os.path.join(log_dir, f)
                    os.remove(file_path)
                    self.log.info("*** Deleted %s.", file_path)
            except OSError:
                self.log.warning("*** Could not delete file(s) in %s.", log_dir)

    def test(self):
        source_uid = "source_uid-{}".format(uts.random_string())
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:birthday", "birthday")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        self.create_log_dirs()
        self.create_pyhooks()

        self.log.info("*** 1/8 Importing a user from each role (create), with dry-run...")
        config.update_entry("dry_run", True)
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        for person in person_list:
            utils.verify_ldap_object(person.dn, should_exist=False)
        self.check_hook_log_exists(
            with_support=True,
            no_support=False,
            dry_run=True,
            hooks_expected_to_run=("pre_create", "post_create"),
        )
        self.purge_hook_logs()

        self.log.info("*** 2/8 Importing a user from each role (create), without dry-run (real run)...")
        config.update_entry("dry_run", False)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            utils.verify_ldap_object(person.dn, should_exist=True)
        self.check_hook_log_exists(
            with_support=True,
            no_support=True,
            dry_run=False,
            hooks_expected_to_run=("pre_create", "post_create"),
        )
        self.purge_hook_logs()

        self.log.info("*** 3/8 Importing a user from each role (modify), with dry-run...")
        config.update_entry("dry_run", True)
        for person in person_list:
            person.set_random_birthday()
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                should_exist=True,
                expected_attr={"univentionBirthday": ""},  # make sure it was a dry-run
            )
        self.check_hook_log_exists(
            with_support=True,
            no_support=False,
            dry_run=True,
            hooks_expected_to_run=("pre_modify", "post_modify"),
        )
        self.purge_hook_logs()

        self.log.info("*** 4/8 Importing a user from each role (modify), without dry-run (real run)...")
        config.update_entry("dry_run", False)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                should_exist=True,
                expected_attr={"univentionBirthday": [person.birthday]},  # make sure it was a real run
            )
        self.check_hook_log_exists(
            with_support=True,
            no_support=True,
            dry_run=False,
            hooks_expected_to_run=("pre_modify", "post_modify"),
        )
        self.purge_hook_logs()

        self.log.info("*** 5/8 Importing a user from each role (move), with dry-run...")
        config.update_entry("dry_run", True)
        for person in person_list:
            person.update(school=self.ou_B.name)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            person.update(school=self.ou_A.name)  # dry-run did'nt change LDAP, check needs old value
            utils.verify_ldap_object(person.dn, should_exist=True)
        self.check_hook_log_exists(
            with_support=True,
            no_support=False,
            dry_run=True,
            hooks_expected_to_run=("pre_move", "post_move"),
        )
        self.purge_hook_logs()

        self.log.info("*** 6/8 Importing a user from each role (move), without dry-run (real run)...")
        config.update_entry("dry_run", False)
        # CSV still contains school=ou_B.name
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            person.update(school=self.ou_B.name)  # this time it must have changed
            utils.verify_ldap_object(person.dn, should_exist=True)
        self.check_hook_log_exists(
            with_support=True,
            no_support=True,
            dry_run=False,
            hooks_expected_to_run=("pre_move", "post_move"),
        )
        self.purge_hook_logs()

        self.log.info("*** 7/8 Importing a user from each role (remove), with dry-run...")
        config.update_entry("dry_run", True)
        fn_csv = self.create_csv_file(person_list=[], mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            utils.verify_ldap_object(
                person.dn,
                should_exist=True,  # dry-run did'nt change LDAP, user must still exist
            )
        self.check_hook_log_exists(
            with_support=True,
            no_support=False,
            dry_run=True,
            hooks_expected_to_run=("pre_remove", "post_remove"),
        )
        self.purge_hook_logs()

        self.log.info("*** 8/8 Importing a user from each role (move), without dry-run (real run)...")
        config.update_entry("dry_run", False)
        fn_config = self.create_config_json(values=config)
        self.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[-1].username)))
        for person in person_list:
            utils.verify_ldap_object(person.dn, should_exist=False)  # this time users were removed
        self.check_hook_log_exists(
            with_support=True,
            no_support=True,
            dry_run=False,
            hooks_expected_to_run=("pre_remove", "post_remove"),
        )
        self.purge_hook_logs()


if __name__ == "__main__":
    Test().run()
