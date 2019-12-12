import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
from faker import Faker

import ucsschool.lib.models.user
from ucsschool.lib.roles import create_ucsschool_role_string
from ucsschool.lib.schoolldap import SchoolSearchBase
from udm_rest_client import UDM, NoObject as UdmNoObject
from univention.config_registry import ConfigRegistry

APP_ID = "ucsschool-kelvin"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = APP_BASE_PATH / "conf"
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"
UCS_SSL_CA_CERT = "/usr/local/share/ca-certificates/ucs.crt"

fake = Faker()


@lru_cache(maxsize=1)
def ucr() -> ConfigRegistry:
    ucr = ConfigRegistry()
    ucr.load()
    return ucr


@lru_cache(maxsize=32)
def env_or_ucr(key: str) -> str:
    try:
        return os.environ[key.replace("/", "_").upper()]
    except KeyError:
        return ucr()[key]


@pytest.fixture(scope="session")
def ldap_base():
    return env_or_ucr("ldap/base")


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
    def _func() -> Dict[str, str]:
        return {
            "name": f"test.{fake.user_name()}",
            "school": "DEMOSCHOOL",
            "description": fake.text(max_nb_chars=50),
            "users": [
                f"uid={fake.user_name()},cn=users,{ldap_base}",
                f"uid={fake.user_name()},cn=users,{ldap_base}",
            ],
        }

    return _func


@pytest.fixture
def users_user_props(ldap_base):
    def _func() -> Dict[str, str]:
        fn = fake.first_name()
        ln = fake.last_name()
        return {
            "firstname": fn,
            "lastname": ln,
            "username": f"test.{fn}.{ln}".lower(),
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

    async def _func() -> Tuple[str, Dict[str, str]]:
        async with UDM(**udm_kwargs) as udm:
            sc_attrs = school_class_attrs()
            grp_obj = await udm.get("groups/group").new()
            grp_obj.position = (
                f"cn=klassen,cn=schueler,cn=groups,ou={sc_attrs['school']},{ldap_base}"
            )
            grp_obj.props.name = f"{sc_attrs['school']}-{sc_attrs['name']}"
            grp_obj.props.description = sc_attrs["description"]
            grp_obj.props.users = sc_attrs["users"]
            await grp_obj.save()
            created_school_classes.append(grp_obj.dn)
            print("Created new SchoolClass: {!r}".format(grp_obj))

            share_obj = await udm.get("shares/share").new()
            share_obj.position = (
                f"cn=klassen,cn=shares,ou={sc_attrs['school']},{ldap_base}"
            )
            share_obj.props.name = grp_obj.props.name
            share_obj.props.host = f"{sc_attrs['school']}.{env_or_ucr('domainname')}"
            share_obj.props.owner = 0
            share_obj.props.group = 0
            share_obj.props.path = f"/home/tmp/{grp_obj.props.name}"
            share_obj.props.directorymode = "0770"
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
            print(f"Deleted SchoolClass {dn!r}.")
        share_mod = udm.get("shares/share")
        for dn in created_school_shares:
            try:
                share_obj = await share_mod.get(dn)
            except UdmNoObject:
                print(f"ClassShare {dn!r} does not exist (anymore).")
                continue
            await share_obj.delete()
            print(f"Deleted ClassShare {dn!r}.")


@pytest.fixture
async def new_user(udm_kwargs, ldap_base, users_user_props, new_school_class):
    """Create a new user"""
    created_users = []

    async def _func(role) -> Tuple[str, Dict[str, str]]:
        assert role in ("staff", "student", "teacher", "teacher_and_staff")
        user_props = users_user_props()
        if role == "teacher_and_staff":
            user_props["ucsschoolRole"] = [
                create_ucsschool_role_string("teacher", user_props["school"][0]),
                create_ucsschool_role_string("teacher", user_props["school"][0]),
            ]
        else:
            user_props["ucsschoolRole"] = [
                create_ucsschool_role_string(role, user_props["school"][0])
            ]
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
            user_obj.options.extend(options)
            user_obj.position = position
            user_obj.props.update(user_props)
            if role != "staff":
                cls_dn1, _ = await new_school_class()
                cls_dn2, _ = await new_school_class()
                user_obj.props.groups.extend([cls_dn1, cls_dn2])
            await user_obj.save()
            created_users.append(user_obj.dn)
            print(f"Created new {role!r}: {user_obj!r}")

        return user_obj.dn, user_props

    yield _func

    async with UDM(**udm_kwargs) as udm:
        user_mod = udm.get("users/user")
        for dn in created_users:
            try:
                user_obj = await user_mod.get(dn)
            except UdmNoObject:
                print(f"User {dn!r} does not exist (anymore).")
                continue
            await user_obj.delete()
            print(f"Deleted user {dn!r}.")


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
