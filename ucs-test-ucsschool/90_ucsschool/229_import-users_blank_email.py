#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test bahavior of import with and without email column/mapping/value
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [46317, 46462]

import copy

from ldap.filter import filter_format

import univention.testing.strings as uts
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def create_persons(self, *roles, **attrs):
        person_list = []
        for role in roles:
            person = Person(self.ou_A.name, role)
            person_attrs = copy.deepcopy(attrs)
            person_attrs["record_uid"] = person_attrs.get("record_uid") or uts.random_name()
            person_attrs["source_uid"] = (
                person_attrs.get("source_uid") or self.source_uid or uts.random_name()
            )
            person.update(**person_attrs)
            person_list.append(person)
        return person_list

    def import_and_verify(self, person_list, config):
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        for person in person_list:
            person.verify()

    def test(self):
        self.source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        # default_config contains: ("csv:mapping:E-Mail": "email")
        # and also: ("scheme:email", "<:umlauts><firstname>[0].<lastname>@<maildomain>")
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)
        config.update_entry("source_uid", self.source_uid)

        self.log.info(
            "*** 1.1.1 scheme and mapping and column filled, NEW users"
            " -> filled email addresses from column"
        )

        config.update_entry("csv:mapping:E-Mail", "email")
        config.update_entry("scheme:email", "<:umlauts><firstname>[0].<lastname>@<maildomain>")

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff")
        self.import_and_verify(person_list, config)

        self.log.info(
            "*** 1.1.2 scheme and mapping and column filled, SAME users with new email addresses"
            " -> new email addresses from column"
        )

        for person in person_list:
            person.update(mail="{}@{}".format(uts.random_name(), self.maildomain))
        self.import_and_verify(person_list, config)

        self.log.info(
            "*** 1.1.3 scheme and mapping and column empty, SAME users"
            " -> empty email addresses from column"
        )

        for person in person_list:
            person.update(mail="")
        self.import_and_verify(person_list, config)

        self.log.info(
            "*** 1.2.1 scheme and mapping and column empty, NEW users"
            " -> empty email addresses from column"
        )

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff", mail="")
        self.import_and_verify(person_list, config)

        self.log.info(
            "*** 1.2.2 scheme and mapping and column empty, SAME users"
            " -> empty email addresses from column"
        )
        self.import_and_verify(person_list, config)

        # not allowed anymore (Bug #47681):
        # self.log.info(
        # 	'*** 1.3.1 scheme and mapping and no column, NEW users (with email addresses in CSV)'
        # 	' -> filled email addresses from scheme')

        # not allowed anymore (Bug #47681):
        # self.log.info(
        # 	'*** 1.3.2 scheme and mapping and no column, SAME users (with email addresses in CSV)'
        # 	' -> email addresses unchanged from 1.3.1')

        self.log.info(
            "*** 1.3.3 scheme and mapping and column empty, SAME users"
            " -> empty email addresses from column"
        )

        for person in person_list:
            person.update(mail="")
        self.import_and_verify(person_list, config)

        self.log.info(
            "*** 2.1.1 scheme and no mapping and column filled, NEW users"
            " -> filled email addresses from scheme"
        )

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff")
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config_without_email_mapping = copy.deepcopy(config)
        del config_without_email_mapping["csv"]["mapping"]["E-Mail"]
        config_without_email_mapping.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config_without_email_mapping)
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        for person in person_list:
            person.update(mail="{}.{}@{}".format(person.firstname[0], person.lastname, self.maildomain))
            person.verify()

        self.log.info(
            "*** 2.1.2 scheme and no mapping and column filled, SAME users"
            " -> email addresses unchanged from 2.1.1"
        )

        # same import: same config and csv
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        for person in person_list:
            # mail already set in 2.1.1
            person.verify()

        self.log.info(
            "*** 2.2 scheme and no mapping and column empty, NEW users (with email addresses in CSV)"
            " -> filled email addresses from scheme"
        )

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff", mail="")
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config_without_email_mapping = copy.deepcopy(config)
        del config_without_email_mapping["csv"]["mapping"]["E-Mail"]
        config_without_email_mapping.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config_without_email_mapping)
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        for person in person_list:
            person.update(mail="{}.{}@{}".format(person.firstname[0], person.lastname, self.maildomain))
            person.verify()

        self.log.info(
            "*** 2.3 scheme and no mapping and no column, NEW users"
            " -> filled email addresses from scheme"
        )

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff")
        config_without_email_mapping = copy.deepcopy(config)
        del config_without_email_mapping["csv"]["mapping"]["E-Mail"]
        fn_csv = self.create_csv_file(
            person_list=person_list, mapping=config_without_email_mapping["csv"]["mapping"]
        )
        config_without_email_mapping.update_entry("input:filename", fn_csv)
        config_without_email_mapping.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config_without_email_mapping)
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        for person in person_list:
            person.update(mail="{}.{}@{}".format(person.firstname[0], person.lastname, self.maildomain))
            person.verify()

        self.log.info(
            "*** 3.1 no scheme and mapping and column filled, NEW users"
            " -> new email addresses from column"
        )

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff")
        config_without_email_scheme = copy.deepcopy(config)
        del config_without_email_scheme["scheme"]["email"]
        self.import_and_verify(person_list, config_without_email_scheme)

        self.log.info(
            "*** 3.2 no scheme and mapping and column empty, NEW users"
            " -> empty email addresses (from column)"
        )

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff", mail="")
        self.import_and_verify(person_list, config_without_email_scheme)

        # not allowed anymore (Bug #47681):
        # self.log.info(
        # 	'*** 3.3 no scheme and mapping and no column, NEW users'
        # 	' -> empty email addresses')

        self.log.info(
            "*** 4.1 no scheme and no mapping and column filled, NEW users" " -> empty email addresses"
        )

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff")
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config_without_email_scheme_and_mapping = copy.deepcopy(config)
        del config_without_email_scheme_and_mapping["scheme"]["email"]
        del config_without_email_scheme_and_mapping["csv"]["mapping"]["E-Mail"]
        config_without_email_scheme_and_mapping.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config_without_email_scheme_and_mapping)
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        for person in person_list:
            person.update(mail="")
            person.verify()

        self.log.info(
            "*** 4.2 no scheme and no mapping and column empty, NEW users" " -> empty email addresses"
        )

        person_list = self.create_persons("student", "teacher", "staff", "teacher_and_staff")
        for person in person_list:
            person.mail = ""
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        config_without_email_scheme_and_mapping.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config_without_email_scheme_and_mapping)
        self.run_import(["-c", fn_config])
        wait_for_drs_replication(filter_format("cn=%s", (person_list[-1].username,)))
        for person in person_list:
            person.verify()

        # not allowed anymore (Bug #47681):
        # self.log.info(
        # 	'*** 4.3 no scheme and no mapping and no column, NEW users'
        # 	' -> empty email addresses')


if __name__ == "__main__":
    Test().run()
