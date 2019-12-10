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
async def test_school_class_exists(new_school_class, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        sc0 = await SchoolClass.from_dn(dn, attr["school"], udm)
        assert await sc0.exists(udm) is True
        sc1 = SchoolClass(name=f"{attr['school']}-{attr['name']}", school=attr["school"])
        assert await sc1.exists(udm) is True
        sc2 = SchoolClass(name=f"{attr['school']}-{fake.pystr()}", school=attr["school"])
        assert await sc2.exists(udm) is False


@pytest.mark.asyncio
async def test_school_class_from_dn(new_school_class, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        sc = await SchoolClass.from_dn(dn, attr["school"], udm)
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


@pytest.mark.asyncio
async def test_school_class_create(school_class_attrs, udm_kwargs):
    sc_attrs = school_class_attrs()
    async with UDM(**udm_kwargs) as udm:
        sc1 = SchoolClass(**sc_attrs)
        success = await sc1.create(udm)
        assert success
    async with UDM(**udm_kwargs) as udm:
        sc2 = await SchoolClass.from_dn(sc1.dn, sc_attrs["school"], udm)
    for key, exp_value in sc_attrs.items():
        found_value = getattr(sc2, key)
        if isinstance(exp_value, list):
            exp_value = set(exp_value)
            found_value = set(found_value)
        assert exp_value == found_value


@pytest.mark.asyncio
async def test_school_class_modify(new_school_class, new_user, ldap_base, udm_kwargs):
    dn, attr = await new_school_class()
    dn_user, attr_user = await new_user("student")
    async with UDM(**udm_kwargs) as udm:
        sc1 = await SchoolClass.from_dn(dn, attr["school"], udm)
        description_new = fake.text(max_nb_chars=50)
        sc1.description = description_new
        sc1.users.append(dn_user)
        await sc1.modify(udm)
    async with UDM(**udm_kwargs) as udm:
        sc2 = await SchoolClass.from_dn(dn, attr["school"], udm)
    for k, v in attr.items():
        exp_value = getattr(sc1, k)
        found_value = getattr(sc2, k)
        if k == "users":
            exp_value = set(exp_value)
            exp_value.add(dn_user)
            found_value = set(found_value)
        assert exp_value == found_value


@pytest.mark.asyncio
async def test_school_class_remove(new_school_class, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        sc = await SchoolClass.from_dn(dn, attr["school"], udm)
        await sc.remove(udm)
        assert sc.dn is None
    async with UDM(**udm_kwargs) as udm:
        with pytest.raises(UdmNoObject):
            await udm.obj_by_dn(dn)
