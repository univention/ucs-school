import random
from typing import List, NamedTuple, Type, Union

import pytest
from faker import Faker

from ucsschool.lib.models.user import Staff, Student, Teacher, TeachersAndStaff, User
from udm_rest_client import UDM

UserType = Type[Union[Staff, Student, Teacher, TeachersAndStaff, User]]
Role = NamedTuple("Role", [("name", str), ("klass", UserType)])


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
fake = Faker()
USER_ROLES: List[Role] = [
    Role("staff", Staff),
    Role("student", Student),
    Role("teacher", Teacher),
    Role("teacher_and_staff", TeachersAndStaff),
]
random.shuffle(USER_ROLES)


def role_id(value: Role) -> str:
    return value.name


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_user_exists(new_user, udm_kwargs, role: Role):
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as udm:
        user0 = await User.from_dn(dn, attr["school"][0], udm)
        assert await user0.exists(udm) is True
        user1 = User(name=attr["username"], school=attr["school"][0])
        assert await user1.exists(udm) is True
        user2 = User(name=fake.pystr(), school=attr["school"][0])
        assert await user2.exists(udm) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_user_type_is_converted(new_user, role2class, udm_kwargs, role: Role):
    """aka test_*_get_class_for_udm_obj()"""
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as udm:
        user0 = await User.from_dn(dn, attr["school"][0], udm)
        assert await user0.exists(udm) is True
        exp_cls = role2class[role.name]
        assert isinstance(user0, exp_cls)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_read_user(new_user, udm_kwargs, role: Role):
    async with UDM(**udm_kwargs) as lo_udm:
        dn, attr = await new_user(role.name)
        user = await role.klass.from_dn(dn, attr["school"][0], lo_udm)
        assert await user.exists(lo_udm)
        del attr["description"]
        del attr["password"]
        del attr["ucsschoolRole"]
        for k, v in attr.items():
            if k == "username":
                val1 = v
                val2 = getattr(user, "name")
            elif k == "school":
                val1 = v
                val2 = [getattr(user, k)]
            elif k == "birthday":
                val1 = str(v)
                val2 = getattr(user, k)
            elif k == "mailPrimaryAddress":
                val1 = v
                val2 = getattr(user, "email")
            else:
                val1 = v
                val2 = getattr(user, k)
            if isinstance(v, list):
                val1 = set(val1)
                val2 = set(val2)
            assert val1 == val2, "k={!r} v={!r} getattr(user, k)={!r}".format(
                k, v, getattr(user, k)
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_create_user(new_school_class, users_user_props, udm_kwargs, role: Role):
    async with UDM(**udm_kwargs) as lo_udm:
        user_props = users_user_props()
        user_props["name"] = user_props["username"]
        user_props["email"] = user_props["mailPrimaryAddress"]
        user_props["school"] = user_props["school"][0]
        user_props["birthday"] = str(user_props["birthday"])
        if role.klass != Staff:
            cls_dn1, cls_attr1 = await new_school_class()
            cls_dn2, cls_attr2 = await new_school_class()
            user_props["school_classes"] = {
                "DEMOSCHOOL": [
                    f"DEMOSCHOOL-{cls_attr1['name']}",
                    f"DEMOSCHOOL-{cls_attr2['name']}",
                ]
            }
        user = role.klass(**user_props)
        await user.create(lo_udm)
        assert await user.exists(lo_udm)
        udm_user = await lo_udm.get("users/user").get(user.dn)
        print(udm_user.__dict__)
        del user_props["description"]
        del user_props["password"]
        del user_props["name"]  # tested by username
        del user_props["email"]  # tested by mailPrimaryAddress
        if role.klass != Staff:
            del user_props["school_classes"]
        for k, v in user_props.items():
            if k == "school":
                val1 = [v]
                val2 = getattr(udm_user.props, k)
            else:
                val1 = v
                val2 = getattr(udm_user.props, k)
            if isinstance(v, list):
                val1 = set(val1)
                val2 = set(val2)
            assert val1 == val2, "k={!r} v={!r} getattr(user, k)={!r}".format(
                k, v, getattr(udm_user.props, k)
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_remove_user(udm_kwargs, new_user, role: Role):
    async with UDM(**udm_kwargs) as lo_udm:
        dn, attr = await new_user(role.name)
        user = await role.klass.from_dn(dn, attr["school"][0], lo_udm)
        assert await user.exists(lo_udm)
        await user.remove(lo_udm)
        assert not await user.exists(lo_udm)
