#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: check that errors in configuration files are written to a logfile (Bug 42373)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [42373]
## versions:
##  4.1: skip
##  4.2: skip

import copy
import os
import re

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):  # formally test_bad_config()
        """
        Bug #42373: check that errors in configuration files are written to a logfile
        """
        source_uid = "source_uid-%s" % (uts.random_string(),)
        config = copy.deepcopy(self.default_config)
        config.update_entry("source_uid", source_uid)
        person = Person(self.ou_A.name, "student")
        fn_csv = self.create_csv_file(person_list=[person], mapping=config["csv"]["mapping"])
        config.update_entry("input:filename", fn_csv)
        fn_config = self.create_config_json(config=config)
        with open(fn_config, "rb+") as fp:
            fp.seek(-3, os.SEEK_END)
            fp.write("foo")
        self.log.info("*** Running import with broken configuration file...\n*")
        try:
            self.run_import(["-c", fn_config])
            self.fail("Import ran with broken configuration.")
        except ImportException as exc:
            self.log.info("*** OK - error was expected: %r", exc)
        # look for error message in logfile
        msg = r"InitialisationError.*Error in configuration file '{}'".format(fn_config)
        for line in open("/var/log/univention/ucs-school-import.log", "rb"):
            found = re.findall(msg, line)
            if found:
                self.log.info("Found in logfile: %r", found[0])
                break
        else:
            self.fail("Error message not found in logfile.")


if __name__ == "__main__":
    Test().run()
