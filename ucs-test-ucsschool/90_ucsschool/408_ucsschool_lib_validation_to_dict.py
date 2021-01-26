#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.validator obj_to_dict function
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python-ucs-school

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./......py::test_create
#
try:
    from typing import Dict, List, Tuple
except ImportError:
    pass

import re

import univention.admin.modules as udm_modules
import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.group import ComputerRoom, SchoolClass, WorkGroup
from ucsschool.lib.models.share import ClassShare, MarketplaceShare, WorkGroupShare
from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff, User
from ucsschool.lib.models.validator import obj_to_dict


def test_udm_user_to_dict():
    with utu.UCSTestSchool() as schoolenv:
        for cls in [Staff, Student, Teacher, TeachersAndStaff, ExamStudent]:
            user = cls(
                school="DEMOSCHOOL",
                name=uts.random_name(),
                firstname=uts.random_name(),
                lastname=uts.random_name(),
            )
            user.create(schoolenv.lo)
            udm_obj = udm_modules.lookup(
                "users/user",
                None,
                schoolenv.lo,
                scope="sub",
                base=schoolenv.ucr.get("ldap/base"),
                filter=str("uid={}".format(user.name)),
                superordinate=None,
            )[0]
            dict_obj = obj_to_dict(udm_obj)
            assert dict_obj["props"]
            for key, value in udm_obj.items():
                assert key in dict_obj["props"].keys()
                assert dict_obj["props"][key] == value
            assert udm_obj.position.getDn() == dict_obj["dn"]
            position = re.search(r"[^=]+=[^,]+,(.+)", udm_obj.position.getDn()).group(1)
            assert position == dict_obj["position"]
            for option in udm_obj.options:
                if option in dict_obj["options"]:
                    assert option in dict_obj["options"]
                else:
                    assert option in dict_obj["options"]


def test_udm_group_to_dict():
    with utu.UCSTestSchool() as schoolenv:
        for cls in [SchoolClass, WorkGroup, ComputerRoom]:
            name = "DEMOSCHOOL-{}".format(uts.random_name())
            group = cls(school="DEMOSCHOOL", name=name,)
            group.create(schoolenv.lo)
            udm_obj = udm_modules.lookup(
                "groups/group",
                None,
                schoolenv.lo,
                scope="sub",
                base=schoolenv.ucr.get("ldap/base"),
                filter=str("cn={}".format(group.name)),
                superordinate=None,
            )[0]
            dict_obj = obj_to_dict(udm_obj)
            assert dict_obj["props"]
            for key, value in udm_obj.items():
                assert key in dict_obj["props"].keys()
                assert dict_obj["props"][key] == value
            assert udm_obj.position.getDn() == dict_obj["dn"]
            position = re.search(r"[^=]+=[^,]+,(.+)", udm_obj.position.getDn()).group(1)
            assert position == dict_obj["position"]
            for option in udm_obj.options:
                if option in dict_obj["options"]:
                    assert option in dict_obj["options"]
                else:
                    assert option in dict_obj["options"]


def test_udm_share_to_dict():
    with utu.UCSTestSchool() as schoolenv:
        for cls in [ClassShare, WorkGroupShare, MarketplaceShare]:
            if cls in [ClassShare, WorkGroupShare]:
                name = "DEMOSCHOOL-{}".format(uts.random_name())
                if cls == ClassShare:
                    group = SchoolClass(school="DEMOSCHOOL", name=name,)
                    group.create(schoolenv.lo)
                elif cls == WorkGroupShare:
                    group = WorkGroup(school="DEMOSCHOOL", name=name,)
                    group.create(schoolenv.lo)
            else:
                name = "Marktplatz"

            share = cls(school="DEMOSCHOOL", name=name,)
            share.create(schoolenv.lo)
            udm_obj = udm_modules.lookup(
                "shares/share",
                None,
                schoolenv.lo,
                scope="sub",
                base=schoolenv.ucr.get("ldap/base"),
                filter=str("cn={}".format(share.name)),
                superordinate=None,
            )[0]
            dict_obj = obj_to_dict(udm_obj)
            assert dict_obj["props"]
            for key, value in udm_obj.items():
                assert key in dict_obj["props"].keys()
                assert dict_obj["props"][key] == value
            assert udm_obj.position.getDn() == dict_obj["dn"]
            position = re.search(r"[^=]+=[^,]+,(.+)", udm_obj.position.getDn()).group(1)
            assert position == dict_obj["position"]
            for option in udm_obj.options:
                if option in dict_obj["options"]:
                    assert option in dict_obj["options"]
                else:
                    assert option in dict_obj["options"]
