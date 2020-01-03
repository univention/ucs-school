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
from ucsschool.lib.models.base import NoObject
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
                assert value == getattr(udm_obj.props, key)
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
async def test_search_no_filter(
    auth_header, url_fragment, create_random_users, udm_kwargs
):
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
        assert response.status_code == 200, response.reason
        api_users = {data["name"]: UserModel(**data) for data in response.json()}
        assert len(api_users) == len(lib_users)
        assert {u.name for u in users}.issubset(api_users.keys())
        for lib_user in lib_users:
            api_user = api_users[lib_user.name]
            await compare_lib_api_user(lib_user, api_user, udm, url_fragment)


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
    user = create_random_users({role: 1}, **create_kwargs)[0]
    async with UDM(**udm_kwargs) as udm:
        import_user: ImportUser = (
            await ImportUser.get_all(udm, "DEMOSCHOOL", filter_str=f"uid={user.name}")
        )[0]
        assert user.name == import_user.name
        assert import_user.role_sting == role  # TODO: add 'r' when #47210 is fixed

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
        api_users = {data["name"]: UserModel(**data) for data in response.json()}
        if filter_param not in ("disabled", "roles", "school"):
            assert len(api_users) == 1
        assert user.name in api_users
        api_user = api_users[user.name]
        await compare_lib_api_user(import_user, api_user, udm, url_fragment)


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
        create_kwargs = {"udm_properties": {filter_param: [random_name(), filter_value, random_name()]}}
    else:
        create_kwargs = {}
    role = random.choice(("student", "teacher", "staff", "teacher_and_staff"))
    user = create_random_users({role: 1}, **create_kwargs)[0]
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
            assert set(udm_user.props[filter_param]) == set(create_kwargs["udm_properties"][filter_param])
        else:
            assert udm_user.props[filter_param] == create_kwargs["udm_properties"][filter_param]
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
            assert set(created_value) == set(create_kwargs["udm_properties"][filter_param])
        else:
            assert created_value == filter_value
        await compare_lib_api_user(import_user, api_user, udm, url_fragment)


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
    user = create_random_users({role.name: 1}, **create_kwargs)[0]
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


def test_get_empty_udm_properties_are_returned(
    auth_header,
    url_fragment,
    create_random_users,
    random_name,
    import_config,
    udm_kwargs,
):
    role: Role = random.choice(USER_ROLES)
    create_kwargs = {"udm_properties": {}}
    user = create_random_users({role.name: 1}, **create_kwargs)[0]
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
    role: Role,
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    r_user = create_random_user_data(
        roles=[f"{url_fragment}/roles/{role_}" for role_ in roles]
    )
    title = random_name()
    r_user.udm_properties["title"] = title
    phone = [random_name(), random_name()]
    r_user.udm_properties["phone"] = phone
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
        assert api_user.udm_properties["title"] == title
        assert set(api_user.udm_properties["phone"]) == set(phone)
        udm_props = (await lib_users[0].get_udm_object(udm)).props
        assert udm_props.title == title
        assert set(udm_props.phone) == set(phone)
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
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
):
    user = create_random_users({role.name: 1})[0]
    new_user_data = create_random_user_data(roles=user.roles).dict()
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
    assert response.status_code == 200
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
    user = create_random_users({role.name: 1})[0]
    new_user_data = create_random_user_data(roles=user.roles).dict()
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
    assert response.status_code == 200
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
