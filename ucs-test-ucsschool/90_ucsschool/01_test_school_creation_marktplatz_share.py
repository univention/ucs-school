#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test if Marktplatz is created with every school
## roles: [domaincontroller_master, domaincontroller_backup]
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python-ucs-school

import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.share import MarketplaceShare


def test_market_place_created():
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou()
        objs = MarketplaceShare.get_all(lo=schoolenv.lo, school=ou_name)
        assert len(objs) == 1
        assert objs[0].name == "Marktplatz"
