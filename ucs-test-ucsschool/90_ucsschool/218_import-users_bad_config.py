#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: check that errors in configuration files are written to a logfile (Bug 42373)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [42373]
## versions:
##  4.1-0: skip
##  4.2-0: skip
##  5.0-0: skip

# This test should be disabled until
# https://forge.univention.org/bugzilla/show_bug.cgi?id=42373 is fixed.

import copy
import os
import re

import pytest

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formally test_bad_config()
        """Bug #42373: check that errors in configuration files are written to a logfile"""
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("source_uid", source_uid)
        person = Person(self.ou_A.name, "student")
        fn_csv = self.create_csv_file(person_list=[person], mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config)
        with open(fn_config, "r+") as fp:
            fp.seek(0, os.SEEK_END)
            fp.seek(fp.tell() - 3, os.SEEK_SET)
            fp.write("foo")
        self.log.info("*** Running import with broken configuration file...\n*")
        with pytest.raises(ImportException) as exc:
            self.run_import(["-c", fn_config])
        self.log.info("*** OK - error was expected: %r", exc.value)
        # look for error message in logfile
        msg = r"InitialisationError.*Error in configuration file '{}'".format(fn_config)
        for line in open("/var/log/univention/ucs-school-import/workers-import.log"):
            found = re.findall(msg, line)
            if found:
                self.log.info("Found in logfile: %r", found[0])
                break
        else:
            self.fail("Error message not found in logfile.")


if __name__ == "__main__":
    Test().run()
