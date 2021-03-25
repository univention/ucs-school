import random
from pathlib import Path
from typing import Set

import pytest
from ldap.filter import filter_format

from ucsschool.kelvin.ldap_access import LDAPAccess
from ucsschool.lib.create_ou import create_ou
from ucsschool.lib.models.computer import SchoolDCSlave
from ucsschool.lib.models.utils import env_or_ucr, exec_cmd, ucr
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_single_master,
    role_staff,
    role_student,
    role_teacher,
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


def create_school(host: str, ou_name: str):
    # todo refacture as fixture
    print(f"Creating school {ou_name!r} on host {host!r}...")
    if not Path("/usr/bin/ssh").exists() or not Path("/usr/bin/sshpass").exists():
        print("Installing 'ssh' and 'sshpass'...")
        returncode, stdout, stderr = exec_cmd(["apk", "add", "--no-cache", "openssh", "sshpass"])
        print(f"stdout={stdout}")
        print(f"stderr={stderr}")
    print(f"ssh to {host!r} to create {ou_name!r} with /usr/share/ucs-school-import/scripts/create_ou")
    short_ou_name = f"{ou_name}"[:13]
    returncode, stdout, stderr = exec_cmd(
        [
            "/usr/bin/sshpass",
            "-p",
            "univention",
            "/usr/bin/ssh",
            "-o",
            "StrictHostKeyChecking no",
            f"root@{host}",
            "/usr/share/ucs-school-import/scripts/create_ou",
            ou_name,
            f"edu{short_ou_name}",
            f"adm{short_ou_name}",
            f"--sharefileserver=edu{short_ou_name}",
            f"--displayName='displ {ou_name}'",
            f"--alter-dhcpd-base=false",
        ]
    )
    stdout = stdout.decode()
    stderr = stderr.decode()
    print(f"stdout={stdout}")
    print(f"stderr={stderr}")
    assert (not stderr) or ("Already attached!" in stderr) or ("created successfully" in stderr)
    if "Already attached!" in stderr:
        print(f" => OU {ou_name!r} exists in {host!r}.")
    else:
        print(f" => OU {ou_name!r} created in {host!r}.")


async def get_all_host_dns() -> Set[str]:
    lo = LDAPAccess()
    return set(e.entry_dn for e in await lo.search("(!(sn=dummy))", []))


async def create_test_ou(ou_name, udm):
    return await create_ou(
        ou_name=ou_name,
        display_name=f"displ {ou_name}",
        edu_name=f"edu{ou_name}"[:13],
        admin_name=f"adm{ou_name}"[:13],
        share_name=f"edu{ou_name}",
        lo=udm,
        baseDN=env_or_ucr("ldap/base"),
        hostname=env_or_ucr("hostname"),
        is_single_master=ucr.is_true("ucsschool/singlemaster"),
        alter_dhcpd_base=False,
    )


@pytest.mark.asyncio
async def test_create_ou(udm_kwargs, ldap_base):
    """
    - create school via ssh and get new dns after creation
    - create school via kelvin and get new dns after creation
    - compare them exclusive ou=name
    """
    all_dns_0 = await get_all_host_dns()
    # create an ou via ssh

    ou_name_ssh = f"ou{random.randint(100, 999)}"  # nosec
    create_school(host=env_or_ucr("docker_host_name"), ou_name=ou_name_ssh)
    all_dns_1 = await get_all_host_dns()
    # safe the dns of the objects after school creation
    dns_after_ssh_school_creation = {
        dn
        for dn in all_dns_1.difference(all_dns_0)
        if not dn.endswith(f"cn=temporary,cn=univention,{ldap_base}")
    }
    ou_name_kelvin = f"ou{random.randint(100, 999)}"  # nosec
    async with UDM(**udm_kwargs) as udm:
        await create_test_ou(ou_name_kelvin, udm)
        all_dns_2 = await get_all_host_dns()
    dns_after_kelvin_school_creation = all_dns_2.difference(all_dns_1)
    # the new objects should be the same except for the ou name.
    dns_after_kelvin_school_creation = set(
        dn.replace(ou_name_kelvin, ou_name_ssh)
        for dn in dns_after_kelvin_school_creation
        if not dn.endswith(f"cn=temporary,cn=univention,{ldap_base}")
    )
    with open("/tmp/log", "w") as fp:
        fp.write(
            f"in kelvin, but not in ssh: {sorted(dns_after_kelvin_school_creation - dns_after_ssh_school_creation)}\n"
        )
        fp.write(
            f"in ssh, but not in kelvin: {sorted(dns_after_ssh_school_creation - dns_after_kelvin_school_creation)}\n"
        )
    assert (dns_after_kelvin_school_creation ^ dns_after_ssh_school_creation) == set()


