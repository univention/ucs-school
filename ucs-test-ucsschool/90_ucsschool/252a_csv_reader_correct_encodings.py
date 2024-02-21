#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: The CsvReader does correctly detect defined encodings
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
from ucsschool.importer.reader.csv_reader import CsvReader
from univention.testing.ucsschool.csv_test_helper import get_test_chars, write_formatted_csv
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException

# This dictionary maps the python specifier for each encoding
# and the output given by the magiclib.
#
# Note: Meaning of utf-16-le and utf-16-be differ from the
#       usual Python specifiers. In this instance, we are
#       adding the related BOM, which would not exist when
#       using the specifier as per normal.
encodings = {
    "binary": "binary",
    "ascii": "us-ascii",
    "latin-1": "iso-8859-1",
    "utf-8": "utf-8",
    "utf-8-sig": "utf-8-sig",
    "utf-16": "utf-16-be",
    "utf-16-le": "utf-16le",
    "utf-16-be": "utf-16be",
    "utf-16-no-bom": "utf-16-be",
}

import_logfile = "/var/log/univention/ucs-school-import.log"


class Test(CLI_Import_v2_Tester):
    def check_logfile_error(self, fn_config, fn_csv):
        with pytest.raises(ImportException):
            self.run_import(["-c", fn_config, "-i", fn_csv])

            # By default, a binary file is not supported. But it should not fail
            # before a reader class is used. A custom reader class might be able to read
            # binary files.
            with open(import_logfile) as f:
                lines = f.readlines()
                assert (
                    "UnsupportedEncodingError: Unsupported encoding 'binary' detected, "
                    "please check the manual for supported encodings." in lines[-1]
                ), lines[-1]

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

            with open(fn_csv_utf8) as f:
                content = f.read()

            if input_encoding == "binary":
                with open(fn_csv, "wb") as g:
                    g.write(bytes(range(256)))
                # Expecting logfile error due to binary encoding
                self.check_logfile_error(fn_config, fn_csv)

            else:
                write_formatted_csv(fn_csv, input_encoding, content)

                if input_encoding == "utf-16-no-bom":
                    # No BOM here. Data has to be interpreted as binary.
                    assert "binary" == CsvReader.get_encoding(fn_csv)
                    # Expecting logfile error due to binary encoding
                    self.check_logfile_error(fn_config, fn_csv)

                    self.log.info("OK: Detected correct encoding: binary (caused by missing BOM).")

                else:
                    detected_encoding = CsvReader.get_encoding(fn_csv)

                    assert (detected_encoding == input_encoding) or (
                        # special case: only used for "utf-16" encodings
                        detected_encoding
                        in magic_encoding_repr
                    ), "Expected encoding: %s Detected encoding: %s MagicPackageEncodingRepr: %s" % (
                        input_encoding,
                        detected_encoding,
                        magic_encoding_repr,
                    )
                    self.log.info("OK: Detected correct encoding: %s." % detected_encoding)


if __name__ == "__main__":
    Test().run()
