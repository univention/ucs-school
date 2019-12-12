import pytest
from faker import Faker
from ldap.filter import filter_format
from ucsschool.lib.models.group import Group, SchoolClass

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
        obj = await SchoolClass.from_dn(dn, attr["school"], udm)
    for key, value in attr.items():
        exp_value = value
        found_value = getattr(obj, key)
        if key == "name":
            exp_value = f"{attr['school']}-{exp_value}"
        if isinstance(exp_value, list):
            exp_value = set(exp_value)
            found_value = set(found_value)
        assert exp_value == found_value


@pytest.mark.asyncio
async def test_school_class_from_udm_obj(new_school_class, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        udm_mod = udm.get(SchoolClass._meta.udm_module)
        udm_obj = await udm_mod.get(dn)
        obj = await SchoolClass.from_udm_obj(udm_obj, attr["school"], udm)
        for key, value in attr.items():
            exp_value = value
            found_value = getattr(obj, key)
            if key == "name":
                exp_value = f"{attr['school']}-{exp_value}"
            if isinstance(exp_value, list):
                exp_value = set(exp_value)
                found_value = set(found_value)
            assert exp_value == found_value


@pytest.mark.asyncio
async def test_school_class_get_all(new_school_class, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        for obj in await SchoolClass.get_all(udm, attr["school"]):
            if obj.dn == dn:
                break
        else:
            raise AssertionError(
                f"DN {dn!r} not found in SchoolClass.get_all(udm, {attr['school']})."
            )
        filter_str = filter_format("(cn=%s)", (f"{attr['school']}-{attr['name']}",))
        objs = await SchoolClass.get_all(udm, attr["school"], filter_str=filter_str)
        assert len(objs) == 1
        for key, value in attr.items():
            exp_value = value
            found_value = getattr(objs[0], key)
            if key == "name":
                exp_value = f"{attr['school']}-{exp_value}"
            if isinstance(exp_value, list):
                exp_value = set(exp_value)
                found_value = set(found_value)
            assert exp_value == found_value


@pytest.mark.asyncio
async def test_school_class_get_class_for_udm_obj(new_school_class, udm_kwargs):
    dn, attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        obj = await SchoolClass.from_dn(dn, attr["school"], udm)
        udm_obj = await obj.get_udm_object(udm)
        udm_class = await Group.get_class_for_udm_obj(udm_obj, attr["school"])
        assert udm_class is SchoolClass


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


@pytest.mark.xfail(reason="new_ou() NotImplementedYet")
@pytest.mark.asyncio
async def test_school_class_move(new_school_class, new_ou, ldap_base, udm_kwargs):
    dn, attr = await new_school_class()
    ou_dn, ou_attr = new_ou()
    new_school = ou_attr["name"]
    async with UDM(**udm_kwargs) as udm:
        obj1 = await SchoolClass.from_dn(dn, attr["school"], udm)
        obj1.school = new_school
        obj1.change_school(new_school, udm)
        assert f"ou={new_school}" in obj1.dn
        assert f"ou={attr['school']}" not in obj1.dn
        obj2 = await SchoolClass.from_dn(obj1.dn, new_school, udm)
        for k, v in attr.items():
            exp_value = getattr(obj1, k)
            found_value = getattr(obj2, k)
            if isinstance(exp_value, list):
                exp_value = set(exp_value)
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
