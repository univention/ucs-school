# Copyright 2020-2021 Univention GmbH
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
import datetime
import itertools
import random
import time
from typing import Any, Dict, List, NamedTuple, Tuple, Type, Union
from urllib.parse import SplitResult, urlsplit

import pytest
import requests
from conftest import MAPPED_UDM_PROPERTIES
from faker import Faker
from ldap3.core.exceptions import LDAPBindError
from ldap.filter import filter_format
from pydantic import HttpUrl

import ucsschool.kelvin.constants
import ucsschool.kelvin.ldap_access
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.kelvin.routers.role import SchoolUserRole
from ucsschool.kelvin.routers.user import (
    PasswordsHashes,
    UserCreateModel,
    UserModel,
    UserPatchModel,
    set_password_hashes,
)
from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import Staff, Student, Teacher, TeachersAndStaff, User
from ucsschool.lib.models.utils import env_or_ucr
from udm_rest_client import UDM

pytestmark = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)

fake = Faker()
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


def two_roles_id(value: List[Role]) -> str:
    return f"{value[0].name} -> {value[1].name}"


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
            assert api_user.unscheme_and_unquote(value) == f"{url_fragment}/users/{lib_user.name}"
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
                [SchoolUserRole.from_lib_role(role).value for role in lib_user.ucsschool_roles]
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
                    kls.replace(f"{school}-", "") for kls in lib_user.school_classes[school]
                )
        else:
            lib_user_value = getattr(lib_user, key)
            if isinstance(value, (list, set, tuple)) or isinstance(lib_user_value, (list, set, tuple)):
                assert set(value) == set(lib_user_value)
            else:
                assert value == lib_user_value


def compare_ldap_json_obj(dn, json_resp, url_fragment):  # noqa: C901
    import univention.admin.uldap

    lo, pos = univention.admin.uldap.getAdminConnection()
    ldap_obj = lo.get(dn)
    for attr, value in json_resp.items():
        if attr == "record_uid" and "ucsschoolRecordUID" in ldap_obj:
            assert value == ldap_obj["ucsschoolRecordUID"][0].decode("utf-8")
        elif attr == "ucsschool_roles" and "ucsschoolRole" in ldap_obj:
            assert set(value) == set(r.decode("utf-8") for r in ldap_obj["ucsschoolRole"])
        elif attr == "email" and "mailPrimaryAddress" in ldap_obj:
            assert value in [o.decode("utf-8") for o in ldap_obj["mail"]]
            assert value in [o.decode("utf-8") for o in ldap_obj["mailPrimaryAddress"]]
        elif attr == "source_uid" and "ucsschoolSourceUID" in ldap_obj:
            assert value == ldap_obj["ucsschoolSourceUID"][0].decode("utf-8")
        elif attr == "birthday" and "univentionBirthday" in ldap_obj:
            assert value == ldap_obj["univentionBirthday"][0].decode("utf-8")
        elif attr == "firstname" and "givenName" in ldap_obj:
            assert value == ldap_obj["givenName"][0].decode("utf-8")
        elif attr == "lastname" and "sn" in ldap_obj:
            assert value == ldap_obj["sn"][0].decode("utf-8")
        elif attr == "school" and "ucsschoolSchool" in ldap_obj:
            assert value.split("/")[-1] in [s.decode("utf-8") for s in ldap_obj["ucsschoolSchool"]]
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


@pytest.fixture
def import_user_to_create_model_kwargs(url_fragment):
    def _func(user: ImportUser, exclude: List[str] = None) -> Dict[str, Any]:
        user_data = user.to_dict()
        user_data["birthday"] = datetime.date.fromisoformat(user_data["birthday"])
        user_data["roles"] = [
            f"{url_fragment}/roles/{SchoolUserRole.from_lib_role(lib_role).value}"
            for lib_role in user_data["ucsschool_roles"]
        ]
        user_data["school_classes"] = {
            k: [klass.split("-", 1)[1] for klass in v] for k, v in user_data["school_classes"].items()
        }
        user_data["school"] = f"{url_fragment}/schools/{user_data['school']}"
        user_data["schools"] = [f"{url_fragment}/schools/{school}" for school in user_data["schools"]]
        exclude = exclude or []
        for attr in [
            "$dn$",
            "action",
            "display_name",
            "entry_count",
            "in_hook",
            "input_data",
            "objectType",
            "old_user",
            "type",
            "type_name",
        ] + exclude:
            del user_data[attr]
        return user_data

    return _func


@pytest.mark.asyncio
async def test_search_no_filter(
    auth_header, retry_http_502, url_fragment, new_school_users, create_ou_using_python, udm_kwargs
):
    ou_name = await create_ou_using_python()
    users: List[User] = await new_school_users(
        ou_name,
        {"student": 2, "teacher": 2, "staff": 2, "teacher_and_staff": 2},
        disabled=False,
    )
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, ou_name)
    assert {u.name for u in users}.issubset({u.name for u in lib_users})
    response = retry_http_502(
        requests.get,
        f"{url_fragment}/users",
        headers=auth_header,
        params={"school": ou_name},
    )
    assert response.status_code == 200, response.reason
    api_users = {data["name"]: UserModel(**data) for data in response.json()}
    assert len(api_users) == len(lib_users)
    assert {u.name for u in users}.issubset(set(api_users.keys()))
    json_resp = response.json()
    async with UDM(**udm_kwargs) as udm:
        for lib_user in lib_users:
            api_user = api_users[lib_user.name]
            await compare_lib_api_user(lib_user, api_user, udm, url_fragment)
            resp = [r for r in json_resp if r["dn"] == api_user.dn][0]
            compare_ldap_json_obj(api_user.dn, resp, url_fragment)


