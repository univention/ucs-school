#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Import networks via CLI
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import

from univention.testing.ucsschool.importnetworks import import_networks_basics

if __name__ == '__main__':
	import_networks_basics(use_cli_api=True, use_python_api=False)
