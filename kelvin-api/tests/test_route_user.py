import random
from typing import List, NamedTuple, Type, Union
from urllib.parse import SplitResult, urlsplit

import pytest
import requests
from ldap.filter import filter_format
from pydantic import HttpUrl

import ucsschool.kelvin.constants
from ucsschool.kelvin.routers.role import SchoolUserRole
from ucsschool.kelvin.routers.user import UserCreateModel, UserModel, UserPatchModel
from ucsschool.lib.models.base import NoObject
from ucsschool.lib.models.user import Staff, Student, Teacher, TeachersAndStaff, User
from udm_rest_client import UDM

pytestmark = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)

UserType = Type[Union[Staff, Student, Teacher, TeachersAndStaff, User]]
Role = NamedTuple("Role", [("name", str), ("klass", UserType)])
USER_ROLES: List[Role] = [
    Role("staff", Staff),
    Role("student", Student),
    Role("teacher", Teacher),
    Role("teacher_and_staff", TeachersAndStaff),
]
random.shuffle(USER_ROLES)


def role_id(value: Role) -> str:
    return value.name


async def compare_lib_api_user(lib_user, api_user, udm, url_fragment):  # noqa: C901
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
            for key, value in value.items():
                assert value == getattr(udm_obj, key)
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
        else:
            assert value == getattr(lib_user, key)


@pytest.mark.asyncio
async def test_search(auth_header, url_fragment, create_random_users, udm_kwargs):
    users = create_random_users(
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
        api_users = {data["name"]: UserModel(**data) for data in response.json()}
        assert len(api_users.keys()) == len(lib_users)
        assert {u.name for u in users}.issubset(api_users.keys())
        for lib_user in lib_users:
            api_user = api_users[lib_user.name]
            await compare_lib_api_user(lib_user, api_user, udm, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_get(
    auth_header, url_fragment, create_random_users, udm_kwargs, role: Role
):
    user = create_random_users({role.name: 1})[0]
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        response = requests.get(
            f"{url_fragment}/users/{user.name}", headers=auth_header
        )
        assert isinstance(response.json(), dict)
        api_user = UserModel(**response.json())
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_create(
    auth_header, url_fragment, create_random_user_data, udm_kwargs, role: Role
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    r_user = create_random_user_data(
        roles=[f"{url_fragment}/roles/{role_}" for role_ in roles]
    )
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 0
        response = requests.post(
            f"{url_fragment}/users/",
            headers={"Content-Type": "application/json", **auth_header},
            data=r_user.json(),
        )
        api_user = UserModel(**response.json())
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
        requests.delete(
            f"{url_fragment}/users/{r_user.name}", headers=auth_header,
        )
        with pytest.raises(NoObject):
            await User.from_dn(lib_users[0].dn, lib_users[0].school, udm)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_put(
    auth_header,
    url_fragment,
    create_random_users,
    create_random_user_data,
    udm_kwargs,
    role: Role,
):
    user = create_random_users({role.name: 1})[0]
    new_user_data = create_random_user_data(roles=user.roles).dict()
    del new_user_data["name"]
    del new_user_data["record_uid"]
    del new_user_data["source_uid"]
    modified_user = UserCreateModel(**{**user.dict(), **new_user_data})
    response = requests.put(
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
        data=modified_user.json(),
    )
    assert response.status_code == 200
    api_user = UserModel(**response.json())
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_patch(
    auth_header,
    url_fragment,
    create_random_users,
    create_random_user_data,
    udm_kwargs,
    role: Role,
):
    user = create_random_users({role.name: 1})[0]
    new_user_data = create_random_user_data(roles=user.roles).dict()
    del new_user_data["name"]
    del new_user_data["record_uid"]
    del new_user_data["source_uid"]
    for key in random.sample(
        new_user_data.keys(), random.randint(1, len(new_user_data.keys()))
    ):
        del new_user_data[key]
    patch_user = UserPatchModel(**new_user_data)
    response = requests.patch(
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
        data=patch_user.json(),
    )
    assert response.status_code == 200
    api_user = UserModel(**response.json())
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_school_change(
    auth_header,
    url_fragment,
    create_random_users,
    create_random_schools,
    udm_kwargs,
    role: Role,
):
    schools = await create_random_schools(2)
    school1_dn, school1_attr = schools[0]
    school2_dn, school2_attr = schools[1]
    user = create_random_users(
        {role.name: 1}, school=f"{url_fragment}/schools/{school1_attr['name']}"
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
        new_school_url = HttpUrl(url, scheme=_url.scheme, host=_url.netloc)
        patch_model = UserPatchModel(school=new_school_url, schools=[new_school_url])
        patch_data = patch_model.dict()
        response = requests.patch(
            f"{url_fragment}/users/{user.name}", headers=auth_header, json=patch_data,
        )
        json_response = response.json()
        assert response.status_code == 200
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


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_delete(
    auth_header, url_fragment, create_random_users, udm_kwargs, role: Role
):
    r_user = create_random_users({role.name: 1})[0]
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        response = requests.delete(
            f"{url_fragment}/users/{r_user.name}", headers=auth_header,
        )
        assert response.status_code == 204
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 0


def test_delete_non_existent(auth_header, url_fragment, random_name):
    response = requests.delete(
        f"{url_fragment}/users/{random_name}", headers=auth_header,
    )
    assert response.status_code == 404
