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
    with utu.UCSTestSchool() as schoolenv:
        ucr = schoolenv.ucr
        name = uts.random_name()
        value = "Domain Users %s" % name

        assert value not in ucr.get(ucrv, "")

        schoolenv.create_ou(ou_name=name, use_cache=False)
        ucr.load()
        ucr_value = ucr.get(ucrv, "")
        assert value in ucr_value


if __name__ == "__main__":
    test_school_creation()
