import pytest
from faker import Faker
from ucsschool.lib.models.group import SchoolClass

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
async def test_read_school_class(new_school_class, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        sc = await SchoolClass.from_dn(dn, attr["school"], udm)
    print("** sc.to_dict()={!r}".format(sc.to_dict()))
    for k, v in attr.items():
        val1 = v
        val2 = getattr(sc, k)
        if k == "name":
            val2 = val2.replace(f"{attr['school']}-", "")
        if isinstance(v, list):
            val1 = set(val1)
            val2 = set(val2)
        assert val1 == val2, "k={!r} v={!r} getattr(sc, k)={!r}".format(
            k, v, getattr(sc, k)
        )


@pytest.mark.xfail(reason="Creation of share fails.")
@pytest.mark.asyncio
async def test_create_school_class(school_class_attrs, udm_kwargs):
    async with UDM(**udm_kwargs) as udm:
        sc1 = SchoolClass(**school_class_attrs)
        success = await sc1.create(udm)
        print("** sc1.to_dict()={!r}".format(sc1.to_dict()))
        assert success
    async with UDM(**udm_kwargs) as udm:
        sc2 = await SchoolClass.from_dn(sc1.dn, school_class_attrs["school"], udm)
        print("** sc2.to_dict()={!r}".format(sc2.to_dict()))
    for k, v in school_class_attrs.items():
        assert getattr(sc1, k) == getattr(sc2, k)


@pytest.mark.asyncio
async def test_modify_school_class(new_school_class, ldap_base, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        sc1 = await SchoolClass.from_dn(dn, attr["school"], udm)
        print("** sc1.to_dict()={!r}".format(sc1.to_dict()))
        description_new = fake.text(max_nb_chars=50)
        sc1.description = description_new
        sc1.users.append(f"uid={fake.user_name()},cn=users,{ldap_base}")
        await sc1.modify(udm)
    async with UDM(**udm_kwargs) as udm:
        sc2 = await SchoolClass.from_dn(dn, attr["school"], udm)
        print("** sc2.to_dict()={!r}".format(sc2.to_dict()))
    for k, v in attr.items():
        assert getattr(sc1, k) == getattr(sc2, k)


@pytest.mark.asyncio
async def test_delete_school_class(new_school_class, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        sc = await SchoolClass.from_dn(dn, attr["school"], udm)
        print("** sc.to_dict()={!r}".format(sc.to_dict()))
        await sc.remove(udm)
        assert sc.dn is None
    async with UDM(**udm_kwargs) as udm:
        with pytest.raises(UdmNoObject):
            await udm.obj_by_dn(dn)