@pytest.mark.asyncio  # noqa: C901
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
async def test_search_filter(  # noqa: C901
    auth_header,
    retry_http_502,
    url_fragment,
    new_import_user,
    udm_kwargs,
    random_name,
    create_ou_using_python,
    import_config,
    filter_param: str,
):
    ou1_name = await create_ou_using_python()
    ou_name = ou1_name
    if filter_param.startswith("roles_"):
        filter_param, role = filter_param.split("_", 1)
    else:
        role = random.choice(("staff", "student", "teacher", "teacher_and_staff"))
    if filter_param == "source_uid":
        create_kwargs = {"source_uid": random_name()}
    elif filter_param == "disabled":
        create_kwargs = {"disabled": random.choice((True, False))}
    elif filter_param == "school":
        # use 2nd OU from cache, create_ou_using_python() returns a random OU from the cache
        while True:
            ou2_name = await create_ou_using_python()
            if ou1_name != ou2_name:
                break
        ou_name = ou2_name
        create_kwargs = {"schools": [ou1_name, ou2_name]}
    else:
        create_kwargs = {}

    user: ImportUser = await new_import_user(ou_name, role, **create_kwargs)
    assert ou_name == user.school
    assert user.role_sting == role  # TODO: add 'r' when #47210 is fixed
    if filter_param == "school":
        assert ou_name == ou2_name
        assert set(school.rsplit("/", 1)[-1] for school in user.schools) == {
            ou1_name,
            ou2_name,
        }

    param_value = getattr(user, filter_param)
    if filter_param in ("source_uid", "disabled"):
        assert param_value == create_kwargs[filter_param]
    elif filter_param == "roles":
        param_value = ["student" if p == "pupil" else p for p in param_value]
    elif filter_param == "school":
        param_value = ou2_name

    if filter_param == "roles":
        # list instead of dict for using same key ("roles") twice
        params = [(filter_param, pv) for pv in param_value]
    else:
        params = {filter_param: param_value}
    response = retry_http_502(
        requests.get,
        f"{url_fragment}/users",
        headers=auth_header,
        params=params,
    )
    assert response.status_code == 200, response.reason
    json_resp = response.json()
    api_users = {
        data["name"]: UserModel(**data) for data in json_resp if data["school"].endswith(ou_name)
    }
    if filter_param not in ("disabled", "roles", "school"):
        assert len(api_users) == 1
    assert user.name in api_users
    api_user = api_users[user.name]
    async with UDM(**udm_kwargs) as udm:
        await compare_lib_api_user(user, api_user, udm, url_fragment)
    resp = [r for r in json_resp if r["dn"] == api_user.dn][0]
    compare_ldap_json_obj(api_user.dn, resp, url_fragment)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filter_param",
    MAPPED_UDM_PROPERTIES,
)
async def test_search_filter_udm_properties(
    auth_header,
    create_ou_using_python,
    retry_http_502,
    url_fragment,
    new_import_user,
    import_config,
    udm_kwargs,
    random_name,
    filter_param: str,
):
    if filter_param in ("description", "displayName", "employeeType", "organisation", "title"):
        filter_value = random_name()
        create_kwargs = {"udm_properties": {filter_param: filter_value}}
    elif filter_param == "e-mail":
        domainname = env_or_ucr("domainname")
        email1 = f"{random_name()}mail{fake.pyint()}@{domainname}".lower()
        filter_value = f"{random_name()}mail{fake.pyint()}@{domainname}".lower()
        email3 = f"{random_name()}mail{fake.pyint()}@{domainname}".lower()
        create_kwargs = {
            "email": filter_value,
            "udm_properties": {filter_param: [email1, filter_value, email3]},
        }
    elif filter_param == "phone":
        filter_value = random_name()
        create_kwargs = {"udm_properties": {filter_param: [random_name(), filter_value, random_name()]}}
    else:
        create_kwargs = {}
    role = random.choice(("student", "teacher", "staff", "teacher_and_staff"))
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, role, **create_kwargs)
    assert user.role_sting == role  # TODO: add 'r' when #47210 is fixed
    async with UDM(**udm_kwargs) as udm:
        udm_user = await user.get_udm_object(udm)
    if filter_param in ("uidNumber", "gidNumber"):
        filter_value = udm_user.props[filter_param]
    elif filter_param in ("e-mail", "phone"):
        assert set(udm_user.props[filter_param]) == set(create_kwargs["udm_properties"][filter_param])
    else:
        assert udm_user.props[filter_param] == create_kwargs["udm_properties"][filter_param]
    params = {filter_param: filter_value}
    response = retry_http_502(
        requests.get,
        f"{url_fragment}/users",
        headers=auth_header,
        params=params,
    )
    assert response.status_code == 200, response.reason
    api_users = {data["name"]: UserModel(**data) for data in response.json()}
    if filter_param != "gidNumber":
        assert len(api_users) == 1
    assert user.name in api_users
    api_user = api_users[user.name]
    created_value = api_user.udm_properties[filter_param]
    if filter_param in ("e-mail", "phone"):
        assert set(created_value) == set(create_kwargs["udm_properties"][filter_param])
    else:
        assert created_value == filter_value
    await compare_lib_api_user(user, api_user, udm, url_fragment)
    json_resp = response.json()
    resp = [r for r in json_resp if r["dn"] == api_user.dn][0]
    compare_ldap_json_obj(api_user.dn, resp, url_fragment)


