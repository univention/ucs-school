# Copyright 2020 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

from typing import List

import pytest
from faker import Faker

import requests
import ucsschool.kelvin.constants
from ldap.filter import filter_format
from ucsschool.kelvin.routers.school_class import SchoolClassModel
from ucsschool.lib.models.base import NoObject
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.user import User
from udm_rest_client import UDM

fake = Faker()
pytestmark = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)


def dn2username(dn: str) -> str:
    return dn.split(",")[0].split("=")[1]


def url2username(url: str) -> str:
    return url.rsplit("/", 1)[-1]


class RequestFake:
    def __init__(self, url_fragment: str):
        self.url_fragment = url_fragment

    def url_for(self, name: str, **path_params) -> str:
        assert name == "get"
        if "class_name" in path_params:
            # self.url
            class_name = path_params["class_name"]
            school = path_params["school"]
            return f"{self.url_fragment}/classes/{school}/{class_name}"
        if "school_name" in path_params:
            # self.school
            school_name = path_params["school_name"]
            return f"{self.url_fragment}/schools/{school_name}"
        if "username" in path_params:
            # self.users
            username = path_params["username"]
            return f"{self.url_fragment}/users/{username}"


async def compare_lib_api_obj(
    lib_obj: SchoolClass, api_obj: SchoolClassModel, url_fragment
):
    for attr, lib_value in lib_obj.to_dict().items():
        if attr == "$dn$":
            assert lib_value == api_obj.dn
        elif attr == "objectType":
            assert lib_value == "groups/group"
        elif attr == "school":
            assert (
                f"{url_fragment}/schools/{lib_value}"
                == api_obj.unscheme_and_unquote(api_obj.school)
            )
        elif attr == "users":
            lib_users = {dn2username(lu) for lu in lib_value}
            api_users = {url2username(url) for url in api_obj.users}
            assert lib_users == api_users
        elif attr == "ucsschool_roles":
            if lib_value:
                assert lib_value == api_obj.ucsschool_roles
            else:
                assert api_obj.ucsschool_roles == ["school_class:school:DEMOSCHOOL"]
        else:
            assert lib_value == getattr(api_obj, attr)


def compare_ldap_json_obj(dn, json_resp, url_fragment):
    import univention.admin.uldap

    lo, pos = univention.admin.uldap.getAdminConnection()
    ldap_obj = lo.get(dn)

    for attr, value in json_resp.items():
        if attr == "ucsschool_roles":
            assert value[0] == ldap_obj["ucsschoolRole"][0].decode("utf-8")
        elif attr == "description" and "description" in ldap_obj:
            assert value == ldap_obj["description"][0].decode("utf-8")
        elif attr == "users":
            json_users = {url2username(url) for url in json_resp["users"]}
            if json_users:
                ldap_users = {name.decode("utf-8") for name in ldap_obj["memberUid"]}
                assert json_users == ldap_users
        elif attr == "dn":
            assert f"cn={ldap_obj['cn'][0].decode('utf-8')}" in value
        elif attr == "name":
            assert value in ldap_obj["cn"][0].decode("utf-8")
    if "univentionObjectType" in ldap_obj:
        assert ldap_obj["univentionObjectType"] == [b"groups/group"]


@pytest.mark.asyncio
async def test_search(auth_header, url_fragment, udm_kwargs, new_school_class):
    sc1_dn, sc1_attr = await new_school_class()
    sc2_dn, sc2_attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        lib_classes: List[SchoolClass] = await SchoolClass.get_all(
            udm, sc1_attr["school"]
        )
    assert sc1_dn in [c.dn for c in lib_classes]
    assert sc2_dn in [c.dn for c in lib_classes]
    response = requests.get(
        f"{url_fragment}/classes", headers=auth_header, params={"school": "DEMOSCHOOL"},
    )
    json_resp = response.json()
    assert response.status_code == 200
    api_classes = {
        f"{sc1_attr['school']}-{data['name']}": SchoolClassModel(**data)
        for data in json_resp
    }
    assert set(api_classes.keys()) == set(c.name for c in lib_classes)
    for lib_obj in lib_classes:
        api_obj = api_classes[lib_obj.name]
        await compare_lib_api_obj(lib_obj, api_obj, url_fragment)
        resp = [resp for resp in json_resp if resp["dn"] == api_obj.dn][0]
        compare_ldap_json_obj(api_obj.dn, resp, url_fragment)


@pytest.mark.asyncio
async def test_get(auth_header, url_fragment, udm_kwargs, new_school_class):
    sc1_dn, sc1_attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        lib_obj: SchoolClass = await SchoolClass.from_dn(
            sc1_dn, sc1_attr["school"], udm
        )
    assert sc1_dn == lib_obj.dn
    url = f"{url_fragment}/classes/{sc1_attr['school']}/{sc1_attr['name']}"
    response = requests.get(url, headers=auth_header,)
    json_resp = response.json()
    assert response.status_code == 200
    api_obj = SchoolClassModel(**json_resp)
    await compare_lib_api_obj(lib_obj, api_obj, url_fragment)
    compare_ldap_json_obj(json_resp["dn"], json_resp, url_fragment)


