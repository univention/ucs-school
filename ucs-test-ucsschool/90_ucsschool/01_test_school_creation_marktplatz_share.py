#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: test if the Marktplatz share is created with every school
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

import pytest

from ucsschool.lib.models.share import MarketplaceShare
from ucsschool.lib.models.utils import ucr
from univention.config_registry import handler_set, handler_unset


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_market_place_created(schoolenv, ucr_value):
    if ucr_value == "unset":
        handler_unset(["ucsschool/import/generate/share/marktplatz"])
    else:
        handler_set(["ucsschool/import/generate/share/marktplatz={}".format(ucr_value)])
    ucr.load()
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr["hostname"], use_cache=False)
    objs = MarketplaceShare.get_all(lo=schoolenv.lo, school=ou_name)
    if ucr_value in ("no", "unset"):
        assert len(objs) == 0
    else:
        assert len(objs) == 1
        assert objs[0].name == "Marktplatz"
