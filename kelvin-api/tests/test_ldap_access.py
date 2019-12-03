import collections
from unittest.mock import patch

import pytest

import ucsschool.kelvin.constants
import ucsschool.kelvin.ldap_access
import ucsschool.lib.models.utils
from udm_rest_client import UDM

must_run_in_container = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)


@pytest.mark.asyncio
async def test_ldap_access_props(temp_file_func, random_name):
    tmp_file1 = temp_file_func()
    txt1 = random_name()
    tmp_file1.write_text(txt1)
    tmp_file2 = temp_file_func()
    txt2 = random_name()
    tmp_file2.write_text(txt2)
    with patch.object(
        ucsschool.kelvin.ldap_access, "CN_ADMIN_PASSWORD_FILE", tmp_file1
    ), patch("ucsschool.kelvin.ldap_access.MACHINE_PASSWORD_FILE", tmp_file2), patch(
        "ucsschool.kelvin.ldap_access._udm_kwargs", {}
    ):
        ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
        assert ldap_access.cn_admin == "cn=admin"
        assert txt1 == await ldap_access.cn_admin_password
        assert txt2 == await ldap_access.machine_password


@pytest.mark.asyncio
async def test_udm_kwargs_fake(temp_file_func, random_name):
    tmp_file1 = temp_file_func()
    txt1 = random_name()
    tmp_file1.write_text(txt1)
    tmp_file2 = temp_file_func()
    with patch("ucsschool.kelvin.ldap_access.CN_ADMIN_PASSWORD_FILE", tmp_file1), patch(
        "ucsschool.kelvin.ldap_access.MACHINE_PASSWORD_FILE", tmp_file2
    ), patch("ucsschool.kelvin.ldap_access._udm_kwargs", {}):
        udm_kwargs = await ucsschool.kelvin.ldap_access.udm_kwargs()
    assert udm_kwargs["username"] == "cn=admin"
    assert udm_kwargs["password"] == txt1
    host = ucsschool.lib.models.utils.env_or_ucr("ldap/master")
    assert udm_kwargs["url"] == f"https://{host}/univention/udm/"
    assert udm_kwargs["ssl_ca_cert"] == ucsschool.kelvin.constants.UCS_SSL_CA_CERT


@must_run_in_container
@pytest.mark.asyncio
async def test_get_user():
    username = "Administrator"
    ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
    user_obj = await ldap_access.get_user(username, school_only=False)
    assert isinstance(user_obj, ucsschool.kelvin.ldap_access.LdapUser)
    assert user_obj.dn == f"uid={username},cn=users,{ldap_access.ldap_base}"


@must_run_in_container
@pytest.mark.asyncio
async def test_admin_group_members():
    username = "Administrator"
    ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
    members = await ldap_access.admin_group_members()
    administrator_dn = f"uid={username},cn=users,{ldap_access.ldap_base}"
    assert isinstance(members, collections.abc.Sequence)
    assert administrator_dn in members


@must_run_in_container
@pytest.mark.asyncio
async def test_udm_kwargs_real():
    ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
    udm_kwargs = await ucsschool.kelvin.ldap_access.udm_kwargs()
    async with UDM(**udm_kwargs) as udm:
        base_dn = await udm.session.base_dn
        assert base_dn == ldap_access.ldap_base