@pytest.mark.asyncio
async def test_search_user_without_firstname(
    auth_header, create_ou_using_python, retry_http_502, url_fragment, new_school_user, udm_kwargs
):
    role = random.choice(("student", "teacher", "staff", "teacher_and_staff"))
    school = await create_ou_using_python()
    lib_user: User = await new_school_user(school, role)
    assert lib_user.firstname
    response = retry_http_502(
        requests.get,
        f"{url_fragment}/users",
        headers=auth_header,
        params={"school": school},
    )
    assert response.status_code == 200, (response.reason, response.content)
    json_resp = response.json()
    assert any(u["firstname"] == lib_user.firstname for u in json_resp)
    # reading the user is OK at this point
    async with UDM(**udm_kwargs) as udm:
        udm_user = await udm.get("users/user").get(lib_user.dn)
        udm_user.props.firstname = ""
        await udm_user.save()
    # should fail now:
    response = retry_http_502(
        requests.get,
        f"{url_fragment}/users",
        headers=auth_header,
        params={"school": school},
    )
    assert response.status_code == 500, (response.reason, response.content)
    json_resp = response.json()
    assert lib_user.dn in json_resp["detail"]
    assert "firstname" in json_resp["detail"]
    assert "none is not an allowed value" in json_resp["detail"]


@pytest.mark.asyncio
async def test_search_returns_no_exam_user(
    auth_header, create_ou_using_python, retry_http_502, url_fragment, create_exam_user, udm_kwargs
):
    school = await create_ou_using_python()
    dn, exam_user = await create_exam_user(school)
    async with UDM(**udm_kwargs) as udm:
        lib_user: User = (await User.get_all(udm, school, filter_str=f"uid={exam_user['username']}"))[0]
    assert lib_user.name == exam_user["username"]
    assert lib_user.school == school
    assert lib_user.ucsschool_roles == exam_user["ucsschoolRole"]
    assert f"cn=examusers,ou={school}" in lib_user.dn

    response = retry_http_502(
        requests.get,
        f"{url_fragment}/users",
        headers=auth_header,
        params={"school": school},
    )
    assert response.status_code == 200, (response.reason, response.content)
    json_resp = response.json()
    assert not any(u["name"] == exam_user["username"] for u in json_resp)
    assert not any(role.startswith("exam") for user in json_resp for role in user["ucsschool_roles"])


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_get(
    auth_header,
    retry_http_502,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
):
    udm_properties = {
        "title": random_name(),
        "description": random_name(),
        "employeeType": random_name(),
        "organisation": random_name(),
        "phone": [random_name(), random_name()],
    }
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, role.name, udm_properties)
    assert isinstance(user, role.klass)
    response = retry_http_502(requests.get, f"{url_fragment}/users/{user.name}", headers=auth_header)
    assert response.status_code == 200, response.reason
    json_resp = response.json()
    assert all(
        attr in json_resp
        for attr in (
            "birthday",
            "disabled",
            "dn",
            "email",
            "firstname",
            "lastname",
            "name",
            "record_uid",
            "roles",
            "schools",
            "school_classes",
            "source_uid",
            "ucsschool_roles",
            "udm_properties",
            "url",
        )
    )
    api_user = UserModel(**json_resp)
    for k, v in udm_properties.items():
        if isinstance(v, (tuple, list)):
            assert set(api_user.udm_properties.get(k, [])) == set(v)
        else:
            assert api_user.udm_properties.get(k) == v
    async with UDM(**udm_kwargs) as udm:
        await compare_lib_api_user(user, api_user, udm, url_fragment)
    json_resp = response.json()
    if type(json_resp) is list:
        json_resp = [resp for resp in json_resp if resp["dn"] == api_user.dn][0]
    compare_ldap_json_obj(api_user.dn, json_resp, url_fragment)


@pytest.mark.asyncio
async def test_get_empty_udm_properties_are_returned(
    auth_header,
    retry_http_502,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    import_config,
    udm_kwargs,
):
    role: Role = random.choice(USER_ROLES)
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, role.name)
    response = retry_http_502(requests.get, f"{url_fragment}/users/{user.name}", headers=auth_header)
    assert response.status_code == 200, response.reason
    api_user = UserModel(**response.json())
    for prop in import_config["mapped_udm_properties"]:
        assert prop in api_user.udm_properties


