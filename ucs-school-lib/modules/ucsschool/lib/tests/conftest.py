import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from faker import Faker

import ucsschool.lib.models.user
from ucsschool.lib.create_ou import create_ou
from ucsschool.lib.models.utils import env_or_ucr, exec_cmd, get_file_handler, ucr
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_school_class,
    role_school_class_share,
    role_staff,
    role_teacher,
)
from ucsschool.lib.schoolldap import SchoolSearchBase
from udm_rest_client import UDM, NoObject as UdmNoObject

APP_ID = "ucsschool-kelvin-rest-api"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = APP_BASE_PATH / "conf"
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"
UCS_SSL_CA_CERT = "/usr/local/share/ca-certificates/ucs.crt"

fake = Faker()


@pytest.fixture(scope="session")
def ldap_base():
    return env_or_ucr("ldap/base")


@pytest.fixture(scope="session")
def random_user_name():
    return fake.user_name


@pytest.fixture(scope="session")
def random_first_name():
    return fake.first_name


@pytest.fixture(scope="session")
def random_last_name():
    return fake.last_name


@pytest.fixture(scope="session")
def udm_kwargs() -> Dict[str, Any]:
    with open(CN_ADMIN_PASSWORD_FILE, "r") as fp:
        cn_admin_password = fp.read().strip()
    host = env_or_ucr("ldap/master")
    return {
        "username": "cn=admin",
        "password": cn_admin_password,
        "url": f"https://{host}/univention/udm/",
        "ssl_ca_cert": UCS_SSL_CA_CERT,
    }


@pytest.fixture
def school_class_attrs(ldap_base):
    def _func(**kwargs) -> Dict[str, str]:
        res = {
            "name": f"test.{fake.user_name()}",
            "school": "DEMOSCHOOL",
            "description": fake.text(max_nb_chars=50),
            "users": [
                f"uid={fake.user_name()},cn=users,{ldap_base}",
                f"uid={fake.user_name()},cn=users,{ldap_base}",
            ],
            "ucsschool_roles": [create_ucsschool_role_string(role_school_class, "DEMOSCHOOL")],
        }
        res.update(kwargs)
        return res

    return _func


@pytest.fixture
def users_user_props(ldap_base):
    def _func() -> Dict[str, str]:
        return {
            "firstname": fake.first_name(),
            "lastname": fake.last_name(),
            "username": f"test.{fake.user_name()}".lower()[:15],
            "school": ["DEMOSCHOOL"],
            "birthday": fake.date_of_birth(minimum_age=6, maximum_age=65),
            "mailPrimaryAddress": None,
            "description": fake.text(max_nb_chars=50),
            "password": fake.password(),
            "disabled": False,
        }

    return _func


