#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test python interactive shell helper import
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [41861]

import univention.testing.strings as uts
import univention.testing.utils as utils
from ucsschool.importer.utils.shell import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
    config,
    logger,
)


def test_import_shell(ucr, schoolenv):
    assert isinstance(config, dict) and isinstance(config["verbose"], bool), "Import configuration has not been not setup."
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    lo = schoolenv.open_ldap_connection(admin=True)
    for kls in [ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff]:
        user = kls(
            name=uts.random_username(),
            school=ou_name,
            firstname=uts.random_name(),
            lastname=uts.random_name(),
            record_uid=uts.random_name(),
        )
        user.prepare_all(True)
        user.create(lo)
        utils.verify_ldap_object(
            user.dn, expected_attr={"uid": [user.name]}, strict=False, should_exist=True
        )
    logger.info("Test was successful.\n\n\n")
