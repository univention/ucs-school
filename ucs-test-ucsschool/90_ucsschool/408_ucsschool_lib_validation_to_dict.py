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
# $ pytest -s -l -v ./......py::test_*
#

import pytest

import univention.testing.strings as uts
from ucsschool.lib.models.group import ComputerRoom, Group, SchoolClass, WorkGroup
from ucsschool.lib.models.share import ClassShare, MarketplaceShare, WorkGroupShare
from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff
from ucsschool.lib.models.validator import get_position_from, obj_to_dict


@pytest.mark.parametrize(
    "ObjectClass",
    [Staff, Student, Teacher, TeachersAndStaff, ExamStudent, SchoolClass, WorkGroup, ComputerRoom],
)
def test_udm_obj_to_dict(ObjectClass, schoolenv):
    if issubclass(ObjectClass, Group):
        name = "DEMOSCHOOL-{}".format(uts.random_name())
    else:
        name = uts.random_name()
    user = ObjectClass(
        school="DEMOSCHOOL",
        name=name,
        firstname=uts.random_name(),
        lastname=uts.random_name(),
    )
    user.create(schoolenv.lo)
    udm_obj = user.get_udm_object(schoolenv.lo)
    dict_obj = obj_to_dict(udm_obj)
    assert dict_obj["props"]
    for key, value in udm_obj.items():
        assert key in dict_obj["props"].keys()
        assert dict_obj["props"][key] == value
    assert udm_obj.dn == dict_obj["dn"]
    assert get_position_from(udm_obj.position.getDn()) == dict_obj["position"]
    for option in udm_obj.options:
        assert option in dict_obj["options"].keys()


@pytest.mark.parametrize("GroupShareClass", [ClassShare, WorkGroupShare, MarketplaceShare])
def test_udm_share_to_dict(GroupShareClass, schoolenv):
    if GroupShareClass in [ClassShare, WorkGroupShare]:
        name = "DEMOSCHOOL-{}".format(uts.random_name())
        if GroupShareClass == ClassShare:
            group = SchoolClass(
                school="DEMOSCHOOL",
                name=name,
            )
            group.create(schoolenv.lo)
        elif GroupShareClass == WorkGroupShare:
            group = WorkGroup(
                school="DEMOSCHOOL",
                name=name,
            )
            group.create(schoolenv.lo)
    else:
        name = "Marktplatz"

    share = GroupShareClass(
        school="DEMOSCHOOL",
        name=name,
    )
    share.create(schoolenv.lo)
    udm_obj = share.get_udm_object(schoolenv.lo)
    dict_obj = obj_to_dict(udm_obj)
    assert dict_obj["props"]
    for key, value in udm_obj.items():
        assert key in dict_obj["props"].keys()
        assert dict_obj["props"][key] == value
    assert udm_obj.dn == dict_obj["dn"]
    assert get_position_from(udm_obj.position.getDn()) == dict_obj["position"]
    for option in udm_obj.options:
        assert option in dict_obj["options"].keys()
