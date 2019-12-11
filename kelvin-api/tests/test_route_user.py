import requests
import pytest
import random
import ucsschool.kelvin.constants
from ucsschool.kelvin.ldap_access import udm_kwargs
from ucsschool.kelvin.routers.role import SchoolUserRole
from ucsschool.kelvin.routers.user import UserModel, UserCreateModel, UserPatchModel
from ucsschool.lib.models.user import User
from udm_rest_client import UDM


must_run_in_container = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)


async def compare_lib_api_user(lib_user, api_user, udm, url_fragment):
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
        elif key == "role":
            assert (
                value.split("/")[-1]
                == SchoolUserRole.from_lib_roles(lib_user.ucsschool_roles).value
            )
        elif key == "birthday":
            if value:
                assert str(value) == getattr(lib_user, key)
            else:
                assert value == getattr(lib_user, key)
        else:
            assert value == getattr(lib_user, key)


@must_run_in_container
@pytest.mark.asyncio
async def test_search(auth_header, url_fragment, create_random_users):
    create_random_users(
        {"student": 2, "teacher": 2, "staff": 2, "teachers_and_staff": 2}
    )
    async with UDM(**await udm_kwargs()) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL")
        response = requests.get(
            f"{url_fragment}/users",
            headers=auth_header,
            params={"school_filter": "DEMOSCHOOL"},
        )
        api_users = {data["name"]: UserModel(**data) for data in response.json()}
        assert len(api_users.keys()) == len(lib_users)
        for lib_user in lib_users:
            api_user = api_users[lib_user.name]
            await compare_lib_api_user(lib_user, api_user, udm, url_fragment)


@must_run_in_container
@pytest.mark.asyncio
async def test_get(auth_header, url_fragment, create_random_users):
    users = create_random_users(
        {"student": 2, "teacher": 2, "staff": 2, "teachers_and_staff": 2}
    )
    async with UDM(**await udm_kwargs()) as udm:
        for user in users:
            lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
            assert len(lib_users) == 1
            response = requests.get(
                f"{url_fragment}/users/{user.name}", headers=auth_header
            )
            assert type(response.json()) == dict
            api_user = UserModel(**response.json())
            await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)


@must_run_in_container
@pytest.mark.asyncio
async def test_create(auth_header, url_fragment, create_random_user_data):
    async with UDM(**await udm_kwargs()) as udm:
        r_user = create_random_user_data("student")
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
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
        requests.delete(
            f"{url_fragment}/users/{r_user.name}",
            headers=auth_header,
            data=r_user.json(),
        )


@must_run_in_container
@pytest.mark.asyncio
async def test_put(
    auth_header, url_fragment, create_random_users, create_random_user_data
):
    users = create_random_users(
        {"student": 2, "teacher": 2, "staff": 2, "teachers_and_staff": 2}
    )
    async with UDM(**await udm_kwargs()) as udm:
        for user in users:
            new_user_data = create_random_user_data(user.role.split("/")[-1]).dict()
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
            lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
            assert len(lib_users) == 1
            await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)


@must_run_in_container
@pytest.mark.asyncio
async def test_patch(auth_header, url_fragment, create_random_users, create_random_user_data):
    users = create_random_users(
        {"student": 2, "teacher": 2, "staff": 2, "teachers_and_staff": 2}
    )
    async with UDM(**await udm_kwargs()) as udm:
        for user in users:
            new_user_data = create_random_user_data(user.role.split("/")[-1]).dict()
            del new_user_data["name"]
            del new_user_data["record_uid"]
            del new_user_data["source_uid"]
            for key in random.sample(new_user_data.keys(), random.randint(1, len(new_user_data.keys()))):
                del new_user_data[key]
            patch_user = UserPatchModel(**new_user_data)
            response = requests.patch(f"{url_fragment}/users/{user.name}", headers=auth_header, data=patch_user.json())
            assert response.status_code == 200
            api_user = UserModel(**response.json())
            lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={user.name}")
            assert len(lib_users) == 1
            await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)


@must_run_in_container
@pytest.mark.asyncio
async def test_delete(auth_header, url_fragment, create_random_user_data):
    async with UDM(**await udm_kwargs()) as udm:
        r_user = create_random_user_data("student")
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 0
        response = requests.post(
            f"{url_fragment}/users/",
            headers={"Content-Type": "application/json", **auth_header},
            data=r_user.json(),
        )
        assert response.status_code == 201
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 1
        response = requests.delete(
            f"{url_fragment}/users/{r_user.name}",
            headers=auth_header,
            data=r_user.json(),
        )
        assert response.status_code == 204
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
        assert len(lib_users) == 0
        response = requests.delete(
            f"{url_fragment}/users/NON_EXISTENT_USER",
            headers=auth_header,
            data=r_user.json(),
        )
        assert response.status_code == 404