@pytest.mark.asyncio
async def test_attached_policies(udm_kwargs):
    """
    when creating schools, policies get attached in
    - create_import_group
    - create_dhcp_dns_policy
    - create_dhcp_search_base
    this tests if they are attached as expected.
    """
    async with UDM(**udm_kwargs) as udm:
        ou = f"ou{random.randint(100, 999)}"  # nosec
        await create_test_ou(ou, udm)

        ou_dn = "ou={},{}".format(ou, env_or_ucr("ldap/base"))
        udm_mod = udm.get("policies/registry")
        udm_obj = await udm_mod.get("cn=ou-default-ucr-policy,cn=policies,{}".format(ou_dn))
        assert "cn=dhcp,{}".format(ou_dn.lower()) == udm_obj.props.registry["dhcpd/ldap/base"]

        udm_obj = await udm.get("container/ou").get(ou_dn)
        policy_dn = "cn=ou-default-ucr-policy,cn=policies,{}".format(ou_dn).lower()
        assert policy_dn in udm_obj.policies["policies/registry"]

        dhcp_dns_policy_dn = "cn=dhcp-dns-{},cn=policies,{}".format(ou.lower(), ou_dn)
        udm_obj = await udm.get("container/cn").get("cn=dhcp,{}".format(ou_dn))
        assert dhcp_dns_policy_dn in udm_obj.policies["policies/dhcp_dns"]

        udm_mod = udm.get("groups/group")
        ou_import_group = "cn={}-import-all,cn=groups,{}".format(ou, ou_dn)
        udm_obj = await udm_mod.get(ou_import_group)
        assert (
            "cn=schoolimport-all,cn=UMC,cn=policies,{}".format(env_or_ucr("ldap/base"))
            in udm_obj.policies["policies/umc"]
        )
        assert "ucsschoolImportGroup" in udm_obj.options
        assert [ou] == udm_obj.props.ucsschoolImportSchool
        for role in [role_student, role_staff, "teacher_and_staff", role_teacher]:
            assert role in udm_obj.props.ucsschoolImportRole


@pytest.mark.asyncio
async def test_ucsschool_roles(udm_kwargs):
    """
    when creating schools, ucsschool roles should get appended to
    the school server
    """
    async with UDM(**udm_kwargs) as udm:
        ou_name = f"ou{random.randint(100, 999)}"  # nosec
        await create_test_ou(ou_name, udm)
        if ucr.is_true("ucsschool/singlemaster", True):
            filter_s = filter_format("cn=%s", [ucr["ldap/master"].split(".", 1)[0]])
            mod = udm.get("computers/domaincontroller_master")
            obj = [o async for o in mod.search(filter_s)][0]
            ucsschool_role = create_ucsschool_role_string(role_single_master, ou_name)
            assert ucsschool_role in obj.props.ucsschoolRole
        else:
            ou_lower = ou_name.lower()
            adm_net_filter = "cn=OU{}-DC-Verwaltungsnetz".format(ou_lower)
            edu_net_filter = "cn=OU{}-DC-Edukativnetz".format(ou_lower)
            base = "cn=ucsschool,cn=groups,{}".format(ucr["ldap/base"])
            for ldap_filter, role in [
                (adm_net_filter, "dc_slave_admin"),
                (edu_net_filter, "dc_slave_edu"),
            ]:
                groups = [grp async for grp in udm.get("groups/group").search(ldap_filter, base=base)]
                if groups:
                    try:
                        server_dn: str = groups[0].props.hosts[0]
                    except IndexError:
                        continue
                    try:
                        await udm.get("computers/domaincontroller_slave").get(server_dn)
                    except UdmNoObject:
                        assert True is False, "A DC slave was expected at {}".format(server_dn)

                    obj = await SchoolDCSlave.from_dn(server_dn, ou_name, udm)
                    ucsschool_role = create_ucsschool_role_string(role, ou_name)
                    assert ucsschool_role in obj.ucsschool_roles
