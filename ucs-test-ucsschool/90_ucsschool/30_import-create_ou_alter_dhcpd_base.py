#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Import OU via CLI and verify dhcpd/ldap/base
## tags: [apptest,ucsschool,ucsschool_import4]
## roles: [domaincontroller_master]
## timeout: 14400
## exposure: dangerous
## packages:
##   - ucs-school-import

import univention.testing.ucsschool.importou as eio

if __name__ == "__main__":
    eio.import_ou_alter_dhcpd_base_flag(use_cli_api=True, use_python_api=False)
