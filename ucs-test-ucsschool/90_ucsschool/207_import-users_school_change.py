#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test moving a user from ou_A to ou_B
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41609, 41910]
## timeout: 7200

import copy
import pprint

from ldap.filter import escape_filter_chars, filter_format

import univention.testing.strings as uts
from ucsschool.lib.models.group import SchoolClass, WorkGroup as LibWorkGroup
from ucsschool.lib.models.user import User
from univention.admin.uldap import explodeDn
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importou import get_school_base
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester
from univention.testing.ucsschool.workgroup import Workgroup


class PersonWithSchool(Person):
    def map_to_dict(self, value_map, prefix_schools=True):
        result = super(PersonWithSchool, self).map_to_dict(value_map, prefix_schools=prefix_schools)
        result[value_map.get("school", "__EMPTY__")] = self.school
        try:
            del result["__EMPTY__"]
        except KeyError:
            pass
        return result


class Test(CLI_Import_v2_Tester):
    ou_C = None

    def test(self):  # formally test_school_change()
        """Test moving a user from ou_A to ou_B (Bug #41609)."""
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:school", "school")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        self.log.info("*** school A=%r school B=%r" % (self.ou_A.name, self.ou_B.name))
        self.log.info("*** Importing a new users of each role and change school afterwards...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = PersonWithSchool(self.ou_A.name, role)
            person.update(record_uid=person.username, source_uid=source_uid, school_classes={})
            person.old_groups = None
            person_list.append(person)

        self.log.info("**** 1.1 create in school A (%r)", self.ou_A.name)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])
        for person in person_list:
            wait_for_drs_replication(filter_format("cn=%s", (person.username,)), base=self.ou_A.dn)
            self.log_person_infos(person)
            person.verify()
            self.verify_exact_schoolgroup_membership(person)

        self.log.info(
            "**** 1.2 move %r to school B (%r)", [p.username for p in person_list], self.ou_B.name
        )
        for person in person_list:
            person.old_groups = self.get_group_membership(person.dn)
            person.update(school=self.ou_B.name, schools=[self.ou_B.name])
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])
        for person in person_list:
            userlist = self.uid_to_dn(person.username)
            person.update(dn=userlist)
            wait_for_drs_replication(filter_format("cn=%s", (person.username,)), base=self.ou_B.dn)
            self.log_person_infos(person)
            current_groups = self.get_group_membership(person.dn)
            for grp_dn in current_groups:
                wait_for_drs_replication(escape_filter_chars(explodeDn(grp_dn)[0]))
            for grp_dn in set(person.old_groups) - set(current_groups):
                self.wait_for_drs_replication_of_membership(grp_dn, person.username, is_member=False)
            person.verify()
            self.verify_removed_schoolgroup_membership(person, self.ou_A.name)
            self.verify_exact_schoolgroup_membership(person)

        self.log.info(
            "**** 2.1 Add %r to a 2nd school (A) -> school=B (%r), schools=[A, B] (%r, %r)",
            [p.username for p in person_list],
            self.ou_B.name,
            self.ou_A.name,
            self.ou_B.name,
        )
        for person in person_list:
            person.update(school=self.ou_B.name, schools=[self.ou_A.name, self.ou_B.name])
            if person.role in ("student", "teacher", "teacher_and_staff"):
                self.log.info("**** 2.1.1 Creating a school_class for %s...", person.role)
                class_A_dn, class_A_name = self.udm.create_group(
                    position=SchoolClass.get_container(self.ou_A.name),
                    name="{}-{}".format(self.ou_A.name, uts.random_groupname()),
                )
                person.school_classes.setdefault(self.ou_A.name, []).append(class_A_name)
            else:
                self.log.info("**** 2.1.1 No school_class for %s...", person.role)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])
        for person in person_list:
            wait_for_drs_replication(filter_format("cn=%s", (person.username,)))
            current_groups = self.get_group_membership(person.dn)
            for grp_dn in current_groups:
                wait_for_drs_replication(escape_filter_chars(explodeDn(grp_dn)[0]))
            self.log_person_infos(person)
            person.verify()
            self.verify_exact_schoolgroup_membership(person)

        for person in person_list:
            self.log.info(
                "**** 2.1.2 Add %r %r to a workgroup in 2nd school (A) (%r)",
                person.role,
                person.username,
                self.ou_A.name,
            )
            wg = Workgroup(self.ou_A.name, ucr=self.ucr, members=[person.dn])
            wg.create()
            wg.verify_ldap_attributes()
            self.log_person_infos(person)
            self.wait_for_drs_replication_of_membership(wg.dn(), person.username)
            self.verify_exact_schoolgroup_membership(person)

        for person in person_list:
            self.log.info(
                "**** 2.2 Remove %r %r from 2nd school (A) -> school=B (%r), schools=[B] (%r)",
                person.role,
                person.username,
                self.ou_B.name,
                self.ou_B.name,
            )
            person.old_groups = self.get_group_membership(person.dn)
            person.update(school=self.ou_B.name, schools=[self.ou_B.name])
            if person.role in ("student", "teacher", "teacher_and_staff"):
                person.school_classes.pop(self.ou_A.name, [])
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])
        for person in person_list:
            wait_for_drs_replication(filter_format("cn=%s", (person.username,)))
            current_groups = self.get_group_membership(person.dn)
            for grp_dn in current_groups:
                wait_for_drs_replication(escape_filter_chars(explodeDn(grp_dn)[0]))
            for grp_dn in set(person.old_groups) - set(current_groups):
                self.wait_for_drs_replication_of_membership(grp_dn, person.username, is_member=False)
            self.log_person_infos(person)
            person.verify()
            self.verify_removed_schoolgroup_membership(person, self.ou_A.name)
            self.verify_exact_schoolgroup_membership(person)

        for person in person_list:
            self.log.info(
                "**** 3.1 (Re)Add %r %r to 2nd school (A) -> school=B (%r), schools=[A, B] (%r, %r)",
                person.role,
                person.username,
                self.ou_B.name,
                self.ou_A.name,
                self.ou_B.name,
            )
            person.update(school=self.ou_B.name, schools=[self.ou_A.name, self.ou_B.name])
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])
        for person in person_list:
            wait_for_drs_replication(filter_format("cn=%s", (person.username,)))
            current_groups = self.get_group_membership(person.dn)
            for grp_dn in current_groups:
                wait_for_drs_replication(escape_filter_chars(explodeDn(grp_dn)[0]))
            self.log_person_infos(person)
            person.verify()
            self.verify_exact_schoolgroup_membership(person)

        for person in person_list:
            self.log.info(
                "**** 3.2 remove %r %r from primary school (B) -> school=A (%r), schools=[A] (%r)",
                person.role,
                person.username,
                self.ou_A.name,
                self.ou_A.name,
            )
            person.old_groups = self.get_group_membership(person.dn)
            person.update(school=self.ou_A.name, schools=[self.ou_A.name])
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])
        for person in person_list:
            person.update(dn=self.uid_to_dn(person.username))
            wait_for_drs_replication(filter_format("cn=%s", (person.username,)), base=self.ou_A.dn)
            current_groups = self.get_group_membership(person.dn)
            for grp_dn in current_groups:
                wait_for_drs_replication(escape_filter_chars(explodeDn(grp_dn)[0]))
            for grp_dn in set(person.old_groups) - set(current_groups):
                self.wait_for_drs_replication_of_membership(grp_dn, person.username, is_member=False)
            self.log_person_infos(person)
            person.verify()
            self.verify_removed_schoolgroup_membership(person, self.ou_B.name)
            self.verify_exact_schoolgroup_membership(person)

    def get_group_membership(self, dn):
        return self.lo.searchDn(filter_format("uniqueMember=%s", (dn,)))

    def uid_to_dn(self, uid):
        userlist = self.lo.searchDn(filter_format("uid=%s", (uid,)))
        if len(userlist) != 1:
            self.fail(
                "Invalid number of user objects for uid %r! Found new objects: %r" % (uid, userlist)
            )
        return userlist[0]

    def log_person_infos(self, person):
        self.log.warning(
            "User object %r:\n%s", person.dn, pprint.pformat(self.lo.get(person.dn), indent=2)
        )
        self.log.info("Membership: %s", pprint.pformat(self.get_group_membership(person.dn), indent=2))

    def verify_removed_schoolgroup_membership(self, person, school_removed_from):
        groups = self.get_group_membership(person.dn)
        ou_dn = get_school_base(school_removed_from)
        if any(g.endswith(ou_dn) for g in groups):
            self.fail("User still has groups from OU %r: %r" % (school_removed_from, groups))
        else:
            self.log.info("*** OK: User is in no groups from school %r anymore.", school_removed_from)

    def verify_exact_schoolgroup_membership(self, person):
        user = User.from_dn(person.dn, person.school, self.lo)
        expected_groups = {g.lower() for g in user.get_specific_groups(self.lo)}
        for school in person.schools:
            workgroups = LibWorkGroup.get_all(
                self.lo, school, filter_format("uniqueMember=%s", (person.dn,))
            )
            expected_groups.update({wg.dn.lower() for wg in workgroups})
        membership = {g.lower() for g in self.get_group_membership(person.dn)}
        if expected_groups != membership:
            self.fail(
                "Group membership not like expected:\nexpected groups=%r\nfound membership=%r"
                % (expected_groups, membership)
            )
        else:
            self.log.info("*** OK: Users group membership is as expected.")


if __name__ == "__main__":
    Test().run()