@pytest.fixture
async def new_school_class(udm_kwargs, ldap_base, school_class_attrs):
    """Create a new school class"""
    created_school_classes = []
    created_school_shares = []

    async def _func(**kwargs) -> Tuple[str, Dict[str, str]]:
        async with UDM(**udm_kwargs) as udm:
            sc_attrs = school_class_attrs(**kwargs)
            grp_obj = await udm.get("groups/group").new()
            grp_obj.position = f"cn=klassen,cn=schueler,cn=groups,ou={sc_attrs['school']},{ldap_base}"
            grp_obj.props.name = f"{sc_attrs['school']}-{sc_attrs['name']}"
            grp_obj.props.description = sc_attrs["description"]
            grp_obj.props.users = sc_attrs["users"]
            grp_obj.props.ucsschoolRole = sc_attrs["ucsschool_roles"]
            await grp_obj.save()
            created_school_classes.append(grp_obj.dn)
            print("Created new SchoolClass: {!r}".format(grp_obj))

            share_obj = await udm.get("shares/share").new()
            share_obj.position = f"cn=klassen,cn=shares,ou={sc_attrs['school']},{ldap_base}"
            share_obj.props.name = grp_obj.props.name
            share_obj.props.host = f"{sc_attrs['school']}.{env_or_ucr('domainname')}"
            share_obj.props.owner = 0
            share_obj.props.group = 0
            share_obj.props.path = f"/home/tmp/{grp_obj.props.name}"
            share_obj.props.directorymode = "0770"
            share_obj.props.ucsschoolRole = [
                create_ucsschool_role_string(role_school_class_share, sc_attrs["school"]),
            ]
            await share_obj.save()
            created_school_shares.append(share_obj.dn)
            print("Created new ClassShare: {!r}".format(share_obj))

        return grp_obj.dn, sc_attrs

    yield _func

    async with UDM(**udm_kwargs) as udm:
        grp_mod = udm.get("groups/group")
        for dn in created_school_classes:
            try:
                grp_obj = await grp_mod.get(dn)
            except UdmNoObject:
                print(f"SchoolClass {dn!r} does not exist (anymore).")
                continue
            await grp_obj.delete()
            print(f"Deleted SchoolClass {dn!r} through UDM.")
        share_mod = udm.get("shares/share")
        for dn in created_school_shares:
            try:
                share_obj = await share_mod.get(dn)
            except UdmNoObject:
                print(f"ClassShare {dn!r} does not exist (anymore).")
                continue
            await share_obj.delete()
            print(f"Deleted ClassShare {dn!r} through UDM.")


@pytest.fixture
async def new_user(udm_kwargs, ldap_base, users_user_props, new_school_class, schedule_delete_user_dn):
    """Create a new user"""

    async def _func(role) -> Tuple[str, Dict[str, str]]:
        assert role in ("staff", "student", "teacher", "teacher_and_staff")
        user_props = users_user_props()
        school = user_props["school"][0]
        if role == "teacher_and_staff":
            user_props["ucsschoolRole"] = [
                create_ucsschool_role_string(role_staff, school),
                create_ucsschool_role_string(role_teacher, school),
            ]
        else:
            user_props["ucsschoolRole"] = [create_ucsschool_role_string(role, school)]
        school_search_base = SchoolSearchBase(user_props["school"])
        options = {
            "staff": ("ucsschoolStaff",),
            "student": ("ucsschoolStudent",),
            "teacher": ("ucsschoolTeacher",),
            "teacher_and_staff": ("ucsschoolStaff", "ucsschoolTeacher"),
        }[role]
        position = {
            "staff": school_search_base.staff,
            "student": school_search_base.students,
            "teacher": school_search_base.teachers,
            "teacher_and_staff": school_search_base.teachersAndStaff,
        }[role]
        async with UDM(**udm_kwargs) as udm:
            user_obj = await udm.get("users/user").new()
            user_obj.options.update(dict((opt, True) for opt in options))
            user_obj.position = position
            user_obj.props.update(user_props)
            user_obj.props.primaryGroup = f"cn=Domain Users {school},cn=groups,ou={school},{ldap_base}"
            user_obj.props.groups.append(user_obj.props.primaryGroup)
            if role != "staff":
                cls_dn1, _ = await new_school_class()
                cls_dn2, _ = await new_school_class()
                user_obj.props.groups.extend([cls_dn1, cls_dn2])
            await user_obj.save()
            schedule_delete_user_dn(user_obj.dn)
            print(f"Created new {role!r}: {user_obj!r}")

        return user_obj.dn, user_props

    yield _func


@pytest.fixture
async def schedule_delete_user_dn(udm_kwargs):
    dns = []

    def _func(dn: str):
        dns.append(dn)

    yield _func

    async with UDM(**udm_kwargs) as udm:
        user_mod = udm.get("users/user")
        for dn in dns:
            try:
                user_obj = await user_mod.get(dn)
            except UdmNoObject:
                print(f"User {dn!r} does not exist (anymore).")
                continue
            await user_obj.delete()
            print(f"Deleted user {dn!r} through UDM.")


