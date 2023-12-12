#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: The importer should not remove existing admin roles or non ucsschool roles
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [53203]

import copy
import string
import tempfile

import pytest

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException

encodings = ["binary", "ascii", "latin_1", "utf_8"]

import_logfile = "/var/log/univention/ucs-school-import.log"


class Test(CLI_Import_v2_Tester):
    def test(self):
        """Test behaviour with different encodings and binary format"""
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("csv:mapping:Benutzername", "name")
        config.update_entry("csv:mapping:record_uid", "record_uid")
        config.update_entry("csv:mapping:role", "__role")
        config.update_entry("source_uid", source_uid)
        config.update_entry("user_role", None)
        fn_config = self.create_config_json(config=config)

        for encoding in encodings:
            self.log.info(f"Testing encoding {encoding}")
            if encoding == "ascii":
                chars = string.ascii_letters
            else:
                chars = "öäüß"
            person_list = []
            person = Person(self.ou_A.name, "teacher", firstname=f"User{''.join(chars)}")
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            person_list.append(person)

            fn_csv_utf8 = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
            fn_csv = tempfile.mkstemp(prefix="users.", dir=self.tmpdir)[1]

            with open(fn_csv_utf8) as f:
                content = f.read()

            if encoding == "binary":
                with open(fn_csv, "wb") as g:
                    g.write(bytes(range(256)))

                with pytest.raises(ImportException):
                    self.run_import(["-c", fn_config, "-i", fn_csv])

                # By default, a binary file is not supported. But it should not fail
                # before a reader class is used. A custom reader class might be able to read
                # binary files.
                with open(import_logfile) as f:
                    lines = f.readlines()
                    assert "LookupError: unknown encoding: binary" in lines[-1]
            else:
                with open(fn_csv, "w", encoding=encoding) as g:
                    g.write(content)
                self.run_import(["-c", fn_config, "-i", fn_csv])

                for person in person_list:
                    person.verify()
                self.log.info("OK: import (create) succeeded.")


if __name__ == "__main__":
    Test().run()
