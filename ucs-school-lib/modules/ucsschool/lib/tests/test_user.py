import itertools
import random
from typing import Any, Dict, List, NamedTuple, Tuple, Type, Union

import pytest
from faker import Faker
from ldap.filter import filter_format

from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.user import (
    ExamStudent,
    Staff,
    Student,
    Teacher,
    TeachersAndStaff,
    User,
    UserTypeConverter,
    convert_to_staff,
    convert_to_student,
    convert_to_teacher,
    convert_to_teacher_and_staff,
)
from udm_rest_client import UDM

UserType = Union[Type[Staff], Type[Student], Type[Teacher], Type[TeachersAndStaff], Type[User]]
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


def compare_attr_and_lib_user(attr: Dict[str, Any], user: User):
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
        elif k == "e-mail":
            val1 = set(v)
            val2 = {getattr(user, "email")}
        else:
            val1 = v
            val2 = getattr(user, k)
        if isinstance(v, list):
            val1 = set(val1)
            val2 = set(val2)
        assert val1 == val2, "k={!r} v={!r} getattr(user, k)={!r}".format(k, v, getattr(user, k))


def role_id(value: Role) -> str:
    return value.name


def two_roles_id(value: List[Role]) -> str:
    return f"{value[0].name} -> {value[1].name}"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_exists(create_ou_using_python, new_udm_user, udm_kwargs, role: Role):
    ou = await create_ou_using_python()
    dn, attr = await new_udm_user(ou, role.name)
    async with UDM(**udm_kwargs) as udm:
        for kls in (role.klass, User):
            user0 = await kls.from_dn(dn, ou, udm)
            assert await user0.exists(udm) is True
            user1 = kls(name=attr["username"], school=ou)
            assert await user1.exists(udm) is True
            user2 = kls(name=fake.pystr(), school=ou)
            assert await user2.exists(udm) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_from_dn(create_ou_using_python, new_udm_user, udm_kwargs, role: Role):
    ou = await create_ou_using_python()
    dn, attr = await new_udm_user(ou, role.name)
    async with UDM(**udm_kwargs) as lo_udm:
        for kls in (role.klass, User):
            user = await kls.from_dn(dn, ou, lo_udm)
            assert isinstance(user, role.klass)
            compare_attr_and_lib_user(attr, user)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_from_udm_obj(create_ou_using_python, new_udm_user, udm_kwargs, role: Role):
    ou = await create_ou_using_python()
    dn, attr = await new_udm_user(ou, role.name)
    async with UDM(**udm_kwargs) as udm:
        for kls in (role.klass, User):
            udm_mod = udm.get(kls._meta.udm_module)
            udm_obj = await udm_mod.get(dn)
            user = await kls.from_udm_obj(udm_obj, ou, udm)
            assert isinstance(user, role.klass)
            compare_attr_and_lib_user(attr, user)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_get_all(create_ou_using_python, new_udm_user, udm_kwargs, role: Role):
    ou = await create_ou_using_python()
    dn, attr = await new_udm_user(ou, role.name)
    async with UDM(**udm_kwargs) as udm:
        for kls in (role.klass, User):
            for obj in await kls.get_all(udm, ou):
                if obj.dn == dn:
                    break
            else:
                raise AssertionError(f"DN {dn!r} not found in {kls.__name__}.get_all(udm, {ou}).")
            filter_str = filter_format("(uid=%s)", (attr["username"],))
            objs = await kls.get_all(udm, ou, filter_str=filter_str)
            assert len(objs) == 1
            assert isinstance(objs[0], role.klass)
            compare_attr_and_lib_user(attr, objs[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_get_class_for_udm_obj(
    create_ou_using_python, new_udm_user, role2class, udm_kwargs, role: Role
):
    ou = await create_ou_using_python()
    dn, attr = await new_udm_user(ou, role.name)
    async with UDM(**udm_kwargs) as udm:
        udm_obj = await udm.get(User._meta.udm_module).get(dn)
        klass = await User.get_class_for_udm_obj(udm_obj, ou)
        assert klass is role.klass


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_create(
    create_ou_using_python, new_school_class_using_udm, udm_users_user_props, udm_kwargs, role: Role
):
    school = await create_ou_using_python()
    async with UDM(**udm_kwargs) as udm:
        user_props = await udm_users_user_props(school)
        user_props["name"] = user_props["username"]
        user_props["email"] = user_props["mailPrimaryAddress"]
        user_props["school"] = school
        user_props["birthday"] = str(user_props["birthday"])
        del user_props["e-mail"]
        if role.klass != Staff:
            cls_dn1, cls_attr1 = await new_school_class_using_udm(school=school)
            cls_dn2, cls_attr2 = await new_school_class_using_udm(school=school)
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
async def test_modify(create_ou_using_python, new_udm_user, udm_kwargs, role: Role):
    ou = await create_ou_using_python()
    dn, attr = await new_udm_user(ou, role.name)
    async with UDM(**udm_kwargs) as udm:
        user = await role.klass.from_dn(dn, ou, udm)
        description = fake.text(max_nb_chars=50)
        user.description = description
        firstname = fake.first_name()
        user.firstname = firstname
        lastname = fake.last_name()
        user.lastname = lastname
        birthday = fake.date_of_birth(minimum_age=6, maximum_age=65).strftime("%Y-%m-%d")
        user.birthday = birthday
        success = await user.modify(udm)
        assert success is True
        user = await role.klass.from_dn(dn, ou, udm)
    attr["firstname"] = firstname
    attr["lastname"] = lastname
    attr["birthday"] = birthday
    compare_attr_and_lib_user(attr, user)


@pytest.mark.asyncio
@pytest.mark.parametrize("roles", itertools.product(USER_ROLES, USER_ROLES), ids=two_roles_id)
async def test_modify_role(
    ldap_base,
    new_school_class_using_udm,
    new_udm_user,
    udm_kwargs,
    roles: Tuple[Role, Role],
    schedule_delete_user_dn,
    create_multiple_ous,
):
    role_from, role_to = roles
    ou1, ou2 = await create_multiple_ous(2)
    dn, attr = await new_udm_user(ou1, role_from.name)
    async with UDM(**udm_kwargs) as udm:
        use_old_udm = await udm.get("users/user").get(dn)
        # add a school class also to staff users, so we can check if it is kept upon conversion to other
        # role
        cls_dn1, cls_attr1 = await new_school_class_using_udm(school=ou1)
        cls_dn2, cls_attr2 = await new_school_class_using_udm(school=ou1)
        role_ou2 = f"teacher:school:{ou2}"
        cls_dn3, cls_attr3 = await new_school_class_using_udm(school=ou2)
        use_old_udm.props.school.append(ou2)
        role_group_prefix = {
            "staff": "mitarbeiter",
            "student": "schueler",
            "teacher": "lehrer",
            "teacher_and_staff": "mitarbeiter",
        }[role_from.name]
        ou2_group_cn = f"cn=groups,ou={ou2},{ldap_base}"
        use_old_udm.props.groups.extend(
            [
                cls_dn1,
                cls_dn3,
                f"cn=Domain Users {ou2},{ou2_group_cn}",
                f"cn={role_group_prefix}-{ou2.lower()},{ou2_group_cn}",
            ]
        )
        non_school_role = f"{fake.first_name()}:{fake.last_name()}:{fake.user_name()}"
        use_old_udm.props.ucsschoolRole.extend([role_ou2, non_school_role])
        await use_old_udm.save()
        user_old = await role_from.klass.from_dn(dn, attr["school"][0], udm)
        assert isinstance(user_old, role_from.klass)
        # check 'addition_class' functionality
        addition_class = {cls_attr2["school"]: [cls_attr2["name"]]}
        if issubclass(role_from.klass, Staff) and issubclass(role_to.klass, Student):
            # Staff user will have no school_class, but for conversion to Student it needs one class per
            # school:
            addition_class[ou2] = [cls_attr3["name"]]

        if issubclass(role_to.klass, Staff):
            user_new = await convert_to_staff(user_old, udm, addition_class)
        elif issubclass(role_to.klass, Student):
            user_new = await convert_to_student(user_old, udm, addition_class)
        elif issubclass(role_to.klass, TeachersAndStaff):
            user_new = await convert_to_teacher_and_staff(user_old, udm, addition_class)
        else:
            assert issubclass(role_to.klass, Teacher)
            user_new = await convert_to_teacher(user_old, udm, addition_class)
        schedule_delete_user_dn(user_new.dn)

        if role_from.klass == role_to.klass:
            assert user_old is user_new
            return

        user_new_udm = await udm.get("users/user").get(user_new.dn)
        user_new_ucsschool_roles = set(user_new.ucsschool_roles)
        new_groups = {grp.lower() for grp in user_new_udm.props.groups}

        # check class
        assert isinstance(user_new, role_to.klass)
        assert user_new.__class__ is role_to.klass
        # check domain users OU
        for ou in user_new.schools:
            assert f"cn=Domain Users {ou},cn=groups,ou={ou},{ldap_base}".lower() in new_groups
        # check non-school role is ignored
        assert non_school_role in user_new_ucsschool_roles
        if isinstance(user_new, Staff):
            # check school class
            assert cls_dn1.lower() not in new_groups
            assert cls_dn2.lower() not in new_groups
            assert cls_dn3.lower() not in new_groups
            # check options
            assert user_new_udm.options.get("ucsschoolStaff") is True
            assert user_new_udm.options.get("ucsschoolStudent", False) is False
            assert user_new_udm.options.get("ucsschoolTeacher", False) is False
            # check position
            assert user_new_udm.position == f"cn=mitarbeiter,cn=users,ou={user_new.school},{ldap_base}"
            # check roles
            assert {f"staff:school:{ou}" for ou in user_new.schools}.issubset(user_new_ucsschool_roles)
            assert {
                f"{role}:school:{ou}" for ou in user_new.schools for role in ("student", "teacher")
            }.isdisjoint(user_new_ucsschool_roles)
        elif isinstance(user_new, Student):
            assert cls_dn1.lower() in new_groups
            assert cls_dn2.lower() in new_groups
            assert cls_dn3.lower() in new_groups
            assert user_new_udm.options.get("ucsschoolStudent") is True
            assert user_new_udm.options.get("ucsschoolAdministrator", False) is False
            assert user_new_udm.options.get("ucsschoolStaff", False) is False
            assert user_new_udm.options.get("ucsschoolTeacher", False) is False
            assert user_new_udm.position == f"cn=schueler,cn=users,ou={user_new.school},{ldap_base}"
            assert {f"student:school:{ou}" for ou in user_new.schools}.issubset(user_new_ucsschool_roles)
            assert {
                f"{role}:school:{ou}"
                for ou in user_new.schools
                for role in ("school_admin", "staff", "teacher")
            }.isdisjoint(user_new_ucsschool_roles)
        elif isinstance(user_new, TeachersAndStaff):
            assert cls_dn1.lower() in new_groups
            assert cls_dn2.lower() in new_groups
            assert cls_dn3.lower() in new_groups
            assert user_new_udm.options.get("ucsschoolStaff") is True
            assert user_new_udm.options.get("ucsschoolTeacher") is True
            assert user_new_udm.options.get("ucsschoolStudent", False) is False
            assert (
                user_new_udm.position == f"cn=lehrer und mitarbeiter,cn=users,ou={user_new.school},"
                f"{ldap_base}"
            )
            assert {
                f"{role}:school:{ou}" for ou in user_new.schools for role in ("staff", "teacher")
            }.issubset(user_new_ucsschool_roles)
            assert {f"student:school:{ou}" for ou in user_new.schools}.isdisjoint(
                user_new_ucsschool_roles
            )
        else:
            assert isinstance(user_new, Teacher)
            assert cls_dn1.lower() in new_groups
            assert cls_dn2.lower() in new_groups
            assert cls_dn3.lower() in new_groups
            assert user_new_udm.options.get("ucsschoolTeacher") is True
            assert user_new_udm.options.get("ucsschoolStaff", False) is False
            assert user_new_udm.options.get("ucsschoolStudent", False) is False
            assert user_new_udm.position == f"cn=lehrer,cn=users,ou={user_new.school},{ldap_base}"
            assert {f"teacher:school:{ou}" for ou in user_new.schools}.issubset(user_new_ucsschool_roles)
            assert {
                f"{role}:school:{ou}" for ou in user_new.schools for role in ("student", "staff")
            }.isdisjoint(user_new_ucsschool_roles)


@pytest.mark.asyncio
async def test_modify_role_forbidden(
    ldap_base,
    new_school_class_using_udm,
    udm_users_user_props,
    new_udm_user,
    udm_kwargs,
    schedule_delete_user_dn,
    create_multiple_ous,
):
    ou1, ou2 = await create_multiple_ous(2)
    # illegal source objects
    cls_dn, cls_attr = await new_school_class_using_udm(school=ou1)
    async with UDM(**udm_kwargs) as udm:
        sc_obj = await SchoolClass.from_dn(cls_dn, cls_attr["school"], udm)
        with pytest.raises(TypeError, match=r"is not an object of a 'User' subclass"):
            new_user_obj = await convert_to_staff(sc_obj, udm)
            schedule_delete_user_dn(new_user_obj.dn)

        dn, attr = await new_udm_user(ou1, "teacher")
        user_obj = await Teacher.from_dn(dn, ou1, udm)
        user_udm = await user_obj.get_udm_object(udm)
        user_udm.options["ucsschoolAdministrator"] = True
        with pytest.raises(TypeError, match=r"not allowed for school administrator"):
            new_user_obj = await convert_to_student(user_obj, udm)
            schedule_delete_user_dn(new_user_obj.dn)

    user_props = await udm_users_user_props(ou1)
    user_props["name"] = user_props.pop("username")
    user_props["school"] = ou1
    user_props["email"] = user_props.pop("mailPrimaryAddress")
    del user_props["description"]
    del user_props["e-mail"]

    user_obj = User(**user_props)
    with pytest.raises(TypeError, match=r"is not an object of a 'User' subclass"):
        new_user_obj = await convert_to_staff(user_obj, udm)
        schedule_delete_user_dn(new_user_obj.dn)

    user_obj = ExamStudent(**user_props)
    with pytest.raises(TypeError, match=r"from or to 'ExamStudent' is not allowed"):
        new_user_obj = await convert_to_teacher(user_obj, udm)
        schedule_delete_user_dn(new_user_obj.dn)

    # illegal convert target
    dn, attr = await new_udm_user(ou1, "student")
    async with UDM(**udm_kwargs) as udm:
        user_obj = await Student.from_dn(dn, attr["school"][0], udm)

        with pytest.raises(TypeError, match=r"is not a subclass of 'User'"):
            new_user_obj = await UserTypeConverter.convert(user_obj, User, udm)
            schedule_delete_user_dn(new_user_obj.dn)

        with pytest.raises(TypeError, match=r"from or to 'ExamStudent' is not allowed"):
            new_user_obj = await UserTypeConverter.convert(user_obj, ExamStudent, udm)
            schedule_delete_user_dn(new_user_obj.dn)

        with pytest.raises(TypeError, match=r"is not a subclass of 'User'"):
            new_user_obj = await UserTypeConverter.convert(user_obj, SchoolClass, udm)
            schedule_delete_user_dn(new_user_obj.dn)

        # no school_class for student target
        dn, attr = await new_udm_user(ou1, "staff")
        user_obj = await Staff.from_dn(dn, attr["school"][0], udm)
        with pytest.raises(TypeError, match=r"requires at least one school class per school"):
            new_user_obj = await UserTypeConverter.convert(user_obj, Student, udm)
            schedule_delete_user_dn(new_user_obj.dn)

        # not enough school_classes for student target
        dn, attr = await new_udm_user(ou1, "teacher")
        user_obj = await Teacher.from_dn(dn, ou1, udm)
        user_obj.schools.append(ou2)
        with pytest.raises(TypeError, match=r"requires at least one school class per school"):
            new_user_obj = await UserTypeConverter.convert(user_obj, Student, udm)
            schedule_delete_user_dn(new_user_obj.dn)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_move(create_multiple_ous, new_udm_user, role: Role, udm_kwargs):
    ou1, ou2 = await create_multiple_ous(2)
    dn, attr = await new_udm_user(ou1, role.name)
    assert attr["school"][0] == ou1
    async with UDM(**udm_kwargs) as udm:
        user = await role.klass.from_dn(dn, ou1, udm)
        user.school = ou2
        user.schools = [ou2]
        success = await user.change_school(ou2, udm)
        assert success is True
        users = await role.klass.get_all(udm, ou2, f"uid={user.name}")
    assert len(users) == 1
    user = users[0]
    assert user.school == ou2
    assert user.schools == [ou2]
    assert f"ou={ou1}" not in user.dn
    assert f"ou={ou2}" in user.dn


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_remove(create_ou_using_python, udm_kwargs, new_udm_user, role: Role):
    ou = await create_ou_using_python()
    dn, attr = await new_udm_user(ou, role.name)
    async with UDM(**udm_kwargs) as udm:
        user = await role.klass.from_dn(dn, ou, udm)
        assert await user.exists(udm)
        success = await user.remove(udm)
        assert success is True
        assert not await user.exists(udm)


unixhomes = {
    "student": "schueler",
    "teacher": "lehrer",
    "staff": "mitarbeiter",
    "teacher_and_staff": "lehrer",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_unixhome(
    create_ou_using_python, new_school_class_using_udm, udm_users_user_props, udm_kwargs, role: Role
):
    school = await create_ou_using_python()
    async with UDM(**udm_kwargs) as udm:
        user_props = await udm_users_user_props(school)
        user_props["name"] = user_props["username"]
        user_props["email"] = user_props["mailPrimaryAddress"]
        user_props["school"] = school
        user_props["birthday"] = str(user_props["birthday"])
        del user_props["e-mail"]
        if role.klass != Staff:
            cls_dn1, cls_attr1 = await new_school_class_using_udm(school=school)
            cls_dn2, cls_attr2 = await new_school_class_using_udm(school=school)
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
        udm_user = await user.get_udm_object(udm)
        assert f"/home/{school}/{unixhomes[role.name]}/{user.name}" == udm_user.props.unixhome