@pytest.fixture
def role2class():
    return {
        "staff": ucsschool.lib.models.user.Staff,
        "student": ucsschool.lib.models.user.Student,
        "teacher": ucsschool.lib.models.user.Teacher,
        "teacher_and_staff": ucsschool.lib.models.user.TeachersAndStaff,
    }


@pytest.fixture
def cn_attrs(ldap_base):
    raise NotImplementedError


@pytest.fixture
async def new_cn(udm_kwargs, ldap_base, cn_attrs):
    """Create a new container"""
    created_cns = []

    async def _func() -> Tuple[str, Dict[str, str]]:
        async with UDM(**udm_kwargs) as udm:
            attr = cn_attrs()
            obj = await udm.get("container/cn").new()
            obj.position = f"ou={attr['school']},{ldap_base}"
            obj.props.name = attr["name"]
            obj.props.description = attr["description"]
            await obj.save()
            created_cns.append(obj.dn)
            print("Created new container: {!r}".format(obj))

        return obj.dn, attr

    yield _func

    async with UDM(**udm_kwargs) as udm:
        mod = udm.get("container/cn")
        for dn in created_cns:
            try:
                obj = await mod.get(dn)
            except UdmNoObject:
                print(f"Container {dn!r} does not exist (anymore).")
                continue
            await obj.delete()
            print(f"Deleted container {dn!r}.")


@pytest.fixture
def ou_attrs(ldap_base):
    raise NotImplementedError


@pytest.fixture
async def new_ou(udm_kwargs, ldap_base, ou_attrs):
    """Create a new school (OU)"""
    created_ous = []

    async def _func() -> Tuple[str, Dict[str, str]]:
        raise NotImplementedError
        print(f"Created new OU: {TODO!r}")

    yield _func
    print(f"Deleted OU 'TODO'.")


@pytest.fixture
async def demoschool2(create_ou_using_python, ldap_base) -> Tuple[str, str]:
    """Create DEMOSCHOOL2, return (DN, name)"""
    name = "DEMOSCHOOL2"
    dn = f"ou={name},{ldap_base}"

    await create_ou_using_python(name)
    return dn, name


@pytest.fixture
def random_logger():
    with tempfile.NamedTemporaryFile() as f:
        handler = get_file_handler("DEBUG", f.name)
        logger = logging.getLogger(f.name)
        logger.addHandler(handler)
        logger.setLevel("DEBUG")
        yield logger


@pytest.fixture(scope="session")
def installed_ssh():
    if not Path("/usr/bin/ssh").exists() or not Path("/usr/bin/sshpass").exists():
        print("Installing 'ssh' and 'sshpass'...")
        returncode, stdout, stderr = exec_cmd(
            ["apk", "add", "--no-cache", "openssh", "sshpass"], log=True
        )
        print(f"stdout={stdout}")
        print(f"stderr={stderr}")
    else:
        print("'ssh' and 'sshpass' are already installed.")


@pytest.fixture(scope="session")
def exec_with_ssh(installed_ssh):
    def _func(cmd: List[str], host: str = None) -> Tuple[int, str, str]:
        host = host or env_or_ucr("docker_host_name")
        ssh_cmd = [
            "/usr/bin/sshpass",
            "-p",
            "univention",
            "/usr/bin/ssh",
            "-o",
            "StrictHostKeyChecking no",
            f"root@{host}",
        ] + cmd
        print(f"ssh to {host!r} and execute: {cmd!r}...")
        returncode, stdout, stderr = exec_cmd(ssh_cmd, log=True)
        print(f"stdout={stdout}")
        print(f"stderr={stderr}")
        return returncode, stdout, stderr

    return _func


