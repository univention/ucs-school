#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Basic tests importing users via CLI v2, classes are not prefixed with school names
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [46970]

from copy import deepcopy

from ldap.filter import filter_format

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import NonPrefixPerson
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formerly test_create_modify_delete_user()
        """
        for role in ('student', 'teacher', 'staff', 'teacher_and_staff'):
            import user with role <role>
            modify user with role <role> → changing group memberships
            remove user with role <role>
        """
        self.log.info("*** Import a new user of each role...")

        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = deepcopy(self.default_config)
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = NonPrefixPerson(self.ou_A.name, role)
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            person_list.append(person)

        # Bug #46970: test stripping whitespace
        person.firstname = "{} ".format(person.firstname)
        person.lastname = " {}".format(person.lastname)

        fn_csv = self.create_csv_file(
            person_list=person_list, mapping=config["csv"]["mapping"], prefix_schools=False
        )
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(values=config)
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(4, 0)

        filter_src = filter_format("(objectClass=ucsschoolType)(ucsschoolSourceUID=%s)", (source_uid,))
        for person in person_list:
            filter_s = "(&{}{})".format(
                filter_src, filter_format("(ucsschoolRecordUID=%s)", (person.record_uid,))
            )
            res = self.lo.search(filter=filter_s)
            if len(res) != 1:
                self.fail(
                    "Search with filter={!r} did not return 1 result:\n{}".format(
                        filter_s, "\n".join(repr(res))
                    )
                )
            try:
                dn = res[0][0]
                attrs = res[0][1]
            except KeyError as exc:
                self.log.exception("Error searching for user: %s res=%r", exc, res)
                raise
            username = attrs["uid"][0].decode("UTF-8")
            email = attrs["mailPrimaryAddress"][0].decode("UTF-8")
            self.log.debug("role=%r username=%r email=%r dn=%r", person.role, username, email, dn)
            person.update(dn=dn, username=username, mail=email)
            person.update(firstname=person.firstname.strip(), lastname=person.lastname.strip())
            person.verify()

        self.log.info("*** Modify each user...")

        for person in person_list:
            if person.role == "student":
                person.school_classes = {}
            if person.role != "staff":
                person.append_random_class()

        self.create_csv_file(
            person_list=person_list,
            mapping=config["csv"]["mapping"],
            fn_csv=fn_csv,
            prefix_schools=False,
        )
        # save ldap state for later comparison
        self.save_ldap_status()

        # start import
        self.run_import(["-c", fn_config])

        # check for new users in LDAP
        self.check_new_and_removed_users(0, 0)

        # verify LDAP attributes
        for person in person_list:
            person.verify()

        self.log.info("*** Remove all users...")

        # mark as removed
        for person in person_list:
            person.set_mode_to_delete()
        self.create_csv_file(
            person_list=[], mapping=config["csv"]["mapping"], fn_csv=fn_csv, prefix_schools=False
        )
        # save ldap state for later comparison
        self.save_ldap_status()

        # start import
        self.run_import(["-c", fn_config])

        # check for new users in LDAP
        self.check_new_and_removed_users(0, 4)

        # verify LDAP attributes
        for person in person_list:
            person.verify()


if __name__ == "__main__":
    Test().run()
