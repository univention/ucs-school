#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Check SingleSourcePartialUserImport scenario, classes are not prefixed with school names
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [47447]

import copy
import random

from ldap.filter import escape_filter_chars

import univention.testing.strings as uts
from ucsschool.lib.models.group import SchoolClass
from univention.testing.ucs_samba import wait_for_drs_replication, wait_for_s4connector
from univention.testing.ucsschool.importusers import NonPrefixPerson
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    def _import_and_verify(self, config, person, delete=False):
        person_list = [] if delete else [person]
        fn_config = self.create_config_json(config=config)

        fn_csv = self.create_csv_file(
            person_list=person_list,
            mapping=config["csv"]["mapping"],
            sisopi_school=config["school"],
            prefix_schools=False,
        )
        self.run_import(["-c", fn_config, "-i", fn_csv])
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person.username)))
        # wait for the connector to do its job, wait_for_drs_replication just checks if dn exists
        # school import stops the u-d-n so all modifications are delayed and we have to wait
        # at this point, to not disturb the next test
        wait_for_s4connector()
        person.verify()
        schools = self.lo.get(person.dn, attr=["ucsschoolSchool"])["ucsschoolSchool"]
        self.log.info("User is in ou=%r and has schools=%r.", person.school, schools)
        if person.school == self.limbo_ou_name:
            assert schools == [self.limbo_ou_name.encode("UTF-8")]
            group_dns = self.lo.searchDn(
                "(&(objectClass=univentionGroup)(uniqueMember={}))".format(person.dn)
            )
            self.log.debug("Groups of user: %r", group_dns)
            assert all(dn.endswith(self.limbo_ou_dn) for dn in group_dns), (group_dns, self.limbo_ou_dn)

    def test(self):
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:birthday", "birthday")
        config.update_entry(
            "classes:user_importer",
            "ucsschool.importer.mass_import.sisopi_user_import.SingleSourcePartialUserImport",
        )
        config.update_entry("configuration_checks", ["defaults", "sisopi"])
        config.update_entry("deletion_grace_period:deactivation", 0)
        config.update_entry("deletion_grace_period:deletion", 90)
        del config["csv"]["mapping"]["OUs"]

        self.limbo_ou_name, self.limbo_ou_dn = self.schoolenv.create_ou(
            "limbotestou{}".format(random.randint(1000, 9999)),
            name_edudc=self.ucr.get("hostname"),
            use_cache=False,
        )
        config.update_entry("limbo_ou", self.limbo_ou_name)
        self.log.info("*** Created limbo OU %r.", self.limbo_ou_name)

        class_A_dn, class_A_name = self.udm.create_group(
            position=SchoolClass.get_container(self.ou_A.name),
            name="{}-{}".format(self.ou_A.name, uts.random_groupname()),
        )
        class_B_dn, class_B_name = self.udm.create_group(
            position=SchoolClass.get_container(self.ou_B.name),
            name="{}-{}".format(self.ou_B.name, uts.random_groupname()),
        )
        class_C_dn, class_C_name = self.udm.create_group(
            position=SchoolClass.get_container(self.ou_C.name),
            name="{}-{}".format(self.ou_C.name, uts.random_groupname()),
        )

        for num, role in enumerate(("student", "staff", "teacher", "teacher_and_staff"), start=1):
            config.update_entry("user_role", role)

            self.log.info(
                "*** (%d/4) - 1. Importing (create) %r in school %r...", num, role, self.ou_A.name
            )
            config.update_entry("school", self.ou_A.name)
            person = NonPrefixPerson(self.ou_A.name, role)
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            if role != "staff":
                person.update(school_classes={self.ou_A.name: [class_A_name]})
            self._import_and_verify(config, person)
            self.log.info("OK: create (A) succeeded.")

            self.log.info(
                "*** (%d/4) - 2. Importing (add OU) %r in school %r...", num, role, self.ou_B.name
            )
            config.update_entry("school", self.ou_B.name)
            person.update(school=self.ou_A.name, schools=[self.ou_A.name, self.ou_B.name])
            if role != "staff":
                person.update(
                    school_classes={self.ou_A.name: [class_A_name], self.ou_B.name: [class_B_name]}
                )
            self._import_and_verify(config, person)
            self.log.info("OK: create (A -> A+B) succeeded.")

            self.log.info(
                "*** (%d/4) - 3. Importing (modify) %r in school %r...", num, role, self.ou_B.name
            )
            config.update_entry("school", self.ou_B.name)
            person.set_random_birthday()
            self._import_and_verify(config, person)
            self.log.info("OK: modification (A+B -> A+B) succeeded.")

            self.log.info(
                "***  (%d/4) - 4. Importing (add OU) %r in school %r...", num, role, self.ou_C.name
            )
            config.update_entry("school", self.ou_C.name)
            person.update(
                school=self.ou_A.name, schools=[self.ou_A.name, self.ou_B.name, self.ou_C.name]
            )
            if role != "staff":
                person.update(
                    school_classes={
                        self.ou_A.name: [class_A_name],
                        self.ou_B.name: [class_B_name],
                        self.ou_C.name: [class_C_name],
                    }
                )
            self._import_and_verify(config, person)
            self.log.info("OK: create (A+B -> A+B+C) succeeded.")

            self.log.info(
                "*** (%d/4) - 5. Importing (modify) %r in school %r...", num, role, self.ou_A.name
            )
            config.update_entry("school", self.ou_A.name)
            person.set_random_birthday()
            self._import_and_verify(config, person)
            self.log.info("OK: modification (A+B+C -> A+B+C) succeeded.")

            self.log.info(
                "***  (%d/4) - 6. Deleting (del OU) %r in school %r...", num, role, self.ou_B.name
            )
            config.update_entry("school", self.ou_B.name)
            person.update(school=self.ou_A.name, schools=[self.ou_A.name, self.ou_C.name])
            if role != "staff":
                person.update(
                    school_classes={self.ou_A.name: [class_A_name], self.ou_C.name: [class_C_name]}
                )
            self._import_and_verify(config, person, delete=True)
            self.log.info("OK: deletion (A+B+C -> A+C) succeeded.")

            self.log.info(
                "***  (%d/4) - 7. Deleting (del OU) %r in school %r...", num, role, self.ou_A.name
            )
            config.update_entry("school", self.ou_A.name)
            person.update(school=self.ou_C.name, schools=[self.ou_C.name], school_classes={})
            if role != "staff":
                person.update(school_classes={self.ou_C.name: [class_C_name]})
            self._import_and_verify(config, person, delete=True)
            self.log.info("OK: deletion (A+C -> C) succeeded.")

            self.log.info(
                "***  (%d/4) - 8. Deleting (move) %r in (last) school %r...", num, role, self.ou_C.name
            )
            config.update_entry("school", self.ou_C.name)
            person.update(school=self.limbo_ou_name, schools=[self.limbo_ou_name])
            person.update(school=self.limbo_ou_name, schools=[self.limbo_ou_name], school_classes={})
            person.set_inactive()
            self._import_and_verify(config, person, delete=True)
            self.log.info("OK: deletion (C -> limbo) succeeded.")

            self.log.info(
                "*** (%d/4) - 9. Importing (move) %r in school %r...", num, role, self.ou_B.name
            )
            config.update_entry("school", self.ou_B.name)
            person.update(school=self.ou_B.name, schools=[self.ou_B.name])
            person.set_active()
            person.append_random_groups()
            self._import_and_verify(config, person)
            self.log.info("OK: reactivate (limbo -> B) succeeded.")

            self.log.info(
                "***  (%d/4) - 10. Deleting (move) %r in (last) school %r...", num, role, self.ou_B.name
            )
            config.update_entry("school", self.ou_B.name)
            person.update(school=self.limbo_ou_name, schools=[self.limbo_ou_name], school_classes={})
            person.set_inactive()
            self._import_and_verify(config, person, delete=True)
            self.log.info("OK: deletion (B -> limbo) succeeded.")


if __name__ == "__main__":
    Test().run()
