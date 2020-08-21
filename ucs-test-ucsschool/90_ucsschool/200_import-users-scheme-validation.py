#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Basic scheme tests importing users via CLI v2
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [51545]

import copy

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException


class Test(CLI_Import_v2_Tester):
    def __init__(self):
        super(Test, self).__init__()
        self.ou_B = None
        self.ou_C = None

    def verify_correct_config(self, config, source_uid):
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            person.update(source_uid=source_uid, username=None)
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config, "-i", fn_csv, "--dry-run"])

    def test(self):
        ctr_mode = "COUNTER2"
        user_scheme = "<:umlauts>user-<firstname>[0:2].<lastname>[0:2]-[{}]".format(ctr_mode)
        default_config = copy.deepcopy(self.default_config)
        default_config.update_entry("csv:mapping:role", "__role")
        default_config.update_entry("user_role", None)
        source_uid = "source_uid-%s" % (uts.random_string(),)
        default_config.update_entry("source_uid", source_uid)

        for scheme_role in [
            "default",
            "staff",
            "student",
            "teacher",
            "teacher_and_staff",
        ]:
            self.log.info("*** Test allowed scheme:username:{} : {}".format(scheme_role, user_scheme))
            config = copy.deepcopy(default_config)
            config.update_entry(
                "scheme:username:{}".format(scheme_role), user_scheme,
            )
            self.verify_correct_config(config, source_uid)

        for scheme_value in [
            123,
            (uts.random_string(), user_scheme),
            [uts.random_string(), user_scheme],
        ]:
            self.log.info("*** Test disallowed scheme:username:default : {}".format(scheme_value))
            config = copy.deepcopy(default_config)
            config.update_entry(
                "scheme:username:default", scheme_value,
            )
            try:
                self.verify_correct_config(config, source_uid)
                self.fail(
                    "No error reported for bad 'scheme:username:default' value {!r}.".format(
                        scheme_value
                    )
                )
            except ImportException:
                pass

        self.log.info("*** Test disallowed scheme:username : {}".format(user_scheme))
        config = copy.deepcopy(default_config)
        config["scheme"]["username"] = user_scheme
        try:
            self.verify_correct_config(config, source_uid)
            self.fail("No error reported for bad 'scheme:username' value {!r}.".format(scheme_value))
        except ImportException:
            pass

        self.log.info("*** Test disallowed scheme:username:allow_rename : True")
        config = copy.deepcopy(default_config)
        config.update_entry("scheme:username:allow_rename", "True")
        try:
            self.verify_correct_config(config, source_uid)
            self.fail("No error reported for disallowed 'scheme:username:allow_rename'.")
        except ImportException:
            pass

        for udm_value in [
            "email",
            "firstname",
            "lastname",
            "description",
            "displayName",
            "employeeNumber",
            "record_uid",
        ]:
            self.log.info("*** Test allowed scheme:{} : {}".format(udm_value, user_scheme))
            config = copy.deepcopy(default_config)
            config.update_entry(
                "scheme:{}".format(udm_value), user_scheme,
            )
            self.verify_correct_config(config, source_uid)
            self.log.info(
                "*** Test disallowed scheme:{} : {}".format(udm_value, {"default": user_scheme})
            )
            config = copy.deepcopy(default_config)
            config["scheme"][udm_value] = {"default": user_scheme}
            if udm_value in config["csv"]["mapping"].values():
                for key, value in config["csv"]["mapping"].items():
                    if value == udm_value:
                        del config["csv"]["mapping"][key]
                        break
            try:
                self.verify_correct_config(config, source_uid)
                self.fail(
                    "No error reported for disallowed 'scheme:{}': {!r}.".format(
                        udm_value, {"default": user_scheme}
                    )
                )
            except ImportException:
                pass


if __name__ == "__main__":
    Test().run()