@pytest.mark.asyncio
async def test_get_returns_exam_user(
    auth_header, create_ou_using_python, retry_http_502, url_fragment, create_exam_user, udm_kwargs
):
    school = await create_ou_using_python()
    dn, exam_user = await create_exam_user(school)
    async with UDM(**udm_kwargs) as udm:
        lib_user: User = (await User.get_all(udm, school, filter_str=f"uid={exam_user['username']}"))[0]
        assert lib_user.name == exam_user["username"]
        assert lib_user.school == school
        assert lib_user.ucsschool_roles == exam_user["ucsschoolRole"]
        assert f"cn=examusers,ou={school}" in lib_user.dn

        response = retry_http_502(
            requests.get,
            f"{url_fragment}/users/{exam_user['username']}",
            headers=auth_header,
            params={"school": school},
        )
        assert response.status_code == 200, response.reason
        json_resp = response.json()
        assert json_resp["name"] == exam_user["username"]
        assert json_resp["ucsschool_roles"] == exam_user["ucsschoolRole"]
        assert f"cn=examusers,ou={school}" in json_resp["dn"]


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_create(
    auth_header,
    check_password,
    retry_http_502,
    url_fragment,
    create_ou_using_python,
    random_user_create_model,
    random_name,
    import_config,
    udm_kwargs,
    schedule_delete_user_name_using_udm,
    role: Role,
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    school = await create_ou_using_python()
    r_user = await random_user_create_model(
        school, roles=[f"{url_fragment}/roles/{role_}" for role_ in roles]
    )
    title = random_name()
    r_user.udm_properties["title"] = title
    phone = [random_name(), random_name()]
    r_user.udm_properties["phone"] = phone
    data = r_user.json()
    print(f"POST data={data!r}")
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={r_user.name}")
    assert len(lib_users) == 0
    schedule_delete_user_name_using_udm(r_user.name)
    response = retry_http_502(
        requests.post,
        f"{url_fragment}/users/",
        headers={"Content-Type": "application/json", **auth_header},
        data=data,
    )
    assert response.status_code == 201, f"{response.__dict__!r}"
    response_json = response.json()
    api_user = UserModel(**response_json)
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={r_user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        udm_props = (await lib_users[0].get_udm_object(udm)).props
    assert api_user.udm_properties["title"] == title
    assert set(api_user.udm_properties["phone"]) == set(phone)
    assert udm_props.title == title
    assert set(udm_props.phone) == set(phone)
    await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
    compare_ldap_json_obj(api_user.dn, response_json, url_fragment)
    if r_user.disabled:
        with pytest.raises(LDAPBindError):
            await check_password(response_json["dn"], r_user.password)
    else:
        await check_password(response_json["dn"], r_user.password)
    # Bug #52668: check sambahome and profilepath
    async with UDM(**udm_kwargs) as udm:
        user_udm = await udm.get("users/user").get(response_json["dn"])
        if role.name == "staff":
            assert user_udm.props.profilepath is None
            assert user_udm.props.sambahome is None
        else:
            assert user_udm.props.profilepath == r"%LOGONSERVER%\%USERNAME%\windows-profiles\default"
            school = await School.from_dn(School.cache(lib_users[0].school).dn, None, udm)
            home_share_file_server = school.home_share_file_server
            assert (
                home_share_file_server
            ), f"No 'home_share_file_server' set for OU {lib_users[0].school!r}."
            samba_home_path = fr"\\{school.get_name_from_dn(home_share_file_server)}\{lib_users[0].name}"
            assert user_udm.props.sambahome == samba_home_path


@pytest.mark.asyncio
async def test_create_unmapped_udm_prop(
    create_ou_using_python,
    random_user_create_model,
    url_fragment,
    udm_kwargs,
    schedule_delete_user_name_using_udm,
    retry_http_502,
    auth_header,
):
    school = await create_ou_using_python()
    r_user = await random_user_create_model(school, roles=[f"{url_fragment}/roles/teacher"])
    r_user.udm_properties["unmapped_prop"] = "some value"
    data = r_user.json()
    print(f"POST data={data!r}")
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={r_user.name}")
    assert len(lib_users) == 0
    schedule_delete_user_name_using_udm(r_user.name)
    response = retry_http_502(
        requests.post,
        f"{url_fragment}/users/",
        headers={"Content-Type": "application/json", **auth_header},
        data=data,
    )
    assert response.status_code == 422, f"{response.__dict__!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_create_without_username(
    auth_header,
    check_password,
    retry_http_502,
    url_fragment,
    create_ou_using_python,
    random_user_create_model,
    import_config,
    reset_import_config,
    udm_kwargs,
    add_to_import_config,
    schedule_delete_user_name_using_udm,
    role: Role,
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    school = await create_ou_using_python()
    r_user = await random_user_create_model(
        school, roles=[f"{url_fragment}/roles/{role_}" for role_ in roles]
    )
    data = r_user.json(exclude={"name"})
    assert "'name'" not in data
    expected_name = f"test.{r_user.firstname[:2]}.{r_user.lastname[:3]}".lower()
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={expected_name}")
    assert len(lib_users) == 0
    schedule_delete_user_name_using_udm(expected_name)
    print(f"POST data={data!r}")
    response = retry_http_502(
        requests.post,
        f"{url_fragment}/users/",
        headers={"Content-Type": "application/json", **auth_header},
        data=data,
    )
    assert response.status_code == 201, f"{response.__dict__!r}"
    response_json = response.json()
    api_user = UserModel(**response_json)
    assert api_user.name == expected_name
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={expected_name}")
    assert len(lib_users) == 1
    assert isinstance(lib_users[0], role.klass)
    if r_user.disabled:
        with pytest.raises(LDAPBindError):
            await check_password(response_json["dn"], r_user.password)
    else:
        await check_password(response_json["dn"], r_user.password)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("no_school_s", ("school", "schools"))
async def test_create_minimal_attrs(
    auth_header,
    check_password,
    retry_http_502,
    url_fragment,
    create_ou_using_python,
    random_user_create_model,
    import_config,
    reset_import_config,
    udm_kwargs,
    add_to_import_config,
    schedule_delete_user_name_using_udm,
    role: Role,
    no_school_s: str,
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    school = await create_ou_using_python()
    r_user = await random_user_create_model(
        school, roles=[f"{url_fragment}/roles/{role_}" for role_ in roles], disabled=False
    )
    data = r_user.dict(
        exclude={
            "birthday",
            "disabled",
            no_school_s,
            "email",
            "name",
            "source_uid",
            "ucsschool_roles",
            "udm_properties",
        }
    )
    expected_name = f"test.{r_user.firstname[:2]}.{r_user.lastname[:3]}".lower()
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={expected_name}")
    assert len(lib_users) == 0
    schedule_delete_user_name_using_udm(expected_name)
    print(f"POST data={data!r}")
    response = retry_http_502(
        requests.post,
        f"{url_fragment}/users/",
        headers={"Content-Type": "application/json", **auth_header},
        json=data,
    )
    assert response.status_code == 201, f"{response.__dict__!r}"
    response_json = response.json()
    api_user = UserModel(**response_json)
    assert api_user.name == expected_name
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={expected_name}")
    assert len(lib_users) == 1
    assert isinstance(lib_users[0], role.klass)
    await check_password(response_json["dn"], r_user.password)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [random.choice(USER_ROLES)], ids=role_id)
@pytest.mark.parametrize("no_school_s", ("school", "schools"))
async def test_create_requires_school_or_schools(
    auth_header,
    url_fragment,
    create_ou_using_python,
    retry_http_502,
    random_user_create_model,
    import_config,
    reset_import_config,
    udm_kwargs,
    add_to_import_config,
    schedule_delete_user_name_using_udm,
    role: Role,
    no_school_s: str,
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    school = await create_ou_using_python()
    r_user = await random_user_create_model(
        school, roles=[f"{url_fragment}/roles/{role_}" for role_ in roles], disabled=False
    )
    data = r_user.dict(exclude={"school", "schools"})
    data["birthday"] = data["birthday"].isoformat()
    expected_name = f"test.{r_user.firstname[:2]}.{r_user.lastname[:3]}".lower()
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={expected_name}")
    assert len(lib_users) == 0
    schedule_delete_user_name_using_udm(expected_name)
    print(f"POST data={data!r}")
    response = retry_http_502(
        requests.post,
        f"{url_fragment}/users/",
        headers={"Content-Type": "application/json", **auth_header},
        json=data,
    )
    assert response.status_code == 422, f"{response.__dict__!r}"
    print(f"response.content={response.content!r}")
    response_json = response.json()
    print(f"response_json={response_json!r}")
    assert "At least one of" in response_json["detail"][0]["msg"]


@pytest.mark.asyncio
async def test_create_with_password_hashes(
    auth_header,
    check_password,
    retry_http_502,
    url_fragment,
    create_ou_using_python,
    random_user_create_model,
    import_config,
    udm_kwargs,
    schedule_delete_user_name_using_udm,
    password_hash,
):
    role = random.choice(USER_ROLES)
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    school = await create_ou_using_python()
    r_user = await random_user_create_model(
        school,
        roles=[f"{url_fragment}/roles/{role_}" for role_ in roles],
        disabled=False,
        school_classes={},
    )
    school = r_user.school.split("/")[-1]
    r_user.password = None
    password_new, password_new_hashes = await password_hash()
    r_user.kelvin_password_hashes = password_new_hashes.dict()
    data = r_user.json()
    print(f"POST data={data!r}")
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={r_user.name}")
    assert len(lib_users) == 0
    schedule_delete_user_name_using_udm(r_user.name)
    response = retry_http_502(
        requests.post,
        f"{url_fragment}/users/",
        headers={"Content-Type": "application/json", **auth_header},
        data=data,
    )
    assert response.status_code == 201, f"{response.__dict__!r}"
    response_json = response.json()
    api_user = UserModel(**response_json)
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={r_user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
    await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
    compare_ldap_json_obj(api_user.dn, response_json, url_fragment)
    await check_password(response_json["dn"], password_new)
    print("OK: can login as user with new password.")


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_put(
    auth_header,
    check_password,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    random_user_create_model,
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
):
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, role.name, disabled=False)
    await check_password(user.dn, user.password)
    print("OK: can login with old password")
    old_user_data = import_user_to_create_model_kwargs(user)
    user_create_model = await random_user_create_model(
        school,
        roles=old_user_data["roles"],
        disabled=False,
        school=old_user_data["school"],
        schools=old_user_data["schools"],
    )
    new_user_data = user_create_model.dict(exclude={"name", "record_uid", "source_uid"})
    title = random_name()
    phone = [random_name(), random_name()]
    new_user_data["udm_properties"] = {"title": title, "phone": phone}
    modified_user = UserCreateModel(**{**old_user_data, **new_user_data})
    modified_user.password = modified_user.password.get_secret_value()
    print(f"PUT modified_user={modified_user.dict()!r}.")
    response = retry_http_502(
        requests.put,
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
        data=modified_user.json(),
    )
    assert response.status_code == 200, response.reason
    api_user = UserModel(**response.json())
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={user.name}")
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
    await check_password(lib_users[0].dn, modified_user.password)


@pytest.mark.asyncio
async def test_put_with_password_hashes(
    auth_header,
    check_password,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    random_user_create_model,
    password_hash,
    import_config,
    udm_kwargs,
):
    role = random.choice(USER_ROLES)
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, role.name, disabled=False, school_classes={})
    await check_password(user.dn, user.password)
    print("OK: can login with old password")
    old_user_data = import_user_to_create_model_kwargs(user)
    new_user_create_model = await random_user_create_model(
        school,
        roles=old_user_data["roles"],
        disabled=False,
        school=old_user_data["school"],
        schools=old_user_data["schools"],
    )
    new_user_data = new_user_create_model.dict(exclude={"name", "password", "record_uid", "source_uid"})
    for key in ("name", "password", "record_uid", "source_uid"):
        assert key not in new_user_data
    modified_user = UserCreateModel(**{**old_user_data, **new_user_data})
    modified_user.password = None
    password_new, password_new_hashes = await password_hash()
    modified_user.kelvin_password_hashes = password_new_hashes.dict()
    print(f"PUT modified_user={modified_user.dict()!r}.")
    response = retry_http_502(
        requests.put,
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
        data=modified_user.json(),
    )
    assert response.status_code == 200, response.reason
    api_user = UserModel(**response.json())
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
    json_resp = response.json()
    compare_ldap_json_obj(api_user.dn, json_resp, url_fragment)
    await check_password(lib_users[0].dn, password_new)
    print("OK: can login as user with new password.")
    with pytest.raises(LDAPBindError):
        await check_password(lib_users[0].dn, user.password)
    print("OK: cannot login as user with old password.")


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("null_value", ("birthday", "email"))
async def test_patch(
    auth_header,
    check_password,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    random_user_create_model,
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
    null_value: str,
):
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, role.name, disabled=False)
    await check_password(user.dn, user.password)
    print("OK: can login with old password")
    old_user_data = import_user_to_create_model_kwargs(user)
    user_create_model = await random_user_create_model(
        school,
        roles=old_user_data["roles"],
        disabled=False,
        school=old_user_data["school"],
        schools=old_user_data["schools"],
    )
    new_user_data = user_create_model.dict(exclude={"name", "record_uid", "source_uid"})
    new_user_data["birthday"] = str(new_user_data["birthday"])
    for key in random.sample(new_user_data.keys(), random.randint(1, len(new_user_data.keys()))):
        del new_user_data[key]
    title = random_name()
    phone = [random_name(), random_name()]
    new_user_data["udm_properties"] = {"title": title, "phone": phone}
    new_user_data[null_value] = None
    new_user_data["password"] = fake.password(length=20)
    print(f"PATCH new_user_data={new_user_data!r}.")
    response = retry_http_502(
        requests.patch,
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
        json=new_user_data,
    )
    assert response.status_code == 200, response.reason
    api_user = UserModel(**response.json())
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={user.name}")
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
    await check_password(lib_users[0].dn, new_user_data["password"])


@pytest.mark.asyncio
async def test_patch_with_password_hashes(
    auth_header,
    check_password,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    random_user_create_model,
    import_config,
    password_hash,
    udm_kwargs,
):
    role = random.choice(USER_ROLES)
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, role.name, disabled=False, school_classes={})
    await check_password(user.dn, user.password)
    print("OK: can login with old password")
    old_user_data = import_user_to_create_model_kwargs(user)
    user_create_model = await random_user_create_model(
        school,
        roles=old_user_data["roles"],
        disabled=False,
        school=old_user_data["school"],
        schools=old_user_data["schools"],
    )
    new_user_data = user_create_model.dict(
        exclude={"birthday", "name", "password", "record_uid", "source_uid"}
    )
    password_new, password_new_hashes = await password_hash()
    new_user_data["kelvin_password_hashes"] = password_new_hashes.dict()
    print(f"PATCH new_user_data={new_user_data!r}.")
    response = retry_http_502(
        requests.patch,
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
        json=new_user_data,
    )
    assert response.status_code == 200, response.reason
    json_resp = response.json()
    api_user = UserModel(**json_resp)
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)
        await compare_lib_api_user(lib_users[0], api_user, udm, url_fragment)
    compare_ldap_json_obj(api_user.dn, json_resp, url_fragment)
    await check_password(user.dn, password_new)
    print("OK: can login as user with new password.")
    with pytest.raises(LDAPBindError):
        await check_password(user.dn, user.password)
    print("OK: cannot login as user with old password.")


