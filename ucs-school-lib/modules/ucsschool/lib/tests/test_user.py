import random
from typing import List, NamedTuple, Type, Union

import pytest
from faker import Faker
from ldap.filter import filter_format

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


def compare_attr_and_lib_user(attr, user):
    for k, v in attr.items():
        if k in ("description", "password", "ucsschoolRole"):
            continue
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


def role_id(value: Role) -> str:
    return value.name


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_exists(new_user, udm_kwargs, role: Role):
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as udm:
        for kls in (role.klass, User):
            user0 = await kls.from_dn(dn, attr["school"][0], udm)
            assert await user0.exists(udm) is True
            user1 = kls(name=attr["username"], school=attr["school"][0])
            assert await user1.exists(udm) is True
            user2 = kls(name=fake.pystr(), school=attr["school"][0])
            assert await user2.exists(udm) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_from_dn(new_user, udm_kwargs, role: Role):
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as lo_udm:
        for kls in (role.klass, User):
            user = await kls.from_dn(dn, attr["school"][0], lo_udm)
            assert isinstance(user, role.klass)
            compare_attr_and_lib_user(attr, user)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_from_udm_obj(new_user, udm_kwargs, role: Role):
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as udm:
        for kls in (role.klass, User):
            udm_mod = udm.get(kls._meta.udm_module)
            udm_obj = await udm_mod.get(dn)
            user = await kls.from_udm_obj(udm_obj, attr["school"], udm)
            assert isinstance(user, role.klass)
            compare_attr_and_lib_user(attr, user)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_get_all(new_user, udm_kwargs, role: Role):
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as udm:
        for kls in (role.klass, User):
            for obj in await kls.get_all(udm, attr["school"][0]):
                if obj.dn == dn:
                    break
            else:
                raise AssertionError(
                    f"DN {dn!r} not found in {kls.__name__}.get_all(udm, {attr['school'][0]})."
                )
            filter_str = filter_format("(uid=%s)", (attr["username"],))
            objs = await kls.get_all(udm, attr["school"][0], filter_str=filter_str)
            assert len(objs) == 1
            assert isinstance(objs[0], role.klass)
            compare_attr_and_lib_user(attr, objs[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_get_class_for_udm_obj(new_user, role2class, udm_kwargs, role: Role):
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as udm:
        udm_obj = await udm.get(User._meta.udm_module).get(dn)
        klass = await User.get_class_for_udm_obj(udm_obj, attr["school"])
        assert klass is role.klass


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_create(new_school_class, users_user_props, udm_kwargs, role: Role):
    async with UDM(**udm_kwargs) as udm:
        user_props = users_user_props()
        user_props["name"] = user_props["username"]
        user_props["email"] = user_props["mailPrimaryAddress"]
        school = user_props["school"][0]
        user_props["school"] = school
        user_props["birthday"] = str(user_props["birthday"])
        if role.klass != Staff:
            cls_dn1, cls_attr1 = await new_school_class()
            cls_dn2, cls_attr2 = await new_school_class()
            user_props["school_classes"] = {
                school: [
                    f"{school}-{cls_attr1['name']}",
                    f"{school}-{cls_attr2['name']}",
                ]
            }
        user = role.klass(**user_props)
        success = await user.create(udm)
        assert success is True
        user = await role.klass.from_dn(user.dn, school, udm)
        user_props["school"] = [school]
        compare_attr_and_lib_user(user_props, user)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
@pytest.mark.xfail(reason="NotImplementedYet")
async def test_modify(
    new_school_class, users_user_props, new_user, udm_kwargs, role: Role
):
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as udm:
        user = await role.klass.from_dn(dn, attr["school"], udm)
        description = fake.text(max_nb_chars=50)
        user.description = description
        firstname = fake.first_name()
        user.firstname = firstname
        lastname = fake.last_name()
        user.lastname = lastname
        birthday = fake.date_of_birth(minimum_age=6, maximum_age=65).strftime(
            "%Y-%m-%d"
        )
        user.birthday = birthday
        success = await user.modify(udm)
        assert success is True
        user = await role.klass.from_dn(dn, attr["school"], udm)
    compare_attr_and_lib_user(attr, user)


@pytest.mark.xfail(reason="new_ou() NotImplementedYet")
@pytest.mark.asyncio
async def test_move(new_school_class, new_ou, ldap_base, udm_kwargs):
    raise NotImplementedError


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_remove(udm_kwargs, new_user, role: Role):
    dn, attr = await new_user(role.name)
    async with UDM(**udm_kwargs) as udm:
        user = await role.klass.from_dn(dn, attr["school"][0], udm)
        assert await user.exists(udm)
        success = await user.remove(udm)
        assert success is True
        assert not await user.exists(udm)
