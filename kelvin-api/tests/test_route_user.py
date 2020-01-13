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

import random
from typing import List, NamedTuple, Type, Union
from urllib.parse import SplitResult, urlsplit

import pytest
import requests
from ldap.filter import filter_format
from pydantic import HttpUrl

import ucsschool.kelvin.constants
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.kelvin.routers.role import SchoolUserRole
from ucsschool.kelvin.routers.user import UserCreateModel, UserModel, UserPatchModel
from ucsschool.lib.models.user import Staff, Student, Teacher, TeachersAndStaff, User
from udm_rest_client import UDM

pytestmark = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)

MAPPED_UDM_PROPERTIES = [
    "title",
    "description",
    "employeeType",
    "organisation",
    "phone",
    "uidNumber",
    "gidNumber",
]  # keep in sync with conftest.py::MAPPED_UDM_PROPERTIES
random.shuffle(MAPPED_UDM_PROPERTIES)
UserType = Type[Union[Staff, Student, Teacher, TeachersAndStaff, User]]
Role = NamedTuple("Role", [("name", str), ("klass", UserType)])
USER_ROLES: List[Role] = [
    Role("staff", Staff),
    Role("student", Student),
    Role("teacher", Teacher),
    Role("teacher_and_staff", TeachersAndStaff),
]  # User.role_sting -> User
random.shuffle(USER_ROLES)


def role_id(value: Role) -> str:
    return value.name


async def compare_lib_api_user(  # noqa: C901
    lib_user: ImportUser, api_user: UserModel, udm: UDM, url_fragment: str
) -> None:
    udm_obj = await lib_user.get_udm_object(udm)
    for key, value in api_user.dict().items():
        if key == "school":
            assert value.split("/")[-1] == getattr(lib_user, key)
        elif key == "schools":
            assert len(value) == len(getattr(lib_user, key))
            for entry in value:
                assert entry.split("/")[-1] in getattr(lib_user, key)
        elif key == "url":
            assert (
                api_user.unscheme_and_unquote(value)
                == f"{url_fragment}/users/{lib_user.name}"
            )
        elif key == "record_uid":
            assert value == udm_obj.props.ucsschoolRecordUID
        elif key == "source_uid":
            assert value == udm_obj.props.ucsschoolSourceUID
        elif key == "udm_properties":
            for prop, prop_val in value.items():
                assert prop_val == getattr(udm_obj.props, prop)
        elif key == "roles":
            api_roles = set([role.split("/")[-1] for role in value])
            lib_roles = set(
                [
                    SchoolUserRole.from_lib_role(role).value
                    for role in lib_user.ucsschool_roles
                ]
            )
            assert api_roles == lib_roles
        elif key == "birthday":
            if value:
                assert str(value) == getattr(lib_user, key)
            else:
                assert value == getattr(lib_user, key)
        elif key == "school_classes":
            if isinstance(lib_user, Staff):
                assert value == {}
            for school, classes in value.items():
                assert school in lib_user.school_classes
                assert set(classes) == set(
                    kls.replace(f"{school}-", "")
                    for kls in lib_user.school_classes[school]
                )
        else:
            assert value == getattr(lib_user, key)


def compare_ldap_json_obj(dn, json_resp, url_fragment):  # noqa: C901
    import univention.admin.uldap

    lo, pos = univention.admin.uldap.getAdminConnection()
    ldap_obj = lo.get(dn)
    # assert True is False
    for attr, value in json_resp.items():
        if attr == "record_uid" and "ucsschoolRecordUID" in ldap_obj:
            assert value == ldap_obj["ucsschoolRecordUID"][0].decode("utf-8")
        elif attr == "ucsschool_roles" and "ucsschoolRole" in ldap_obj:
            assert value[0] == ldap_obj["ucsschoolRole"][0].decode("utf-8")
        elif attr == "email" and "mail" in ldap_obj:
            assert value == ldap_obj["mail"][0].decode("utf-8")
        elif attr == "source_uid" and "ucsschoolSourceUID" in ldap_obj:
            assert value == ldap_obj["ucsschoolSourceUID"][0].decode("utf-8")
        elif attr == "birthday" and "univentionBirthday" in ldap_obj:
            assert value == ldap_obj["univentionBirthday"][0].decode("utf-8")
        elif attr == "firstname" and "givenName" in ldap_obj:
            assert value == ldap_obj["givenName"][0].decode("utf-8")
        elif attr == "lastname" and "sn" in ldap_obj:
            assert value == ldap_obj["sn"][0].decode("utf-8")
        elif attr == "school" and "ucsschoolSchool" in ldap_obj:
            assert value.split("/")[-1] == ldap_obj["ucsschoolSchool"][0].decode(
                "utf-8"
            )
        elif attr == "udm_properties":
            for k, v in json_resp["udm_properties"].items():
                if k == "organisation" and "o" in ldap_obj:
                    assert v == ldap_obj["o"][0].decode("utf-8")
                    continue
                if k == "phone" and "telephoneNumber" in ldap_obj:
                    for p1, p2 in zip(v, ldap_obj["telephoneNumber"]):
                        assert p1 == p2.decode("utf-8")
                    continue
                if type(v) is str:
                    assert ldap_obj[k][0].decode("utf-8") == v
                if type(v) is int:
                    assert int(ldap_obj[k][0].decode("utf-8")) == v