@pytest.mark.asyncio
@pytest.mark.parametrize("roles", itertools.product(USER_ROLES, USER_ROLES), ids=two_roles_id)
@pytest.mark.parametrize("method", ("patch", "put"))
async def test_role_change(
    auth_header,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    new_import_user,
    import_config,
    udm_kwargs,
    schedule_delete_user_name_using_udm,
    new_school_class_using_lib,
    random_name,
    roles: Tuple[Role, Role],
    method: str,
    create_multiple_ous,
):
    role_from, role_to = roles
    ou1, ou2 = await create_multiple_ous(2)
    user: ImportUser = await new_import_user(ou1, role_from.name, schools=[ou1, ou2])
    if role_to.name == "teacher_and_staff":
        roles_ulrs = [
            f"{url_fragment}/roles/staff",
            f"{url_fragment}/roles/teacher",
        ]
    else:
        roles_ulrs = [f"{url_fragment}/roles/{role_to.name}"]
    user_url = f"{url_fragment}/users/{user.name}"
    schedule_delete_user_name_using_udm(user.name)
    if role_to.name == "student":
        # For conversion to Student one class per school is required, but user has only the one for ou1.
        sc_dn2, sc_attr2 = await new_school_class_using_lib(ou2)
        school_classes = {ou2: [sc_attr2["name"]]}
        if role_from.name == "staff":
            # Staff user will have no school_class, so it is missing even the one for ou1.
            sc_dn, sc_attr = await new_school_class_using_lib(ou1)
            school_classes[ou1] = [sc_attr["name"]]
    else:
        school_classes = {}
    if method == "patch":
        patch_data = {"roles": roles_ulrs}
        if school_classes:
            patch_data["school_classes"] = school_classes
        response = retry_http_502(
            requests.patch,
            user_url,
            headers=auth_header,
            json=patch_data,
        )
    elif method == "put":
        old_data = import_user_to_create_model_kwargs(user, ["roles"])
        if school_classes:
            old_data["school_classes"] = school_classes
        modified_user = UserCreateModel(roles=roles_ulrs, **old_data)
        response = retry_http_502(
            requests.put,
            user_url,
            headers=auth_header,
            data=modified_user.json(),
        )
    assert response.status_code == 200, response.reason
    json_resp = response.json()
    assert set(UserCreateModel.unscheme_and_unquote(role_url) for role_url in json_resp["roles"]) == set(
        roles_ulrs
    )
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, ou1, f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role_to.klass)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ("patch", "put"))
async def test_role_change_fails_for_student_without_school_class(
    auth_header,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    import_config,
    udm_kwargs,
    schedule_delete_user_name_using_udm,
    method: str,
):
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, "staff")  # staff has no school classes
    roles_ulrs = [f"{url_fragment}/roles/student"]
    user_url = f"{url_fragment}/users/{user.name}"
    schedule_delete_user_name_using_udm(user.name)
    if method == "patch":
        patch_data = {"roles": roles_ulrs}
        response = retry_http_502(
            requests.patch,
            user_url,
            headers=auth_header,
            json=patch_data,
        )
    elif method == "put":
        old_data = import_user_to_create_model_kwargs(user, ["roles"])
        modified_user = UserCreateModel(roles=roles_ulrs, **old_data)
        response = retry_http_502(
            requests.put,
            user_url,
            headers=auth_header,
            data=modified_user.json(),
        )
    assert response.status_code == 400, response.reason
    json_resp = response.json()
    assert "requires at least one school class per school" in json_resp["detail"]
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], Staff)  # unchanged


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ("patch", "put"))
async def test_role_change_fails_for_student_missing_school_class_for_second_school(
    auth_header,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    new_import_user,
    import_config,
    udm_kwargs,
    schedule_delete_user_name_using_udm,
    method: str,
    create_multiple_ous,
):
    ou1, ou2 = await create_multiple_ous(2)
    user: ImportUser = await new_import_user(ou1, "teacher", schools=[ou1, ou2])
    # staff has no school classes
    async with UDM(**udm_kwargs) as udm:
        lib_users = await Teacher.get_all(udm, ou1, f"username={user.name}")
        assert len(lib_users) == 1
        assert lib_users[0].school_classes[ou1]
        assert not lib_users[0].school_classes.get(ou2)
    roles_ulrs = [f"{url_fragment}/roles/student"]
    user_url = f"{url_fragment}/users/{user.name}"
    schedule_delete_user_name_using_udm(user.name)
    if method == "patch":
        patch_data = {"roles": roles_ulrs}
        response = retry_http_502(
            requests.patch,
            user_url,
            headers=auth_header,
            json=patch_data,
        )
    elif method == "put":
        old_data = import_user_to_create_model_kwargs(user, ["roles"])
        modified_user = UserCreateModel(roles=roles_ulrs, **old_data)
        response = retry_http_502(
            requests.put,
            user_url,
            headers=auth_header,
            data=modified_user.json(),
        )
    assert response.status_code == 400, response.reason
    json_resp = response.json()
    assert "requires at least one school class per school" in json_resp["detail"]
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, ou1, f"username={user.name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], Teacher)  # unchanged


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_delete(
    auth_header,
    retry_http_502,
    url_fragment,
    create_ou_using_python,
    new_school_user,
    udm_kwargs,
    role: Role,
):
    school = await create_ou_using_python()
    user: User = await new_school_user(school, role.name)
    assert isinstance(user, role.klass)
    response = retry_http_502(
        requests.delete,
        f"{url_fragment}/users/{user.name}",
        headers=auth_header,
    )
    assert response.status_code == 204, response.reason
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={user.name}")
    assert len(lib_users) == 0


