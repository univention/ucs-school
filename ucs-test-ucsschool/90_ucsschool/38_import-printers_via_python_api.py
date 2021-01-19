#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Import printers via python API
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## timeout: 14400
## packages:
##   - ucs-school-import

import sys

from univention.testing.ucsschool.importprinters import import_printers_basics

if __name__ == "__main__":
    # Not yet implemented
    sys.exit(137)

    import_printers_basics(use_cli_api=False, use_python_api=True)
