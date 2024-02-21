#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: The CsvReader does purposely crash on unsupported encodings
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [56846]


import copy
import tempfile

import pytest

import univention.testing.strings as uts
from ucsschool.importer.reader.csv_reader import CsvReader, UnsupportedEncodingError
from univention.testing.ucsschool.csv_test_helper import get_test_chars, write_formatted_csv
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester

# This dictionary maps the python specifier for each encoding
# and the output given by the magiclib.
#
# Note: Meaning of utf-16-le and utf-16-be differ from the
#       usual Python specifiers. In this instance, we are
#       adding the related BOM, which would not exist when
#       using the specifier as per normal.
encodings = {
    "utf-32": "utf-32le",
}

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

        for input_encoding, magic_encoding_repr in encodings.items():
            self.log.info(f"Testing encoding {input_encoding}")

            person_list = []
            person = Person(
                self.ou_A.name, "teacher", firstname=f"User{''.join(get_test_chars(input_encoding))}"
            )
            person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
            person_list.append(person)

            fn_csv_utf8 = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
            fn_csv = tempfile.mkstemp(prefix="users.", dir=self.tmpdir)[1]

            # prepare csv
            with open(fn_csv_utf8) as f:
                content = f.read()

            write_formatted_csv(fn_csv, input_encoding, content)
            detected_encoding = ""
            with pytest.raises(
                UnsupportedEncodingError,
                match=(
                    fr"Unsupported encoding '{magic_encoding_repr}' detected, "
                    "please check the manual for supported encodings."
                ),
            ):
                detected_encoding = CsvReader.get_encoding(fn_csv)

            self.log.info("OK: Correctly identifies unsupported encoding: %s." % detected_encoding)


if __name__ == "__main__":
    Test().run()