def test_delete_non_existent(auth_header, retry_http_502, url_fragment, random_name):
    response = retry_http_502(
        requests.delete,
        f"{url_fragment}/users/{random_name()}",
        headers=auth_header,
    )
    assert response.status_code == 404, response.reason


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("method", ("patch", "put"))
async def test_rename(
    auth_header,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    create_random_users,
    random_user_create_model,
    random_name,
    import_config,
    udm_kwargs,
    role: Role,
    method: str,
    schedule_delete_user_name_using_udm,
):
    school = await create_ou_using_python()
    if method == "patch":
        user: ImportUser = await new_import_user(school, role.name)
        new_name = f"t.new.{random_name()}.{random_name()}"
        schedule_delete_user_name_using_udm(new_name)
        response = retry_http_502(
            requests.patch,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            json={"name": new_name},
        )
    elif method == "put":
        user_data = (await random_user_create_model(school, roles=[url_fragment, url_fragment])).dict(
            exclude={"roles"}
        )
        user = (await create_random_users(school, {role.name: 1}, **user_data))[0]
        new_name = f"t.new.{random_name()}.{random_name()}"
        old_data = user.dict(exclude={"name"})
        modified_user = UserCreateModel(name=new_name, **old_data)
        response = retry_http_502(
            requests.put,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            data=modified_user.json(),
        )
    assert response.status_code == 200, f"{response.reason} -- {response.content[:4096]}"
    api_user = UserModel(**response.json())
    assert api_user.name == new_name
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={user.name}")
        assert len(lib_users) == 0
        lib_users = await User.get_all(udm, school, f"username={new_name}")
        assert len(lib_users) == 1
        assert isinstance(lib_users[0], role.klass)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("method", ("patch", "put"))
