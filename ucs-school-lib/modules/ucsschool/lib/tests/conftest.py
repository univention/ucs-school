import asyncio
import logging
import random
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import factory
import pytest
from faker import Faker

import ucsschool.lib.models.user
from ucsschool.lib.create_ou import create_ou
from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import User
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

_cached_ous: Set[Tuple[str, str]] = set()
fake = Faker()
logger = logging.getLogger("ucsschool")
logger.setLevel(logging.DEBUG)


@pytest.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_host_name():
    return env_or_ucr("docker_host_name")


@pytest.fixture(scope="session")
def ldap_base():
    return env_or_ucr("ldap/base")


@pytest.fixture
def random_ou_name():
    def _func() -> str:
        return f"testou{fake.pyint(1000, 9999)}"

    return _func


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
    async def _func(school: str, **kwargs) -> Dict[str, str]:
        return {
            "name": kwargs.get("name", f"test.{fake.user_name()}"),
            "school": school,
            "description": kwargs.get("description", fake.text(max_nb_chars=50)),
            "users": kwargs.get(
                "users",
                [
                    f"uid={fake.user_name()},cn=users,{ldap_base}",
                    f"uid={fake.user_name()},cn=users,{ldap_base}",
                ],
            ),
            "ucsschool_roles": kwargs.get(
                "ucsschool_roles", [create_ucsschool_role_string(role_school_class, school)]
            ),
        }

    return _func


class UserFactory(factory.Factory):
    class Meta:
        model = ucsschool.lib.models.user.User

    firstname = factory.Faker("first_name")
    lastname = factory.Faker("last_name")
    name = factory.LazyAttribute(
        lambda o: f"test.{o.firstname[:8]}{fake.pyint(10, 99)}.{o.lastname}"[:15].rstrip(".")
    )
    school = factory.LazyFunction(lambda: fake.user_name()[:10])
    schools = factory.LazyAttribute(lambda o: [o.school])
    birthday = factory.LazyFunction(
        lambda: fake.date_of_birth(minimum_age=6, maximum_age=65).strftime("%Y-%m-%d")
    )
    email = None
    password = factory.Faker("password", length=20)
    disabled = False
    school_classes = factory.Dict({})


@pytest.fixture(scope="session")
async def mail_domain(udm_kwargs) -> str:
    async with UDM(**udm_kwargs) as udm:
        mod = udm.get("mail/domain")
        async for obj in mod.search():
            created_domain = ""
            name = obj.props.name
            print(f"Using existing mail/domain {name!r}.")
            break
        else:
            name = env_or_ucr("domainname") or fake.domain_name()
            print(f"Creating mail/domain object {name!r}...")
            obj = await mod.new()
            obj.props.name = name
            await obj.save()
            created_domain = name

    yield name

    if created_domain:
        print(f"Deleting mail/domain object {created_domain!r}...")
        async with UDM(**udm_kwargs) as udm:
            mod = udm.get("mail/domain")
            async for obj in mod.search(f"(cn={created_domain})"):
                await obj.delete()


@pytest.fixture
def school_user(mail_domain):
    async def _func(school: str, **kwargs) -> ucsschool.lib.models.user.User:
        if "email" not in kwargs:
            local_part = fake.ascii_company_email().split("@", 1)[0]
            kwargs["email"] = f"{local_part}@{mail_domain}"
        if "schools" not in kwargs:
            kwargs["schools"] = [school]
        return UserFactory.build(school=school, **kwargs)

    return _func


@pytest.fixture
def udm_users_user_props(school_user):
    async def _func(school: str, **school_user_kwargs) -> Dict[str, Any]:
        user = await school_user(school, **school_user_kwargs)
        return {
            "firstname": user.firstname,
            "lastname": user.lastname,
            "username": user.name,
            "school": user.schools,
            "birthday": user.birthday,
            "mailPrimaryAddress": user.email,
            "e-mail": [user.email],
            "description": fake.text(max_nb_chars=50),
            "password": user.password,
            "disabled": user.disabled,
        }

    return _func