@pytest.mark.asyncio
async def test_create(auth_header, url_fragment, udm_kwargs, new_school_class_obj):
    lib_obj: SchoolClass = new_school_class_obj()
    attrs = {
        "name": lib_obj.name[len(lib_obj.school) + 1 :],  # noqa: E203
        "school": f"{url_fragment}/schools/{lib_obj.school}",
        "description": lib_obj.description,
        "users": lib_obj.users,
    }
    async with UDM(**udm_kwargs) as udm:
        assert await lib_obj.exists(udm) is False
        response = requests.post(
            f"{url_fragment}/classes/",
            headers={"Content-Type": "application/json", **auth_header},
            json=attrs,
        )
        json_resp = response.json()
        assert response.status_code == 201
        api_obj = SchoolClassModel(**json_resp)
        assert lib_obj.dn == api_obj.dn
        assert (
            await SchoolClass(name=lib_obj.name, school=lib_obj.school).exists(udm)
            is True
        )
        await compare_lib_api_obj(lib_obj, api_obj, url_fragment)
        compare_ldap_json_obj(json_resp["dn"], json_resp, url_fragment)
        await SchoolClass(name=lib_obj.name, school=lib_obj.school).remove(udm)
        assert (
            await SchoolClass(name=lib_obj.name, school=lib_obj.school).exists(udm)
            is False
        )


async def change_operation(
    auth_header,
    url_fragment,
    udm_kwargs,
    new_school_class,
    create_random_users,
    operation,
):
    assert operation in ("patch", "put")
    users_data = await create_random_users(
        {"student": 2, "teacher": 1, "teacher_and_staff": 1}
    )
    student_data = None
    for user_data in users_data:
        for role in user_data.roles:
            if role.endswith("student"):
                student_data = user_data
        if student_data:
            break
    else:
        raise RuntimeError("No student in user data.")
    async with UDM(**udm_kwargs) as udm:
        students = [
            obj
            async for obj in udm.get("users/user").search(
                filter_format("uid=%s", (student_data.name,))
            )
        ]
        assert len(students) == 1
        first_student_dn = students[0].dn
        sc1_dn, sc1_attr = await new_school_class(users=[first_student_dn])
        # verify class exists in LDAP
        lib_obj: SchoolClass = await SchoolClass.from_dn(
            sc1_dn, sc1_attr["school"], udm
        )
        assert lib_obj.description == sc1_attr["description"]
        assert lib_obj.users == [first_student_dn]
        # verify users exist in LDAP
        for user_data in users_data:
            assert (
                await User(name=user_data.name, school=user_data.school).exists(udm)
                is True
            )
        # execute PATCH/PUT
        change_data = {
            "description": fake.text(max_nb_chars=50),
            "users": [
                f"{url_fragment}/users/{user_data.name}" for user_data in users_data
            ],
        }
        if operation == "put":
            change_data["name"] = sc1_attr["name"]
            change_data["school"] = f"{url_fragment}/schools/{sc1_attr['school']}"
        url = f"{url_fragment}/classes/{sc1_attr['school']}/{sc1_attr['name']}"
        requests_method = getattr(requests, operation)
        response = requests_method(url, headers=auth_header, json=change_data,)
        json_resp = response.json()
        assert response.status_code == 200
        # check response
        api_obj = SchoolClassModel(**json_resp)
        assert api_obj.dn == sc1_dn
        assert api_obj.description == change_data["description"]
        assert {api_obj.unscheme_and_unquote(url) for url in api_obj.users} == set(
            change_data["users"]
        )
        usernames_in_response = {url2username(url) for url in api_obj.users}
        # check LDAP content
        lib_obj: SchoolClass = await SchoolClass.from_dn(
            sc1_dn, sc1_attr["school"], udm
        )
        assert lib_obj.description == change_data["description"]
        usernames_in_ldap = {dn2username(dn) for dn in lib_obj.users}
        assert usernames_in_response == usernames_in_ldap


@pytest.mark.asyncio
async def test_put(
    auth_header, url_fragment, udm_kwargs, new_school_class, create_random_users
):
    await change_operation(
        auth_header,
        url_fragment,
        udm_kwargs,
        new_school_class,
        create_random_users,
        operation="put",
    )


@pytest.mark.asyncio
async def test_patch(
    auth_header, url_fragment, udm_kwargs, new_school_class, create_random_users
):
    await change_operation(
        auth_header,
        url_fragment,
        udm_kwargs,
        new_school_class,
        create_random_users,
        operation="patch",
    )


@pytest.mark.asyncio
async def test_delete(auth_header, url_fragment, udm_kwargs, new_school_class):
    sc1_dn, sc1_attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        lib_obj: SchoolClass = await SchoolClass.from_dn(
            sc1_dn, sc1_attr["school"], udm
        )
        assert await lib_obj.exists(udm) is True
    assert sc1_dn == lib_obj.dn
    url = f"{url_fragment}/classes/{sc1_attr['school']}/{sc1_attr['name']}"
    response = requests.delete(url, headers=auth_header,)
    assert response.status_code == 204
    async with UDM(**udm_kwargs) as udm:
        with pytest.raises(NoObject):
            await SchoolClass.from_dn(sc1_dn, sc1_attr["school"], udm)