async def test_school_change(
    auth_header,
    retry_http_502,
    url_fragment,
    create_random_users,
    create_multiple_ous,
    udm_kwargs,
    role: Role,
    method: str,
):
    ou1_name, ou2_name = await create_multiple_ous(2)
    user = (
        await create_random_users(ou1_name, {role.name: 1}, school=f"{url_fragment}/schools/{ou1_name}")
    )[0]
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, ou1_name, f"username={user.name}")
    assert len(lib_users) == 1
    assert isinstance(lib_users[0], role.klass)
    assert lib_users[0].school == ou1_name
    assert lib_users[0].schools == [ou1_name]
    if role.name == "teacher_and_staff":
        roles = {
            f"staff:school:{ou1_name}",
            f"teacher:school:{ou1_name}",
        }
    else:
        roles = {f"{role.name}:school:{ou1_name}"}
    assert set(lib_users[0].ucsschool_roles) == roles
    url = f"{url_fragment}/schools/{ou2_name}"
    _url: SplitResult = urlsplit(url)
    new_school_url = HttpUrl(url, path=_url.path, scheme=_url.scheme, host=_url.netloc)
    if method == "patch":
        patch_data = dict(school=new_school_url, schools=[new_school_url])
        response = retry_http_502(
            requests.patch,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            json=patch_data,
        )
    elif method == "put":
        old_data = user.dict(exclude={"school", "schools", "school_classes"})
        modified_user = UserCreateModel(school=new_school_url, schools=[new_school_url], **old_data)
        response = retry_http_502(
            requests.put,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            data=modified_user.json(),
        )
    json_response = response.json()
    assert response.status_code == 200, response.reason
    async with UDM(**udm_kwargs) as udm:
        async for udm_user in udm.get("users/user").search(filter_format("uid=%s", (user.name,))):
            udm_user_schools = udm_user.props.school
            assert udm_user_schools == [ou2_name]
        api_user = UserModel(**json_response)
        assert (
            api_user.unscheme_and_unquote(str(api_user.school)) == f"{url_fragment}/schools/{ou2_name}"
        )
        lib_users = await User.get_all(udm, ou2_name, f"username={user.name}")
    assert len(lib_users) == 1
    assert isinstance(lib_users[0], role.klass)
    assert lib_users[0].school == ou2_name
    assert lib_users[0].schools == [ou2_name]
    if role.name == "teacher_and_staff":
        roles = {
            f"staff:school:{ou2_name}",
            f"teacher:school:{ou2_name}",
        }
    else:
        roles = {f"{role.name}:school:{ou2_name}"}
    assert set(lib_users[0].ucsschool_roles) == roles


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("http_method", ("patch", "put"))
async def test_change_disable(
    auth_header,
    check_password,
    retry_http_502,
    url_fragment,
    create_ou_using_python,
    create_random_users,
    import_config,
    udm_kwargs,
    role: Role,
    http_method: str,
):
    school = await create_ou_using_python()
    user = (await create_random_users(school, {role.name: 1}, disabled=False))[0]
    assert user.disabled is False
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, school, f"username={user.name}")
        assert len(lib_users) == 1
    # delete password, so PUT with complete user data will not produce
    # 'Password has been used before. Please choose a different one.'
    password = user.password
    user.password = None
    await check_password(lib_users[0].dn, password)

    user.disabled = True
    if http_method == "patch":
        response = retry_http_502(
            requests.patch,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            json={"disabled": user.disabled},
        )
    else:
        response = retry_http_502(
            requests.put,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            data=user.json(),
        )
    assert response.status_code == 200, response.reason
    response = retry_http_502(requests.get, f"{url_fragment}/users/{user.name}", headers=auth_header)
    assert response.status_code == 200, response.reason
    time.sleep(5)
    api_user = UserModel(**response.json())
    assert api_user.disabled == user.disabled
    with pytest.raises(LDAPBindError):
        await check_password(lib_users[0].dn, password)

    user.disabled = False
    if http_method == "patch":
        response = retry_http_502(
            requests.patch,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            json={"disabled": user.disabled},
        )
    else:
        response = retry_http_502(
            requests.put,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            data=user.json(),
        )
    assert response.status_code == 200, response.reason
    time.sleep(5)
    response = retry_http_502(requests.get, f"{url_fragment}/users/{user.name}", headers=auth_header)
    api_user = UserModel(**response.json())
    assert api_user.disabled == user.disabled
    await check_password(lib_users[0].dn, password)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("http_method", ("patch", "put"))
