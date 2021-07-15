#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -s -v
## -*- coding: utf-8 -*-
## desc: markplatz share creation check
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [python3-ucsschool-lib]
## bugs: [40785]

from __future__ import print_function

import pytest

import univention.testing.ucr as ucr_test
from ucsschool.lib.models.utils import ucr as lib_ucr
from univention.config_registry import handler_set, handler_unset
from univention.testing import utils


@pytest.mark.parametrize("should_exist,variable", [(False, None), (True, "yes"), (False, "no")])
def test_markplatz_share_creation(schoolenv, should_exist, variable):
    # ucr fixture is session scoped, but we must reset UCRV on every test start
    with ucr_test.UCSTestConfigRegistry() as ucr:
        if variable is None:
            handler_unset(["ucsschool/import/generate/share/marktplatz"])
        else:
            handler_set(["ucsschool/import/generate/share/marktplatz=%s" % (variable,)])
        lib_ucr.load()

        print("### Creating school. Expecting Marktplatz to exists = %r" % (should_exist,))
        school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"), use_cache=False)
        utils.wait_for_replication()
        utils.verify_ldap_object(
            "cn=Marktplatz,cn=shares,%s" % (oudn,), strict=True, should_exist=should_exist
        )
