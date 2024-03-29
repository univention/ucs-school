#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test group creation (Bug 41907)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [441907]

from copy import deepcopy

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_C = None

    def test(self):  # formally test_modify_with_several_groups()
        """
        Bug #41907:
        for role in ('student', 'teacher', 'staff', 'teacher_and_staff'):
            - create user with 2 schools and 2 classes
            - add user to several groups for each school:
              - global group
              - workgroup
              - class
              - extra group 1 (random name <RANDOM>)
              - extra group 2 (same naming schema as workgroup/class <OU>-<NAME>)
            - modify user with role <role>
              - add user to new random class
              - remove user from class_B
            - remove user with role <role>
        """
        self.log.debug("*** Creating groups...")
        global_group_dn, global_group_name = self.udm.create_group()
        workgroup_A_dn, workgroup_A_name = self.udm.create_group(
            position="cn=schueler,cn=groups,%s" % (self.ou_A.dn,),
            name="{}-{}".format(self.ou_A.name, uts.random_groupname()),
            ucsschoolRole=[f"workgroup:school:{self.ou_A.name}"],
        )
        class_A_dn, class_A_name = self.udm.create_group(
            position="cn=klassen,cn=schueler,cn=groups,%s" % (self.ou_A.dn,),
            name="{}-{}".format(self.ou_A.name, uts.random_groupname()),
        )
        cn_A_dn = self.udm.create_object(
            "container/cn", position=self.ou_A.dn, name="kurs-%s" % uts.random_string()
        )
        extra_A_group1_dn, extra_A_group1_name = self.udm.create_group(position=cn_A_dn)
        extra_A_group2_dn, extra_A_group2_name = self.udm.create_group(
            position=cn_A_dn, name="{}-{}".format(self.ou_A.name, uts.random_groupname())
        )

        workgroup_B_dn, workgroup_B_name = self.udm.create_group(
            position="cn=schueler,cn=groups,%s" % (self.ou_B.dn,),
            name="{}-{}".format(self.ou_B.name, uts.random_groupname()),
            ucsschoolRole=[f"workgroup:school:{self.ou_B.name}"],
        )
        class_B_dn, class_B_name = self.udm.create_group(
            position="cn=klassen,cn=schueler,cn=groups,%s" % (self.ou_B.dn,),
            name="{}-{}".format(self.ou_B.name, uts.random_groupname()),
        )
        cn_B_dn = self.udm.create_object(
            "container/cn", position=self.ou_B.dn, name="kurs-%s" % uts.random_string()
        )
        extra_B_group1_dn, extra_B_group1_name = self.udm.create_group(position=cn_B_dn)
        extra_B_group2_dn, extra_B_group2_name = self.udm.create_group(
            position=cn_B_dn, name="{}-{}".format(self.ou_B.name, uts.random_groupname())
        )

        config = deepcopy(self.default_config)
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("user_role", None)

        self.log.info("*** Importing new users of each role...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            # create user that is member in multiple schools
            # sorted() because csv-mapping has no prim.OU -> import will use first OU, alpha.sorted
            person = Person(sorted([self.ou_A.name, self.ou_B.name])[0], role)
            person.update(
                schools=[self.ou_A.name, self.ou_B.name],
                record_uid=uts.random_name(),
                source_uid=source_uid,
            )
            if role in ("student", "teacher", "teacher_and_staff"):
                person.school_classes.setdefault(self.ou_A.name, []).append(class_A_name)
                person.school_classes.setdefault(self.ou_B.name, []).append(class_B_name)
                self.log.warning(
                    "person.username with class_A_name=%r : %r", class_A_name, person.username
                )
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config, "-i", fn_csv])
        self.check_new_and_removed_users(4, 0)

        # update dn+username of person and verify LDAP attributes
        for person in person_list:
            person.update_from_ldap(self.lo, ["dn", "username"])
            person.verify()
        self.log.warning(
            "[person.dn for person in person_list if person.role in (student, teacher, "
            "teacher_and_staff)]=%r",
            [
                person.dn
                for person in person_list
                if person.role in ("student", "teacher", "teacher_and_staff")
            ],
        )
        utils.verify_ldap_object(
            class_A_dn,
            expected_attr={
                "uniqueMember": [
                    person.dn
                    for person in person_list
                    if person.role in ("student", "teacher", "teacher_and_staff")
                ]
            },
            strict=True,
            should_exist=True,
        )
        utils.verify_ldap_object(
            class_B_dn,
            expected_attr={
                "uniqueMember": [
                    person.dn
                    for person in person_list
                    if person.role in ("student", "teacher", "teacher_and_staff")
                ]
            },
            strict=True,
            should_exist=True,
        )

        self.log.info("*** Adding users to groups...")
        # add user to working groups, extra groups in both schools and to global group
        self.udm.modify_object(
            "groups/group", dn=global_group_dn, append={"users": [person.dn for person in person_list]}
        )
        self.udm.modify_object(
            "groups/group", dn=workgroup_A_dn, append={"users": [person.dn for person in person_list]}
        )
        self.udm.modify_object(
            "groups/group", dn=workgroup_B_dn, append={"users": [person.dn for person in person_list]}
        )
        self.udm.modify_object(
            "groups/group", dn=extra_A_group1_dn, append={"users": [person.dn for person in person_list]}
        )
        self.udm.modify_object(
            "groups/group", dn=extra_A_group2_dn, append={"users": [person.dn for person in person_list]}
        )
        self.udm.modify_object(
            "groups/group", dn=extra_B_group1_dn, append={"users": [person.dn for person in person_list]}
        )
        self.udm.modify_object(
            "groups/group", dn=extra_B_group2_dn, append={"users": [person.dn for person in person_list]}
        )
        utils.verify_ldap_object(
            global_group_dn,
            expected_attr={"uniqueMember": [person.dn for person in person_list]},
            strict=False,
            should_exist=True,
        )
        utils.verify_ldap_object(
            workgroup_A_dn,
            expected_attr={"uniqueMember": [person.dn for person in person_list]},
            strict=False,
            should_exist=True,
        )
        utils.verify_ldap_object(
            extra_A_group1_dn,
            expected_attr={"uniqueMember": [person.dn for person in person_list]},
            strict=False,
            should_exist=True,
        )
        utils.verify_ldap_object(
            extra_A_group2_dn,
            expected_attr={"uniqueMember": [person.dn for person in person_list]},
            strict=False,
            should_exist=True,
        )
        utils.verify_ldap_object(
            workgroup_B_dn,
            expected_attr={"uniqueMember": [person.dn for person in person_list]},
            strict=False,
            should_exist=True,
        )
        utils.verify_ldap_object(
            extra_B_group1_dn,
            expected_attr={"uniqueMember": [person.dn for person in person_list]},
            strict=False,
            should_exist=True,
        )
        utils.verify_ldap_object(
            extra_B_group2_dn,
            expected_attr={"uniqueMember": [person.dn for person in person_list]},
            strict=False,
            should_exist=True,
        )

        self.log.info("*** Modifying users...")
        for person in person_list:
            person.school_classes = {}
            if person.role in ("student", "teacher", "teacher_and_staff"):
                person.append_random_class(schools=person.schools)
                person.school_classes.setdefault(self.ou_A.name, []).append(class_A_name)
        # user is removed from class_B!

        self.create_csv_file(person_list=person_list, fn_csv=fn_csv, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config, "-i", fn_csv])
        self.check_new_and_removed_users(0, 0)

        # verify LDAP attributes
        for person in person_list:
            person.verify()
            utils.verify_ldap_object(
                global_group_dn,
                expected_attr={"uniqueMember": [person.dn for person in person_list]},
                strict=False,
                should_exist=True,
            )
            utils.verify_ldap_object(
                workgroup_A_dn,
                expected_attr={"uniqueMember": [person.dn for person in person_list]},
                strict=False,
                should_exist=True,
            )
            utils.verify_ldap_object(
                extra_A_group1_dn,
                expected_attr={"uniqueMember": [person.dn for person in person_list]},
                strict=False,
                should_exist=True,
            )
            utils.verify_ldap_object(
                extra_A_group2_dn,
                expected_attr={"uniqueMember": [person.dn for person in person_list]},
                strict=False,
                should_exist=True,
            )
            utils.verify_ldap_object(
                workgroup_B_dn,
                expected_attr={"uniqueMember": [person.dn for person in person_list]},
                strict=False,
                should_exist=True,
            )
            utils.verify_ldap_object(
                extra_B_group1_dn,
                expected_attr={"uniqueMember": [person.dn for person in person_list]},
                strict=False,
                should_exist=True,
            )
            utils.verify_ldap_object(
                extra_B_group2_dn,
                expected_attr={"uniqueMember": [person.dn for person in person_list]},
                strict=False,
                should_exist=True,
            )
            if person.role in ("student", "teacher", "teacher_and_staff"):
                utils.verify_ldap_object(
                    class_A_dn,
                    expected_attr={
                        "uniqueMember": [
                            person.dn
                            for person in person_list
                            if person.role in ("student", "teacher", "teacher_and_staff")
                        ]
                    },
                    strict=False,
                    should_exist=True,
                )
                utils.verify_ldap_object(
                    class_B_dn, expected_attr={"uniqueMember": []}, strict=True, should_exist=True
                )

        self.log.info("*** Remove users...")
        for person in person_list:
            # mark person as removed
            person.set_mode_to_delete()

        self.create_csv_file(person_list=[], fn_csv=fn_csv, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config, "-i", fn_csv])
        self.check_new_and_removed_users(0, 4)

        # verify LDAP attributes
        for person in person_list:
            person.verify()


if __name__ == "__main__":
    Test().run()
