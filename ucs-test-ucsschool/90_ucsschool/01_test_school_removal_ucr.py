#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Modify ucrv on school creation/deletion
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python-ucs-school
##   - ucs-school-selfservice-support


import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu

ucrv = "umc/self-service/passwordreset/whitelist/groups"
delimiter = ","


def test_school_creation():
    # with utu.UCSTestSchool() as schoolenv:
    schoolenv = utu.UCSTestSchool()
    ucr = schoolenv.ucr
    name = uts.random_name()
    value = "Domain Users %s" % name
    name, dn = schoolenv.create_ou(ou_name=name, use_cache=False)
    ucr.load()
    ucr_value = ucr.get(ucrv, "")
    assert value in ucr_value

    # TODO test for removing the school. Does not work  - somehow either
    # the school does not seem to get deleted, or the listener does not seem
    # to get called on remove.
    #
    #
    schoolenv.cleanup_ou(ou_name=name)
    ucr = schoolenv.ucr
    ucr.load()
    ucr_value = ucr.get(ucrv, "")
    print("=" * 60)
    print(ucr_value)
    assert value not in ucr_value


if __name__ == "__main__":
    # pytest.main(sys.argv)
    test_school_creation()
