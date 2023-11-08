#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Modify ucrv on school creation/deletion
## roles: [domaincontroller_master, domaincontroller_backup]
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib
##   - ucs-school-selfservice-support


import univention.testing.strings as uts
import univention.testing.utils as utu
from ucsschool.lib.models.utils import ucr as lib_ucr  # 'ucr' already exists as fixture
from univention.udm import UDM

ucrv = "umc/self-service/passwordreset/whitelist/groups"
delimiter = ","


def test_school_creation(schoolenv):
    name = uts.random_name()
    value = "Domain Users %s" % name

    assert value not in lib_ucr.get(ucrv, "")

    schoolenv.create_ou(ou_name=name, use_cache=False)
    lib_ucr.load()
    ucr_value = lib_ucr.get(ucrv, "")
    assert value in ucr_value

    utu.wait_for_replication()

    portals = UDM.machine().version(2).get("portals/entry")
    entry = next(portals.search("cn=self-service-password-change"), None)
    assert entry is not None
    assert any(value in group for group in entry.props.allowedGroups)
