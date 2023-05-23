#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Test that multiple nested CSV configuration arguments can be passed via --set
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [53632]

import copy
import os
import re
import subprocess
import tempfile

from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def __init__(self):
        super(Test, self).__init__()
        self.summary_fd = tempfile.NamedTemporaryFile(delete=False, mode="w+")
        self.passwords_fd = tempfile.NamedTemporaryFile(delete=False, mode="w+")

    def cleanup(self):
        super(Test, self).cleanup()
        os.remove(self.summary_fd.name)
        os.remove(self.passwords_fd.name)

    def test(self):
        config = copy.deepcopy(self.default_config)
        config.update_entry("dry_run", True)
        args = [
            "--set",
            "csv:mapping:lastname=lastname",
            "csv:mapping:name=name",
        ]
        cmd = ["/usr/share/ucs-school-import/scripts/ucs-school-user-import", "-v", "--dry-run"] + args
        proc = subprocess.run(cmd, capture_output=True, text=True)

        csv_mapping = re.search(
            "        'mapping': {([^\n]*)}},\n",
            proc.stderr,
            re.DOTALL,
        )

        assert csv_mapping is not None, "Could not find CSV mapping in command line arguments"
        assert (
            csv_mapping.group(1) == "'lastname': 'lastname', 'name': 'name'"
        ), "CSV mapping in command line arguments is not correct: %s" % csv_mapping.group(1)


if __name__ == "__main__":
    Test().run()
