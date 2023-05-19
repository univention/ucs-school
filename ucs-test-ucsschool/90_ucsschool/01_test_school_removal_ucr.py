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
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.utils import ucr as lib_ucr
from univention.udm import UDM

ucrv = "umc/self-service/passwordreset/whitelist/groups"
delimiter = ","


def test_school_creation():
    with utu.UCSTestSchool() as schoolenv:
        name = uts.random_name()
        value = "Domain Users %s" % name
        schoolenv.create_ou(ou_name=name, use_cache=False)
        lib_ucr.load()
        ucr_value = lib_ucr.get(ucrv, "")
        assert value in ucr_value

        # It would be nice if we could manually cleanup the school. Doing
        # it here does not trigger the listener, however...
        # schoolenv.cleanup_ou(ou_name=name)

    # ...so we let the context manager do the cleanup, which actually works
    lib_ucr.load()
    ucr_value = lib_ucr.get(ucrv, "")
    assert value not in ucr_value

    portals = UDM.machine().version(2).get("portals/entry")
    entry = next(portals.search("cn=self-service-password-change"), None)
    assert entry is not None
    assert all([value not in group for group in entry.props.allowedGroups])
