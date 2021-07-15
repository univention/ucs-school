#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: create DC via CLI
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
##   - ucs-school-master

from __future__ import print_function

import subprocess

import univention.testing.strings as uts
from univention.testing.ucsschool.importou import (
    TYPE_DC_ADMINISTRATIVE,
    TYPE_DC_EDUCATIONAL,
    create_ou_cli,
    remove_ou,
)


def test_import_create_dc_via_cli():
    dc_name = uts.random_name()
    ou_name = uts.random_name()
    try:
        print("*** Creating OU %r with DC %r" % (ou_name, dc_name))
        create_ou_cli(ou_name, dc_name)

        for dc_type in (TYPE_DC_EDUCATIONAL, TYPE_DC_ADMINISTRATIVE):
            dc_name = uts.random_name()
            print("*** Creating new %s DC %r" % (dc_type, dc_name))
            cmd_block = [
                "/usr/share/ucs-school-import/scripts/create_dc",
                "--ou=%s" % ou_name,
                "--name=%s" % dc_name,
                "--type=%s" % dc_type,
            ]
            print("cmd_block: %r" % cmd_block)
            subprocess.check_call(cmd_block)
    finally:
        remove_ou(ou_name)
