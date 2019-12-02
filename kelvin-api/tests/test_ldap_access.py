import collections

import pytest

import ucsschool.kelvin.ldap_access
from udm_rest_client import UDM


@pytest.mark.asyncio
async def test_get_user():
    username = "Administrator"
    ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
    user_obj = await ldap_access.get_user(username, school_only=False)
    assert isinstance(user_obj, ucsschool.kelvin.ldap_access.LdapUser)
    assert user_obj.dn == f"uid={username},cn=users,{ldap_access.ldap_base}"


@pytest.mark.asyncio
async def test_admin_group_members():
    username = "Administrator"
    ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
    members = await ldap_access.admin_group_members()
    administrator_dn = f"uid={username},cn=users,{ldap_access.ldap_base}"
    assert isinstance(members, collections.abc.Sequence)
    assert administrator_dn in members


@pytest.mark.asyncio
async def test_udm_kwargs():
    ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
    udm_kwargs = await ucsschool.kelvin.ldap_access.udm_kwargs()
    async with UDM(**udm_kwargs) as udm:
        base_dn = await udm.session.base_dn
        assert base_dn == ldap_access.ldap_base