async def test_change_password(
    auth_header,
    check_password,
    retry_http_502,
    import_user_to_create_model_kwargs,
    url_fragment,
    create_ou_using_python,
    new_import_user,
    import_config,
    role: Role,
    http_method: str,
):
    school = await create_ou_using_python()
    user: ImportUser = await new_import_user(school, role.name, disabled=False)
    assert user.disabled is False
    old_password = user.password
    await check_password(user.dn, old_password)
    print("OK: can login with old password")
    new_password = fake.password(length=20)
    user.password = new_password
    assert user.password != old_password
    if http_method == "patch":
        response = retry_http_502(
            requests.patch,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            json={"password": new_password},
        )
    else:
        create_model_kwargs = import_user_to_create_model_kwargs(user)
        create_model = UserCreateModel(**create_model_kwargs)
        create_model.password = create_model.password.get_secret_value()
        response = retry_http_502(
            requests.put,
            f"{url_fragment}/users/{user.name}",
            headers=auth_header,
            data=create_model.json(),
        )
    assert response.status_code == 200, response.reason
    await check_password(user.dn, new_password)


@pytest.mark.asyncio
async def test_set_password_hashes(
    check_password, create_ou_using_python, new_school_user, password_hash
):
    role = random.choice(USER_ROLES)
    school = await create_ou_using_python()
    user: User = await new_school_user(school, role.name, disabled=False, school_classes={})
    assert user.disabled is False
    password_old = user.password
    ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
    user_dn = await ldap_access.get_dn_of_user(user.name)
    await check_password(user_dn, password_old)
    print("OK: can login as user with its old password.")
    password_new, password_new_hashes = await password_hash()
    assert password_old != password_new
    await set_password_hashes(user_dn, password_new_hashes)
    await check_password(user_dn, password_new)
    print("OK: can login as user with new password.")
    with pytest.raises(LDAPBindError):
        await check_password(user_dn, password_old)
    print("OK: cannot login as user with old password.")


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.parametrize("model", (UserCreateModel, UserPatchModel))
async def test_not_password_and_password_hashes(
    role: Role,
    model: Union[Type[UserCreateModel], Type[UserPatchModel]],
    create_ou_using_python,
    random_user_create_model,
    password_hash,
    url_fragment,
):
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    school = await create_ou_using_python()
    user_data = await random_user_create_model(
        school,
        roles=[f"{url_fragment}/roles/{role_}" for role_ in roles],
        disabled=False,
        school_classes={},
    )
    password_new, password_new_hashes = await password_hash()

    user_data.password = fake.password()
    user_data.kelvin_password_hashes = None
    model(**user_data.dict())
    model(**user_data.dict())

    user_data.password = None
    user_data.kelvin_password_hashes = password_new_hashes
    model(**user_data.dict())
    model(**user_data.dict())

    user_data.password = fake.password()
    user_data.kelvin_password_hashes = password_new_hashes
    with pytest.raises(ValueError):
        model(**user_data.dict())
    with pytest.raises(ValueError):
        model(**user_data.dict())


@pytest.mark.asyncio
async def test_krb_5_keys_are_base64_binaries(password_hash):
    password_new, password_new_hashes = await password_hash()
    assert PasswordsHashes(**password_new_hashes.dict())

    password_new_hashes.krb_5_key.append("bar")
    with pytest.raises(ValueError) as exc_info:
        _ = PasswordsHashes(**password_new_hashes.dict())
    assert "krb_5_key" in str(exc_info.value)
    assert "must be base64 encoded" in str(exc_info.value)
