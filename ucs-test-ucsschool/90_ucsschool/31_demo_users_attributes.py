#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: check demo users additional attributes
## tags: [apptest,ucsschool]
## roles: [domaincontroller_master]
## exposure: safe
## packages:
##   - ucs-school-singleserver
## bugs: [54205]
import pytest

from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import User


def test_demo_school_exists(lo):
    assert School(name="DEMOSCHOOL").exists(lo)


def test_demo_users_additional_attributes(lo):
    if not School(name="DEMOSCHOOL").exists(lo):
        pytest.skip("demo school does not exist")
    demo_users = User.get_all(lo, school="DEMOSCHOOL")
    for user in demo_users:
        user_udm_object = user.get_udm_object(lo)
        assert user_udm_object["ucsschoolSourceUID"] == "DEMOID"
        assert user_udm_object["ucsschoolRecordUID"]  # not None nor empty string
        assert user_udm_object["ucsschoolRecordUID"] == user_udm_object["username"]
