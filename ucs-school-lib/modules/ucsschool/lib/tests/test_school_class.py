from typing import Any, Dict, List

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


def assert_attr_eq_school_obj_attr(attr: Dict[str, Any], obj: SchoolClass) -> None:
    for key, value in attr.items():
        exp_value = value
        found_value = getattr(obj, key)
        if key == "name":
            exp_value = f"{attr['school']}-{exp_value}"
        if isinstance(exp_value, list):
            exp_value = set(exp_value)
            found_value = set(found_value)
        assert exp_value == found_value


def assert_eq_objs(obj1: SchoolClass, obj2: SchoolClass, comprare_attrs: List[str]):
    for attr in comprare_attrs:
        exp_value = getattr(obj1, attr)
        found_value = getattr(obj2, attr)
        if attr == "users":
            exp_value = set(exp_value)
            found_value = set(found_value)
        assert exp_value == found_value


@pytest.mark.asyncio
async def test_exists(create_ou_using_python, new_school_class_using_udm, udm_kwargs):
    ou = await create_ou_using_python()
    dn, attr = await new_school_class_using_udm(ou)
    async with UDM(**udm_kwargs) as udm:
        sc0 = await SchoolClass.from_dn(dn, ou, udm)
        assert await sc0.exists(udm) is True
        sc1 = SchoolClass(name=f"{ou}-{attr['name']}", school=ou)
        assert await sc1.exists(udm) is True
        sc2 = SchoolClass(name=f"{ou}-{fake.pystr()}", school=ou)
        assert await sc2.exists(udm) is False


@pytest.mark.asyncio
async def test_from_dn(create_ou_using_python, new_school_class_using_udm, udm_kwargs):
    ou = await create_ou_using_python()
    dn, attr = await new_school_class_using_udm(ou)
    async with UDM(**udm_kwargs) as udm:
        obj = await SchoolClass.from_dn(dn, ou, udm)
    assert_attr_eq_school_obj_attr(attr, obj)


@pytest.mark.asyncio
async def test_from_udm_obj(create_ou_using_python, new_school_class_using_udm, udm_kwargs):
    ou = await create_ou_using_python()
    dn, attr = await new_school_class_using_udm(ou)
    async with UDM(**udm_kwargs) as udm:
        udm_mod = udm.get(SchoolClass._meta.udm_module)
        udm_obj = await udm_mod.get(dn)
        obj = await SchoolClass.from_udm_obj(udm_obj, ou, udm)
        assert_attr_eq_school_obj_attr(attr, obj)


@pytest.mark.asyncio
async def test_get_all(create_ou_using_python, new_school_class_using_udm, udm_kwargs):
    ou = await create_ou_using_python()
    dn, attr = await new_school_class_using_udm(ou)
    async with UDM(**udm_kwargs) as udm:
        for obj in await SchoolClass.get_all(udm, ou):
            if obj.dn == dn:
                break
        else:
            raise AssertionError(f"DN {dn!r} not found in SchoolClass.get_all(udm, {ou}).")
        filter_str = filter_format("(cn=%s)", (f"{ou}-{attr['name']}",))
        objs = await SchoolClass.get_all(udm, ou, filter_str=filter_str)
        assert len(objs) == 1
        assert_attr_eq_school_obj_attr(attr, objs[0])


@pytest.mark.asyncio
async def test_get_class_for_udm_obj(create_ou_using_python, new_school_class_using_udm, udm_kwargs):
    ou = await create_ou_using_python()
    dn, attr = await new_school_class_using_udm(ou)
    async with UDM(**udm_kwargs) as udm:
        udm_obj = await udm.get(SchoolClass._meta.udm_module).get(dn)
        klass = await Group.get_class_for_udm_obj(udm_obj, ou)
        assert klass is SchoolClass
        obj = await SchoolClass.from_dn(dn, ou, udm)
        assert await obj.exists(udm) is True
        assert isinstance(obj, SchoolClass)


@pytest.mark.asyncio
async def test_from_dn(create_ou_using_python, new_school_class_using_udm, udm_kwargs):
    ou = await create_ou_using_python()
    dn, attr = await new_school_class_using_udm(ou)
    async with UDM(**udm_kwargs) as udm:
        sc = await SchoolClass.from_dn(dn, ou, udm)
    assert_attr_eq_school_obj_attr(attr, sc)


@pytest.mark.asyncio
async def test_create(create_ou_using_python, school_class_attrs, udm_kwargs):
    ou = await create_ou_using_python()
    sc_attrs = await school_class_attrs(ou)
    create_attr = sc_attrs.copy()
    create_attr["name"] = f"{ou}-{create_attr['name']}"
    async with UDM(**udm_kwargs) as udm:
        sc1 = SchoolClass(**create_attr)
        success = await sc1.create(udm)
        assert success is True
    async with UDM(**udm_kwargs) as udm:
        sc2 = await SchoolClass.from_dn(sc1.dn, ou, udm)
    assert_attr_eq_school_obj_attr(sc_attrs, sc2)


@pytest.mark.asyncio
async def test_modify(create_ou_using_python, new_school_class_using_udm, new_udm_user, udm_kwargs):
    ou = await create_ou_using_python()
    dn, attr = await new_school_class_using_udm(ou)
    dn_user, attr_user = await new_udm_user(ou, "student")
    async with UDM(**udm_kwargs) as udm:
        sc1 = await SchoolClass.from_dn(dn, ou, udm)
        description_new = fake.text(max_nb_chars=50)
        sc1.description = description_new
        sc1.users.append(dn_user)
        success = await sc1.modify(udm)
        assert success is True
    async with UDM(**udm_kwargs) as udm:
        sc2 = await SchoolClass.from_dn(dn, ou, udm)
    assert_eq_objs(sc1, sc2, attr.keys())


@pytest.mark.asyncio
async def test_move(create_multiple_ous, new_school_class_using_udm, udm_kwargs):
    old_school, new_school = await create_multiple_ous(2)
    dn, attr = await new_school_class_using_udm(school=old_school)
    assert f"ou={old_school}" in dn
    async with UDM(**udm_kwargs) as udm:
        obj1 = await SchoolClass.from_dn(dn, old_school, udm)
        assert obj1.school == old_school
        obj1.name = f"{new_school}-{obj1.name[len(old_school) + 1:]}"
        obj1.school = new_school
        success = await obj1.move(udm)
        assert success is False  # moving school classes is not allowed


@pytest.mark.asyncio
async def test_remove(create_ou_using_python, new_school_class_using_udm, udm_kwargs):
    ou = await create_ou_using_python()
    dn, attr = await new_school_class_using_udm(ou)
    async with UDM(**udm_kwargs) as udm:
        sc = await SchoolClass.from_dn(dn, ou, udm)
        success = await sc.remove(udm)
        assert success is True
        assert sc.dn is None
    async with UDM(**udm_kwargs) as udm:
        with pytest.raises(UdmNoObject):
            await udm.obj_by_dn(dn)
