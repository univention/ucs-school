#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: set values in extended attribute (Bug 41707)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41707]

import copy
import pprint
import time

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class ExtAttrPerson(Person):
    def __init__(self, school, role, ext_attr_name):
        super(ExtAttrPerson, self).__init__(school, role)
        self.extattr = time.strftime("%Y-%m-%d")
        self.ext_attr_name = ext_attr_name

    def map_to_dict(self, value_map, prefix_schools=True):
        result = super(ExtAttrPerson, self).map_to_dict(value_map, prefix_schools=prefix_schools)
        result[value_map.get(self.ext_attr_name, "__EMPTY__")] = self.extattr
        return result

    def expected_attributes(self):
        result = super(ExtAttrPerson, self).expected_attributes()
        result["univentionFreeAttributes15"] = [self.extattr]


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formally test_create_modify_with_extended_attribute()
        """Bug #41707: set values in extended attribute"""
        ext_attr_name = uts.random_name()
        properties = {
            "position": self.udm.UNIVENTION_CONTAINER,
            "name": uts.random_name(),
            "shortDescription": uts.random_string(),
            "CLIName": ext_attr_name,
            "module": "users/user",
            "objectClass": "univentionFreeAttributes",
            "ldapMapping": "univentionFreeAttribute15",
            "mayChange": 1,
        }
        self.udm.create_object("settings/extended_attribute", **properties)

        source_uid = "source_uid-%s" % (uts.random_string(),)

        config = copy.deepcopy(self.default_config)
        config.update_entry("source_uid", source_uid)
        config.update_entry("csv:mapping:extattr", ext_attr_name)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("scheme:%s" % (ext_attr_name,), "<firstname:upper> <lastname> <description>")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)

        self.log.info("*** Importing a new user of each role...")
        person_list = []
        for role in ("student", "teacher", "staff", "teacher_and_staff"):
            # create person with extended attribute (today)
            person = ExtAttrPerson(self.ou_A.name, role, ext_attr_name)
            self.log.info("ext_attr_name=%r extattr value=%r", ext_attr_name, person.extattr)
            person.update(record_uid=person.username, source_uid=source_uid)
            person_list.append(person)

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])

        for person in person_list:
            self.log.debug(
                "User object %r:\n%s",
                person.dn,
                pprint.PrettyPrinter(indent=2).pformat(self.lo.get(person.dn)),
            )
            person.verify()

            # modify person and set ext_attr to random value
            person.update(extattr=uts.random_string())

        fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
        fn_config = self.create_config_json(config=config)
        self.run_import(["-c", fn_config, "-i", fn_csv])

        for person in person_list:
            self.log.debug(
                "User object %r:\n%s",
                person.dn,
                pprint.PrettyPrinter(indent=2).pformat(self.lo.get(person.dn)),
            )
            person.verify()


if __name__ == "__main__":
    Test().run()