@pytest.fixture
async def schedule_delete_ou_using_ssh(exec_with_ssh, ldap_base):
    ous_created: List[Tuple[str, str]] = []

    def _func(ou_name: str, host: str):
        ous_created.append((ou_name, host))

    yield _func

    for ou_name, host in ous_created:
        print(f"Deleting OU {ou_name!r} on host {host!r}...")
        dn = f"ou={ou_name},{ldap_base}"
        exec_with_ssh(["/usr/sbin/udm", "container/ou", "remove", "--dn", dn], host)
        group_dns = [
            f"cn=admins-{ou_name.lower()},cn=ouadmins,cn=groups,{ldap_base}",
            f"cn=OU{ou_name}-Klassenarbeit,cn=ucsschool,cn=groups,{ldap_base}",
            f"cn=OU{ou_name.lower()}-DC-Edukativnetz,cn=ucsschool,cn=groups,{ldap_base}",
            f"cn=OU{ou_name.lower()}-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{ldap_base}",
            f"cn=OU{ou_name.lower()}-Member-Edukativnetz,cn=ucsschool,cn=groups,{ldap_base}",
            f"cn=OU{ou_name.lower()}-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{ldap_base}",
        ]
        group_dns_s = " ".join("'{}'".format(dn) for dn in group_dns)
        cmd = f"'for DN in {group_dns_s}; do /usr/sbin/udm groups/group remove --dn \"$DN\"; done'"
        print(f"Deleting groups on host {host!r}: {group_dns!r}...")
        exec_with_ssh(["/bin/bash", "-c", cmd], host)


@pytest.fixture
def create_ou_using_ssh(exec_with_ssh, ldap_base, schedule_delete_ou_using_ssh, udm_kwargs):
    async def _func(ou_name: str = None, host: str = None) -> str:
        ou_name = ou_name or f"testou{fake.pyint(1000, 9999)}"
        host = host or env_or_ucr("docker_host_name")
        print(f"Creating school {ou_name!r} on host {host!r} using SSH...")
        schedule_delete_ou_using_ssh(ou_name, host)
        short_ou_name = f"{ou_name}"[:10]
        returncode, stdout, stderr = exec_with_ssh(
            [
                "/usr/share/ucs-school-import/scripts/create_ou",
                ou_name,
                f"edu{short_ou_name}",
                f"adm{short_ou_name}",
                f"--sharefileserver=edu{short_ou_name}",
                f"--displayName='displ {ou_name}'",
                f"--alter-dhcpd-base=false",
            ]
        )
        assert (not stderr) or ("Already attached!" in stderr) or ("created successfully" in stderr)
        if "Already attached!" in stderr:
            print(f" => OU {ou_name!r} exists in {host!r}.")
        else:
            print(f" => OU {ou_name!r} created in {host!r}.")
        async with UDM(**udm_kwargs) as udm:
            try:
                await udm.get("container/ou").get(f"ou={ou_name},{ldap_base}")
            except UdmNoObject:
                raise AssertionError(f"Creation of OU {ou_name} failed.")
        return ou_name

    return _func


@pytest.fixture
def create_ou_using_python(ldap_base, schedule_delete_ou_using_ssh, udm_kwargs):
    async def _func(ou_name: str = None) -> str:
        ou_name = ou_name or f"testou{fake.pyint(1000, 9999)}"
        print(f"Creating school {ou_name!r} using Python...")
        host = env_or_ucr("docker_host_name")
        schedule_delete_ou_using_ssh(ou_name, host)
        short_ou_name = f"{ou_name}"[:10]
        async with UDM(**udm_kwargs) as udm:
            await create_ou(
                ou_name=ou_name,
                display_name=f"displ {ou_name}",
                edu_name=f"edu{short_ou_name}",
                admin_name=f"adm{short_ou_name}",
                share_name=f"edu{short_ou_name}",
                lo=udm,
                baseDN=env_or_ucr("ldap/base"),
                hostname=env_or_ucr("ldap/master"),
                is_single_master=ucr.is_true("ucsschool/singlemaster"),
                alter_dhcpd_base=False,
            )
            try:
                await udm.get("container/ou").get(f"ou={ou_name},{ldap_base}")
            except UdmNoObject:
                raise AssertionError(f"Creation of OU {ou_name} failed.")

        return ou_name

    return _func
