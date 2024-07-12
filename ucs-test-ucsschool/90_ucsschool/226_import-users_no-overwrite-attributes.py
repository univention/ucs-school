#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test no-overwrite-attributes
## tags: [apptest,ucsschool,ucsschool_import1,skip_in_upgrade_singleserver]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [45679]

# skipped in upgrade singleserver scenario, see Issue #1234

import copy

from ldap.filter import filter_format

import univention.config_registry
import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):
        source_uid = "source_uid-{}".format(uts.random_string())
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry(
            "scheme:email", "<:umlauts><firstname:lower>.<lastname:lower>[ALWAYSCOUNTER]@<maildomain>"
        )
        config.update_entry("scheme:username:default", "<:umlauts><firstname:lower><lastname:lower>")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)
        del config["csv"]["mapping"]["E-Mail"]

        self.log.info("*** 1/5 Importing a user from each role with default UCR config...")
        univention.config_registry.handler_unset(
            ["ucsschool/import/generate/user/attributes/no-overwrite-by-schema"]
        )

        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            person = Person(self.ou_A.name, role)
            record_uid = "record_uid-%s" % (uts.random_string(),)
            person.update(
                record_uid=record_uid,
                source_uid=source_uid,
                firstname=uts.random_username(),
                lastname=uts.random_username(),
                username=None,
                mail=None,
            )
            person_list.append(person)
        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
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
                email = attrs["mailPrimaryAddress"][0].decode("UTF-8")
            except KeyError as exc:
                self.log.exception("Error searching for user: %s res=%r", exc, res)
                raise
            local, domain = email.rsplit("@")
            if not local.endswith("1"):
                self.fail(
                    'Email address should end in "1" ([ALWAYSCOUNTER] in scheme:email), '
                    "but is {!r}.".format(email)
                )
            username = res[0][1]["uid"][0].decode("UTF-8")
            self.log.debug("role=%r username=%r email=%r dn=%r", person.role, username, email, dn)
            person.update(dn=dn, username=username, mail=email)
            person.verify()
        self.log.info("*** OK 1/5: All %r users were created correctly.", len(person_list))

        self.log.info("*** 2/5 Importing the CSV again...")

        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(0, 0)
        for person in person_list:
            person.verify()
        self.log.info("*** OK 2/5: All %r users username and email were NOT modified.", len(person_list))

        self.log.info('*** 3/5 removing "mailPrimaryAddress" from UCRV and importing same CSV...')

        # remove "mailPrimaryAddress" from UCRV
        univention.config_registry.handler_set(
            ["ucsschool/import/generate/user/attributes/no-overwrite-by-schema=uid"]
        )
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(0, 0)
        for person in person_list:
            local, domain = person.mail.rsplit("@")
            person.update(mail="{}2@{}".format(local[:-1], domain))
            person.verify()
        self.log.info("*** OK 3/5: All %r users email WERE modified.", len(person_list))

        self.log.info('*** 4/5 still no "mailPrimaryAddress" in UCRV and importing same CSV again...')

        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(0, 0)
        for person in person_list:
            local, domain = person.mail.rsplit("@")
            person.update(mail="{}3@{}".format(local[:-1], domain))
            person.verify()
        self.log.info("*** OK 4/5: All %r users email were modified again.", len(person_list))

        self.log.info('*** 5/5 adding "mailPrimaryAddress" to UCRV and importing same CSV...')

        # add "mailPrimaryAddress" from UCRV
        univention.config_registry.handler_set(
            ["ucsschool/import/generate/user/attributes/no-overwrite-by-schema=mailPrimaryAddress uid"]
        )
        self.save_ldap_status()
        self.run_import(["-c", fn_config])
        self.check_new_and_removed_users(0, 0)
        for person in person_list:
            person.verify()
        self.log.info("*** OK 5/5: All %r users email were NOT modified.", len(person_list))


if __name__ == "__main__":
    Test().run()
