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

from ucsschool.lib.models.group import ComputerRoom, Group, SchoolClass, WorkGroup
from ucsschool.lib.models.share import ClassShare, WorkGroupShare  # MarketplaceShare
from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff
from ucsschool.lib.models.validator import obj_to_dict
from udm_rest_client import UDM


def _inside_docker():
    try:
        import ucsschool.kelvin.constants
    except ImportError:
        return False
    return ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists()


pytestmark = pytest.mark.skipif(
    not _inside_docker(),
    reason="Must run inside Docker container started by appcenter.",
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ObjectClass",
    [Staff, Student, Teacher, TeachersAndStaff, ExamStudent, SchoolClass, WorkGroup, ComputerRoom],
)
async def test_udm_obj_to_dict(
    ObjectClass,
    udm_kwargs,
    random_first_name,
    random_last_name,
    random_user_name,
    create_ou_using_python,
):
    ou = await create_ou_using_python()
    if issubclass(ObjectClass, Group):
        name = "{}-{}".format(ou, random_user_name())
    else:
        name = random_user_name()
    user = ObjectClass(
        school=ou,
        name=name,
        firstname=random_first_name(),
        lastname=random_last_name(),
    )
    async with UDM(**udm_kwargs) as udm:
        await user.create(udm)
        udm_obj = await user.get_udm_object(udm)
    dict_obj = obj_to_dict(udm_obj)
    assert dict_obj["props"]
    for key, value in udm_obj.props.items():
        assert key in dict_obj["props"].keys()
        assert dict_obj["props"][key] == value
    assert udm_obj.dn == dict_obj["dn"]
    assert udm_obj.position == dict_obj["position"]
    for option in udm_obj.options:
        assert option in dict_obj["options"].keys()


@pytest.mark.asyncio
@pytest.mark.parametrize("GroupShareClass", [ClassShare, WorkGroupShare])  # MarketplaceShare
async def test_udm_share_to_dict(GroupShareClass, udm_kwargs, random_user_name, create_ou_using_python):
    ou = await create_ou_using_python()
    async with UDM(**udm_kwargs) as udm:
        if GroupShareClass in [ClassShare, WorkGroupShare]:
            name = "{}-{}".format(ou, random_user_name())
            if GroupShareClass == ClassShare:
                group = SchoolClass(
                    school=ou,
                    name=name,
                )
                await group.create(udm)
            elif GroupShareClass == WorkGroupShare:
                group = WorkGroup(
                    school=ou,
                    name=name,
                )
                await group.create(udm)
        else:
            name = "Marktplatz"

        share = GroupShareClass(
            school=ou,
            name=name,
        )
        await share.create(udm)
        udm_obj = await share.get_udm_object(udm)
        dict_obj = obj_to_dict(udm_obj)
        assert dict_obj["props"]
        for key, value in udm_obj.props.items():
            assert key in dict_obj["props"].keys()
            assert dict_obj["props"][key] == value
        assert udm_obj.dn == dict_obj["dn"]
        assert udm_obj.position == dict_obj["position"]
        for option in udm_obj.options:
            assert option in dict_obj["options"].keys()