@pytest.fixture
async def new_school_class_using_udm(udm_kwargs, ldap_base, school_class_attrs):
    """Create a new school class"""
    created_school_classes = []
    created_school_shares = []

    async def _func(school: str, **kwargs) -> Tuple[str, Dict[str, str]]:
        async with UDM(**udm_kwargs) as udm:
            sc_attrs = await school_class_attrs(school, **kwargs)
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
            share_obj.position = f"cn=klassen,cn=shares,ou={school},{ldap_base}"
            share_obj.props.name = grp_obj.props.name
            share_obj.props.host = f"{school}.{env_or_ucr('domainname')}"
            share_obj.props.owner = 0
            share_obj.props.group = 0
            share_obj.props.path = f"/home/tmp/{grp_obj.props.name}"
            share_obj.props.directorymode = "0770"
            share_obj.props.ucsschoolRole = [
                create_ucsschool_role_string(role_school_class_share, school),
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
def new_udm_user(
    udm_kwargs, ldap_base, udm_users_user_props, new_school_class_using_udm, schedule_delete_user_dn
):
    """Create a new UDM school user using UDM."""

    async def _func(
        school: str, role: str, udm_properties: Dict[str, Any] = None, **school_user_kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        assert role in ("staff", "student", "teacher", "teacher_and_staff")
        udm_properties = udm_properties or {}
        user_props = await udm_users_user_props(school, **school_user_kwargs)
        if role == "teacher_and_staff":
            user_props["ucsschoolRole"] = [
                create_ucsschool_role_string(role_staff, school),
                create_ucsschool_role_string(role_teacher, school),
            ]
        else:
            user_props["ucsschoolRole"] = [create_ucsschool_role_string(role, school)]
        school_search_base = SchoolSearchBase([school])
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
        user_props.update(udm_properties)
        async with UDM(**udm_kwargs) as udm:
            user_obj = await udm.get("users/user").new()
            user_obj.options.update(dict((opt, True) for opt in options))
            user_obj.position = position
            user_obj.props.update(user_props)
            user_obj.props.primaryGroup = f"cn=Domain Users {school},cn=groups,ou={school},{ldap_base}"
            user_obj.props.ucsschoolRecordUID = school_user_kwargs.get(
                "record_uid", user_props["username"]
            )
            user_obj.props.ucsschoolSourceUID = school_user_kwargs.get("source_uid", "Kelvin")
            user_obj.props.groups.append(user_obj.props.primaryGroup)
            if role != "staff" and "school_classes" not in school_user_kwargs:
                cls_dn1, _ = await new_school_class_using_udm(school=school)
                cls_dn2, _ = await new_school_class_using_udm(school=school)
                user_obj.props.groups.extend([cls_dn1, cls_dn2])
            await user_obj.save()
            schedule_delete_user_dn(user_obj.dn)
            print(f"Created new {role[0].upper()}{role[1:]}: {user_obj!r}")

        return user_obj.dn, user_props

    yield _func


@pytest.fixture
def new_school_user(new_udm_user, udm_kwargs):
    """Create a new school user using UDM."""

    async def _func(
        school: str, role: str, udm_properties: Dict[str, Any] = None, **school_user_kwargs
    ) -> User:
        dn, user_attrs = await new_udm_user(school, role, udm_properties, **school_user_kwargs)
        async with UDM(**udm_kwargs) as udm:
            user = await User.from_dn(dn, school, udm)
            user.password = user_attrs["password"]
            return user

    return _func


@pytest.fixture
def new_users(new_udm_user):
    """Create multiple new UDM school users using UDM."""

    async def _func(
        school: str, roles: Dict[str, int], **school_user_kwargs
    ) -> List[Tuple[str, Dict[str, Any]]]:
        return [
            await new_udm_user(school, role, **school_user_kwargs)
            for role, amount in roles.items()
            for _ in range(amount)
        ]

    return _func


@pytest.fixture
def new_school_users(new_school_user):
    """Create multiple new school users using UDM."""

    async def _func(school: str, roles: Dict[str, int], **school_user_kwargs) -> List[User]:
        return [
            await new_school_user(school, role, **school_user_kwargs)
            for role, amount in roles.items()
            for _ in range(amount)
        ]

    return _func


@pytest.fixture
async def schedule_delete_udm_obj(udm_kwargs):
    objs: List[Tuple[str, str]] = []

    def _func(dn: str, udm_mod: str):
        objs.append((dn, udm_mod))

    yield _func

    async with UDM(**udm_kwargs) as udm:
        for dn, udm_mod_name in objs:
            mod = udm.get(udm_mod_name)
            try:
                udm_obj = await mod.get(dn)
            except UdmNoObject:
                print(f"UDM {udm_mod_name!r} object {dn!r} does not exist (anymore).")
                continue
            await udm_obj.delete()
            print(f"Deleted UDM {udm_mod_name!r} object {dn!r} through UDM.")


@pytest.fixture
async def schedule_delete_user_dn(schedule_delete_udm_obj):
    def _func(dn: str):
        schedule_delete_udm_obj(dn, "users/user")

    yield _func


@pytest.fixture
async def schedule_delete_user_name_using_udm(udm_kwargs):
    usernames = []

    def _func(username: str):
        usernames.append(username)

    yield _func

    async with UDM(**udm_kwargs) as udm:
        user_mod = udm.get("users/user")
        for username in usernames:
            async for user_obj in user_mod.search(f"uid={username}"):
                await user_obj.delete()
                break
            else:
                print(f"User {username!r} does not exist (anymore).")
                continue
            print(f"Deleted user {username!r} through UDM.")


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
        print(f"stdout={stdout} or '<empty>'")
        print(f"stderr={stderr or '<empty>'}")
    else:
        print("'ssh' and 'sshpass' are already installed.")


@pytest.fixture(scope="session")
def exec_with_ssh(docker_host_name, installed_ssh):
    def _func(cmd: List[str], host: str = None) -> Tuple[int, str, str]:
        host = host or docker_host_name
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
        print(f"stdout={stdout or '<empty>'}")
        print(f"stderr={stderr or '<empty>'}")
        return returncode, stdout, stderr

    return _func


@pytest.fixture(scope="session")
def delete_ou_using_ssh(exec_with_ssh, ldap_base):
    async def _func(ou_name: str, host: str):
        print(f"Deleting OU {ou_name!r} on host {host!r}...")
        dn = f"ou={ou_name},{ldap_base}"
        retries = 2
        while retries > 0:
            _, stdout, _ = exec_with_ssh(["/usr/sbin/udm", "container/ou", "remove", "--dn", dn], host)
            if "Operation not allowed on non-leaf" in stdout:
                retries -= 1
            else:
                break

    return _func


@pytest.fixture(scope="session")
def delete_ou_cleanup(ldap_base, udm_kwargs):
    async def _func(ou_name: str):
        group_dns = [
            f"cn=admins-{ou_name.lower()},cn=ouadmins,cn=groups,{ldap_base}",
            f"cn=OU{ou_name}-Klassenarbeit,cn=ucsschool,cn=groups,{ldap_base}",
            f"cn=OU{ou_name.lower()}-DC-Edukativnetz,cn=ucsschool,cn=groups,{ldap_base}",
            f"cn=OU{ou_name.lower()}-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{ldap_base}",
            f"cn=OU{ou_name.lower()}-Member-Edukativnetz,cn=ucsschool,cn=groups,{ldap_base}",
            f"cn=OU{ou_name.lower()}-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{ldap_base}",
        ]
        async with UDM(**udm_kwargs) as udm:
            mod = udm.get("groups/group")
            for dn in group_dns:
                print(f"Deleting group: {dn!r}...")
                try:
                    obj = await mod.get(dn)
                    await obj.delete()
                except UdmNoObject:
                    print(f"Error: group does not exist: {dn!r}")
        if ucr.is_true("ucsschool/singlemaster"):
            master_hostname = env_or_ucr("ldap/master").split(".", 1)[0]
            async with UDM(**udm_kwargs) as udm:
                mod = udm.get("computers/domaincontroller_master")
                async for obj in mod.search(f"cn={master_hostname}"):
                    print(f"Removing 'ucsschoolRole=single_master:school:{ou_name}' from {obj.dn!r}...")
                    try:
                        obj.props.ucsschoolRole.remove(f"single_master:school:{ou_name}")
                        await obj.save()
                    except ValueError:
                        print(f"Error: role was no set: ucsschoolRole={obj.props.ucsschoolRole!r}")

    return _func


@pytest.fixture
async def schedule_delete_ou_using_ssh(delete_ou_using_ssh, delete_ou_cleanup):
    ous_created: List[Tuple[str, str]] = []

    def _func(ou_name: str, host: str):
        ous_created.append((ou_name, host))

    yield _func

    for ou_name, host in ous_created:
        await delete_ou_using_ssh(ou_name, host)
        await delete_ou_cleanup(ou_name)


@pytest.fixture(scope="session")
async def schedule_delete_ou_using_ssh_at_end_of_session(delete_ou_using_ssh, delete_ou_cleanup):
    def _func(ou_name: str, host: str):
        _cached_ous.add((ou_name, host))

    yield _func

    for ou_name, host in _cached_ous:
        await delete_ou_using_ssh(ou_name, host)
        await delete_ou_cleanup(ou_name)


def create_ou_kwargs(ou_name: str = None) -> Dict[str, Any]:
    ou_name = ou_name or f"testou{fake.pyint(1000, 9999)}"
    assert ou_name not in {ou[0] for ou in _cached_ous}
    short_ou_name = f"{ou_name}"[:10]
    is_single_master = ucr.is_true("ucsschool/singlemaster")
    master_hostname = env_or_ucr("ldap/master").split(".", 1)[0]
    edu_name = master_hostname if is_single_master else f"edu{short_ou_name}"
    admin_name = f"adm{short_ou_name}"
    hostname = master_hostname if is_single_master else None
    return {
        "ou_name": ou_name,
        "display_name": f"display name of {ou_name}",
        "edu_name": edu_name,
        "admin_name": admin_name,
        "share_name": edu_name,
        "baseDN": ldap_base,
        "hostname": hostname,
        "is_single_master": is_single_master,
        "alter_dhcpd_base": False,
    }


def get_ou_from_cache(ou_name: str, cache: bool) -> str:
    if ou_name in {c[0] for c in _cached_ous}:
        if not cache:
            raise ValueError(f"Requested fresh OU, but ou {ou_name!r} is in cache.")
        return ou_name
    if not ou_name and cache and len(_cached_ous) > 2:
        # Only return OUs from cache, when we have at least 3 OUs in it. This is to get a bit of
        # randomization / isolation in the tests.
        return random.choice(tuple(_cached_ous))[0]  # nosec
    return ""


@pytest.fixture
def create_ou_using_ssh(
    docker_host_name,
    exec_with_ssh,
    ldap_base,
    delete_ou_using_ssh,
    schedule_delete_ou_using_ssh,
    schedule_delete_ou_using_ssh_at_end_of_session,
    udm_kwargs,
):
    async def _func(ou_name: str = None, host: str = None, cache: bool = True) -> str:
        if cached_ou := get_ou_from_cache(ou_name, cache):
            print(f"Using OU {ou_name!r} from cache.")
            return cached_ou
        args = create_ou_kwargs(ou_name)
        ou_name = args["ou_name"]
        host = host or docker_host_name
        print(f"Creating school {ou_name!r} on host {host!r} using SSH...")
        if cache:
            schedule_delete_ou_using_ssh_at_end_of_session(ou_name, host)
        else:
            schedule_delete_ou_using_ssh(ou_name, host)
        returncode, stdout, stderr = exec_with_ssh(
            [
                "/usr/share/ucs-school-import/scripts/create_ou",
                ou_name,
                args["edu_name"],
                args["admin_name"],
                f"--sharefileserver={args['share_name']}",
                f"--displayName=\"{args['display_name']}\"",
                f"--alter-dhcpd-base={str(args['alter_dhcpd_base']).lower()}",
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
def create_ou_using_python(
    docker_host_name,
    ldap_base,
    delete_ou_using_ssh,
    schedule_delete_ou_using_ssh,
    schedule_delete_ou_using_ssh_at_end_of_session,
    udm_kwargs,
):
    async def _func(ou_name: str = None, cache: bool = True) -> str:
        if cached_ou := get_ou_from_cache(ou_name, cache):
            print(f"Using cached school {cached_ou!r}.")
            return cached_ou
        args = create_ou_kwargs(ou_name)
        ou_name = args["ou_name"]
        print(f"Creating school {ou_name!r} using Python...")
        if cache:
            schedule_delete_ou_using_ssh_at_end_of_session(ou_name, docker_host_name)
        else:
            schedule_delete_ou_using_ssh(ou_name, docker_host_name)
        async with UDM(**udm_kwargs) as udm:
            if await School(ou_name).exists(udm):
                print(f"School {ou_name!r} exists.")
                return ou_name
        is_single_master = ucr.is_true("ucsschool/singlemaster")
        master_hostname = env_or_ucr("ldap/master").split(".", 1)[0]
        hostname = master_hostname if is_single_master else None
        create_ou_python_kwargs = {
            "ou_name": ou_name,
            "display_name": args["display_name"],
            "edu_name": args["edu_name"],
            "admin_name": args["admin_name"],
            "share_name": args["share_name"],
            "baseDN": ldap_base,
            "hostname": hostname,
            "is_single_master": is_single_master,
            "alter_dhcpd_base": False,
        }
        print(f"=> kwargs for create_ou: {create_ou_python_kwargs!r}")
        async with UDM(**udm_kwargs) as udm:
            await create_ou(lo=udm, **create_ou_python_kwargs)
            try:
                await udm.get("container/ou").get(f"ou={ou_name},{ldap_base}")
            except UdmNoObject:
                raise AssertionError(f"Creation of OU {ou_name} failed.")
        print(f"School {ou_name!r} created.")
        return ou_name

    return _func


@pytest.fixture
def create_multiple_ous(
    create_ou_using_python, random_ou_name, schedule_delete_ou_using_ssh_at_end_of_session
):
    async def _func(amount: int, cache: bool = True) -> List[str]:
        if not cache:
            return [await create_ou_using_python(cache=cache) for _ in range(amount)]
        while len(_cached_ous) < amount:
            await create_ou_using_python(ou_name=random_ou_name())
        res = [c[0] for c in _cached_ous]
        random.shuffle(res)
        return res[:amount]

    return _func
