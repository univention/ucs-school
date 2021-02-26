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

        name, dn = schoolenv.create_ou(ou_name=name, use_cache=False)
        ucr.load()
        ucr_value = ucr.get(ucrv, "")
        print("xxx", ucr_value)
        assert value in ucr_value

        # TODO test for removing the school. Does not work  - somehow either
        # the school does not seem to get deleted, or the listener does not seem
        # to get called on remove.
        #
        #
        # schoolenv.cleanup_ou(ou_name=name)
        # # schoolenv.cleanup(wait_for_replication=True)
        # # schoolenv.udm.cleanup()
        # wait_for_listener_replication()
        # res = udm.list_objects("container/ou")
        # # res = mod.get(dn)
        # print('z'*60)
        # print(dn)
        # print(res)
        # ucr.load()
        # ucr_value = ucr.get(ucrv, "")
        # print("+"*100)
        # print('yyy', ucr_value)
        # assert value not in ucr_value


if __name__ == "__main__":
    # pytest.main(sys.argv)
    test_school_creation()