@pytest.mark.asyncio
async def test_search_no_filter(
    auth_header, url_fragment, create_random_users, udm_kwargs
):
    users = await create_random_users(
        {"student": 2, "teacher": 2, "staff": 2, "teacher_and_staff": 2}
    )
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL")
        assert {u.name for u in users}.issubset(u.name for u in lib_users)
        response = requests.get(
            f"{url_fragment}/users",
            headers=auth_header,
            params={"school": "DEMOSCHOOL"},
        )
        assert response.status_code == 200, response.reason
        api_users = {data["name"]: UserModel(**data) for data in response.json()}
        assert len(api_users) == len(lib_users)
        assert {u.name for u in users}.issubset(api_users.keys())
        json_resp = response.json()
        for lib_user in lib_users:
            api_user = api_users[lib_user.name]
            await compare_lib_api_user(lib_user, api_user, udm, url_fragment)
            resp = [r for r in json_resp if r["dn"] == api_user.dn][0]
            compare_ldap_json_obj(api_user.dn, resp, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filter_param",
    (
        "email",
        "record_uid",
        "source_uid",
        "birthday",
        "disabled",
        "firstname",
        "lastname",
        "roles_staff",
        "roles_student",
        "roles_teacher",
        "roles_teacher_and_staff",
        "school",
    ),
)
async def test_search_filter(
    auth_header,
    url_fragment,
    create_random_users,
    udm_kwargs,
    random_name,
    create_random_schools,
    import_config,
    filter_param: str,
):
    if filter_param.startswith("roles_"):
        filter_param, role = filter_param.split("_", 1)
    else:
        role = random.choice(("staff", "student", "teacher", "teacher_and_staff"))
    if filter_param == "source_uid":
        create_kwargs = {"source_uid": random_name()}
    elif filter_param == "disabled":
        create_kwargs = {"disabled": random.choice((True, False))}
    elif filter_param == "school":
        schools = await create_random_schools(2)
        school1_dn, school1_attr = schools[0]
        school2_dn, school2_attr = schools[1]
        school1_url = f"{url_fragment}/schools/{school1_attr['name']}"
        school2_url = f"{url_fragment}/schools/{school2_attr['name']}"
        create_kwargs = {"school": school2_url, "schools": [school1_url, school2_url]}
    else:
        create_kwargs = {}
    user = (await create_random_users({role: 1}, **create_kwargs))[0]
    school = user.school.rsplit("/", 1)[-1]
    async with UDM(**udm_kwargs) as udm:
        import_user: ImportUser = (
            await ImportUser.get_all(udm, school, filter_str=f"uid={user.name}")
        )[0]
        assert user.name == import_user.name
        assert import_user.role_sting == role  # TODO: add 'r' when #47210 is fixed
        if filter_param == "school":
            assert school == school2_attr['name']
            assert set(school.rsplit("/", 1)[-1] for school in user.schools) == {school1_attr['name'], school2_attr['name']}

        param_value = getattr(import_user, filter_param)
        if filter_param in ("source_uid", "disabled"):
            assert param_value == create_kwargs[filter_param]
        elif filter_param == "roles":
            param_value = ["student" if p == "pupil" else p for p in param_value]
        elif filter_param == "school":
            param_value = school2_attr["name"]

        if filter_param == "roles":
            # list instead of dict for using same key ("roles") twice
            params = [(filter_param, pv) for pv in param_value]
        else:
            params = {filter_param: param_value}
        response = requests.get(
            f"{url_fragment}/users", headers=auth_header, params=params,
        )
        assert response.status_code == 200, response.reason
        json_resp = response.json()
        api_users = {data["name"]: UserModel(**data) for data in json_resp}
        if filter_param not in ("disabled", "roles", "school"):
            assert len(api_users) == 1
        assert user.name in api_users
        api_user = api_users[user.name]
        await compare_lib_api_user(import_user, api_user, udm, url_fragment)
        resp = [r for r in json_resp if r["dn"] == api_user.dn][0]
        compare_ldap_json_obj(api_user.dn, resp, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filter_param", MAPPED_UDM_PROPERTIES,
)
async def test_search_filter_udm_properties(
    auth_header,
    url_fragment,
    create_random_users,
    import_config,
    udm_kwargs,
    random_name,
    filter_param: str,
):
    if filter_param in ("title", "description", "employeeType", "organisation"):
        filter_value = random_name()
        create_kwargs = {"udm_properties": {filter_param: filter_value}}
    elif filter_param == "phone":
        filter_value = random_name()
        create_kwargs = {
            "udm_properties": {
                filter_param: [random_name(), filter_value, random_name()]
            }
        }
    else:
        create_kwargs = {}
    role = random.choice(("student", "teacher", "staff", "teacher_and_staff"))
    user = (await create_random_users({role: 1}, **create_kwargs))[0]
    async with UDM(**udm_kwargs) as udm:
        import_user: ImportUser = (
            await ImportUser.get_all(udm, "DEMOSCHOOL", filter_str=f"uid={user.name}")
        )[0]
        assert user.name == import_user.name
        assert import_user.role_sting == role  # TODO: add 'r' when #47210 is fixed
        udm_user = await import_user.get_udm_object(udm)
        if filter_param in ("uidNumber", "gidNumber"):
            filter_value = udm_user.props[filter_param]
        elif filter_param == "phone":
            assert set(udm_user.props[filter_param]) == set(
                create_kwargs["udm_properties"][filter_param]
            )
        else:
            assert (
                udm_user.props[filter_param]
                == create_kwargs["udm_properties"][filter_param]
            )
        params = {filter_param: filter_value}
        response = requests.get(
            f"{url_fragment}/users", headers=auth_header, params=params,
        )
        assert response.status_code == 200, response.reason
        api_users = {data["name"]: UserModel(**data) for data in response.json()}
        if filter_param != "gidNumber":
            assert len(api_users) == 1
        assert user.name in api_users
        api_user = api_users[user.name]
        created_value = api_user.udm_properties[filter_param]
        if filter_param == "phone":
            assert set(created_value) == set(
                create_kwargs["udm_properties"][filter_param]
            )
        else:
            assert created_value == filter_value
        await compare_lib_api_user(import_user, api_user, udm, url_fragment)
        json_resp = response.json()
        resp = [r for r in json_resp if r["dn"] == api_user.dn][0]
        compare_ldap_json_obj(api_user.dn, resp, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_get(
    auth_header,
    url_fragment,
    create_random_users,
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
):
    create_kwargs = {
        "udm_properties": {
            "title": random_name(),
            "description": random_name(),
            "employeeType": random_name(),
            "organisation": random_name(),
            "phone": [random_name(), random_name()],
        }
    }
    user = (await create_random_users({role.name: 1}, **create_kwargs))[0]
    async with UDM(**udm_kwargs) as udm:
        lib_users = await ImportUser.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        response = requests.get(
            f"{url_fragment}/users/{user.name}", headers=auth_header
        )
        assert response.status_code == 200, response.reason
        api_user = UserModel(**response.json())
        for k, v in create_kwargs["udm_properties"].items():
            if isinstance(v, (tuple, list)):
                assert set(api_user.udm_properties.get(k, [])) == set(v)
            else:
                assert api_user.udm_properties.get(k) == v
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
        json_resp = response.json()
        if type(json_resp) is list:
            json_resp = [resp for resp in json_resp if resp["dn"] == api_user.dn][0]
        compare_ldap_json_obj(api_user.dn, json_resp, url_fragment)


@pytest.mark.asyncio
async def test_get_empty_udm_properties_are_returned(
    auth_header, url_fragment, create_random_users, import_config, udm_kwargs,
):
    role: Role = random.choice(USER_ROLES)
    create_kwargs = {"udm_properties": {}}
    user = (await create_random_users({role.name: 1}, **create_kwargs))[0]
    response = requests.get(f"{url_fragment}/users/{user.name}", headers=auth_header)
    assert response.status_code == 200, response.reason
    api_user = UserModel(**response.json())
    for prop in import_config["mapped_udm_properties"]:
        assert prop in api_user.udm_properties


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_create(
    auth_header,
    url_fragment,
    create_random_user_data,
    random_name,
    import_config,
    udm_kwargs,
    schedule_delete_user,
    role: Role,
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    r_user = await create_random_user_data(
        roles=[f"{url_fragment}/roles/{role_}" for role_ in roles]
    )
    title = random_name()
    r_user.udm_properties["title"] = title
    phone = [random_name(), random_name()]
    r_user.udm_properties["phone"] = phone
    data = r_user.json()
    print(f"POST data={data!r}")
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 0
        schedule_delete_user(r_user.name)
        response = requests.post(
            f"{url_fragment}/users/",
            headers={"Content-Type": "application/json", **auth_header},
            data=data,
        )
        assert response.status_code == 201, f"{response.__dict__!r}"
        response_json = response.json()
        api_user = UserModel(**response_json)
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        assert api_user.udm_properties["title"] == title
        assert set(api_user.udm_properties["phone"]) == set(phone)
        udm_props = (await lib_users[0].get_udm_object(udm)).props
        assert udm_props.title == title
        assert set(udm_props.phone) == set(phone)
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
        json_resp = response.json()
        compare_ldap_json_obj(api_user.dn, json_resp, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_create_without_username(
    auth_header,
    url_fragment,
    create_random_user_data,
    random_name,
    import_config,
    reset_import_config,
    udm_kwargs,
    add_to_import_config,
    schedule_delete_user,
    role: Role,
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    r_user = await create_random_user_data(
        roles=[f"{url_fragment}/roles/{role_}" for role_ in roles]
    )
    r_user.name = ""
    data = r_user.json()
    print(f"POST data={data!r}")
    expected_name = f"test.{r_user.firstname[:2]}.{r_user.lastname[:3]}".lower()
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={expected_name}")
        assert len(lib_users) == 0
        schedule_delete_user(expected_name)
        response = requests.post(
            f"{url_fragment}/users/",
            headers={"Content-Type": "application/json", **auth_header},
            data=data,
        )
        assert response.status_code == 201, f"{response.__dict__!r}"
        response_json = response.json()
        api_user = UserModel(**response_json)
        assert api_user.name == expected_name
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={expected_name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_put(
    auth_header,
    url_fragment,
    create_random_users,
    create_random_user_data,
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
):
    user = (await create_random_users({role.name: 1}))[0]
    new_user_data = (await create_random_user_data(roles=user.roles)).dict()
    del new_user_data["name"]
    del new_user_data["record_uid"]
    del new_user_data["source_uid"]
    title = random_name()
    phone = [random_name(), random_name()]
    new_user_data["udm_properties"] = {"title": title, "phone": phone}
    modified_user = UserCreateModel(**{**user.dict(), **new_user_data})
    response = requests.put(
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
        data=modified_user.json(),
    )
    assert response.status_code == 200, response.reason
    api_user = UserModel(**response.json())
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        assert api_user.udm_properties["title"] == title
        assert set(api_user.udm_properties["phone"]) == set(phone)
        udm_props = (await lib_users[0].get_udm_object(udm)).props
        assert udm_props.title == title
        assert set(udm_props.phone) == set(phone)
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
        json_resp = response.json()
        compare_ldap_json_obj(api_user.dn, json_resp, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_patch(
    auth_header,
    url_fragment,
    create_random_users,
    create_random_user_data,
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
):
    user = (await create_random_users({role.name: 1}))[0]
    new_user_data = (await create_random_user_data(roles=user.roles)).dict()
    del new_user_data["name"]
    del new_user_data["record_uid"]
    del new_user_data["source_uid"]
    for key in random.sample(
        new_user_data.keys(), random.randint(1, len(new_user_data.keys()))
    ):
        del new_user_data[key]
    title = random_name()
    phone = [random_name(), random_name()]
    new_user_data["udm_properties"] = {"title": title, "phone": phone}
    patch_user = UserPatchModel(**new_user_data)
    response = requests.patch(
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
        data=patch_user.json(),
    )
    assert response.status_code == 200, response.reason
    api_user = UserModel(**response.json())
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        assert api_user.udm_properties["title"] == title
        assert set(api_user.udm_properties["phone"]) == set(phone)
        udm_props = (await lib_users[0].get_udm_object(udm)).props
        assert udm_props.title == title
        assert set(udm_props.phone) == set(phone)
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
        json_resp = response.json()
        compare_ldap_json_obj(api_user.dn, json_resp, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_delete(
    auth_header, url_fragment, create_random_users, udm_kwargs, role: Role
):
    r_user = (await create_random_users({role.name: 1}))[0]
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        response = requests.delete(
            f"{url_fragment}/users/{r_user.name}", headers=auth_header,
        )
        assert response.status_code == 204, response.reason
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 0


def test_delete_non_existent(auth_header, url_fragment, random_name):
    response = requests.delete(
        f"{url_fragment}/users/{random_name}", headers=auth_header,
    )
    assert response.status_code == 404, response.reason


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("method", ("patch", "put"))
async def test_rename(
    auth_header,
    url_fragment,
    create_random_users,
    create_random_user_data,
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
    method: str,
    schedule_delete_user,
):
    if method == "patch":
        user = (await create_random_users({role.name: 1}))[0]
        new_name = f"t.new.{random_name()}.{random_name()}"
        schedule_delete_user(new_name)
        response = requests.patch(
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            json={"name": new_name},
        )
    elif method == "put":
        user_data = (
            await create_random_user_data(roles=[url_fragment, url_fragment])
        ).dict()
        del user_data["roles"]
        user = (await create_random_users({role.name: 1}, **user_data))[0]
        new_name = f"t.new.{random_name()}.{random_name()}"
        old_data = user.dict()
        del old_data["name"]
        modified_user = UserCreateModel(name=new_name, **old_data)
        response = requests.put(
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            data=modified_user.json(),
        )
    assert (
        response.status_code == 200
    ), f"{response.reason} -- {response.content[:4096]}"
    api_user = UserModel(**response.json())
    assert api_user.name == new_name
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
        assert len(lib_users) == 0
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={new_name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("method", ("patch", "put"))
async def test_school_change(
    auth_header,
    url_fragment,
    create_random_users,
    create_random_schools,
    udm_kwargs,
    role: Role,
    method: str,
):
    schools = await create_random_schools(2)
    school1_dn, school1_attr = schools[0]
    school2_dn, school2_attr = schools[1]
    user = (
        await create_random_users(
            {role.name: 1}, school=f"{url_fragment}/schools/{school1_attr['name']}"
        )
    )[0]
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(
            udm, school1_attr["name"], f"username={user.name}"
        )
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        assert lib_users[0].school == school1_attr["name"]
        assert lib_users[0].schools == [school1_attr["name"]]
        if role.name == "teacher_and_staff":
            roles = {
                f"staff:school:{school1_attr['name']}",
                f"teacher:school:{school1_attr['name']}",
            }
        else:
            roles = {f"{role.name}:school:{school1_attr['name']}"}
        assert set(lib_users[0].ucsschool_roles) == roles
        url = f"{url_fragment}/schools/{school2_attr['name']}"
        _url: SplitResult = urlsplit(url)
        new_school_url = HttpUrl(
            url, path=_url.path, scheme=_url.scheme, host=_url.netloc
        )
        if method == "patch":
            patch_model = UserPatchModel(
                school=new_school_url, schools=[new_school_url]
            )
            patch_data = patch_model.dict()
            response = requests.patch(
                f"{url_fragment}/users/{user.name}",
                headers=auth_header,
                json=patch_data,
            )
        elif method == "put":
            old_data = user.dict()
            del old_data["school"]
            del old_data["schools"]
            del old_data["school_classes"]
            modified_user = UserCreateModel(
                school=new_school_url, schools=[new_school_url], **old_data
            )
            response = requests.put(
                f"{url_fragment}/users/{user.name}",
                headers=auth_header,
                data=modified_user.json(),
            )
        json_response = response.json()
        assert response.status_code == 200, response.reason
        async for udm_user in udm.get("users/user").search(
            filter_format("uid=%s", (user.name,))
        ):
            udm_user_schools = udm_user.props.school
            assert udm_user_schools == [school2_attr["name"]]
        api_user = UserModel(**json_response)
        assert (
            api_user.unscheme_and_unquote(str(api_user.school))
            == f"{url_fragment}/schools/{school2_attr['name']}"
        )
        lib_users = await User.get_all(
            udm, school2_attr["name"], f"username={user.name}"
        )
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        assert lib_users[0].school == school2_attr["name"]
        assert lib_users[0].schools == [school2_attr["name"]]
        if role.name == "teacher_and_staff":
            roles = {
                f"staff:school:{school2_attr['name']}",
                f"teacher:school:{school2_attr['name']}",
            }
        else:
            roles = {f"{role.name}:school:{school2_attr['name']}"}
        assert set(lib_users[0].ucsschool_roles) == roles
