import pytest
from faker import Faker
from ucsschool.lib.models.user import (
    ExamStudent,
    Staff,
    Student,
    Teacher,
    TeachersAndStaff,
    User,
)
from udm_rest_client import UDM, NoObject as UdmNoObject


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


@pytest.mark.asyncio
async def test_user_exists(new_user, udm_kwargs):
    dn, attr = await new_user("student")
    async with UDM(**udm_kwargs) as udm:
        user0 = await User.from_dn(dn, attr["school"][0], udm)
        assert await user0.exists(udm) is True
        user1 = User(name=attr["username"], school=attr["school"][0])
        assert await user1.exists(udm) is True
        user2 = User(name=fake.pystr(), school=attr["school"][0])
        assert await user2.exists(udm) is False


@pytest.mark.asyncio
async def test_user_type_is_converted(new_user, role2class, udm_kwargs):
    async with UDM(**udm_kwargs) as udm:
        for user_type in ("staff", "student", "teacher", "teacher_and_staff"):
            dn, attr = await new_user(user_type)
            user0 = await User.from_dn(dn, attr["school"][0], udm)
            assert await user0.exists(udm) is True
            exp_cls = role2class[user_type]
            assert isinstance(user0, exp_cls)


@pytest.mark.asyncio
async def test_read_user(new_user, udm_kwargs):
    cls_mapping = {
        "student": Student,
        "teacher": Teacher,
        "teacher_and_staff": TeachersAndStaff,
        "staff": Staff,
    }
    async with UDM(**udm_kwargs) as lo_udm:
        for user_role in ("student", "teacher", "staff", "teacher_and_staff"):
            user_cls = cls_mapping[user_role]
            dn, attr = await new_user(user_role)
            user = await user_cls.from_dn(dn, attr["school"][0], lo_udm)
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


# @pytest.mark.asyncio
# async def test_create_user(
#     create_new_user, udm_kwargs
# ):
#     async with UDM(**udm_kwargs) as lo_udm:
#         user_cls = user_attrs.pop("user_cls")
#         print(f"** user_cls={user_cls!r}")
#         cls = globals()[user_cls]
#         print(f"** cls={cls!r}")
#         user = cls(**user_attrs)
#         print("** type(user)=%r user.to_dict()={!r}".format(type(user), user.to_dict()))
#         await user.create(lo_udm)
#         result, returncode = get_user_via_ssh(user.dn)
#         print("** result={!r} returncode={!r}".format(result, returncode))
#         assert isinstance(result, dict)
#         try:
#             for k, value_here in user.to_dict().items():
#                 val_here = value_here
#                 val_ssh = result.get(k)
#                 if k == "disabled" and isinstance(val_ssh, str):
#                     val_ssh = bool(int(val_ssh))
#                 if isinstance(val_here, list):
#                     val_here = set(val_here)
#                     val_ssh = set(val_ssh)
#                 assert (
#                     val_here == val_ssh
#                 ), f"k={k!r} val_here={val_here!r} val_ssh={val_ssh!r}"
#             print("** OK, deleting user...")
#         finally:
#             result, returncode = remove_user_via_ssh(user.dn)
#             assert returncode == 0
#         assert not await User(**user_attrs).exists(lo_udm)


@pytest.mark.asyncio
async def test_remove_user(udm_kwargs, new_user):
    cls_mapping = {
        "student": Student,
        "teacher": Teacher,
        "teacher_and_staff": TeachersAndStaff,
        "staff": Staff,
    }
    async with UDM(**udm_kwargs) as lo_udm:
        for user_role in ("student", "teacher", "staff", "teacher_and_staff"):
            user_cls = cls_mapping[user_role]
            dn, attr = await new_user(user_role)
            user = await user_cls.from_dn(dn, attr["school"][0], lo_udm)
            assert await user.exists(lo_udm)
            await user.remove(lo_udm)
            assert not await user.exists(lo_udm)
