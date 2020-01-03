import datetime
import json
import os
import random
import shutil
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import Any, Callable, Dict, List, Tuple
from unittest.mock import patch

import factory
import pytest
import requests
from faker import Faker

import ucsschool.kelvin.main
import ucsschool.lib.models.base
import ucsschool.lib.models.group
import ucsschool.lib.models.user
from ucsschool.kelvin.import_config import get_import_config
from ucsschool.kelvin.routers.user import UserCreateModel
from udm_rest_client import UDM, NoObject
from univention.config_registry import ConfigRegistry

APP_ID = "ucsschool-kelvin"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = APP_BASE_PATH / "conf"
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"
UCS_SSL_CA_CERT = "/usr/local/share/ca-certificates/ucs.crt"
IMPORT_CONFIG = {
    "active": Path("/var/lib/ucs-school-import/configs/user_import.json"),
    "bak": Path(
        "/var/lib/ucs-school-import/configs/user_import.json.bak.{}".format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        )
    ),
}
MAPPED_UDM_PROPERTIES = (
    "title",
    "description",
    "employeeType",
    "uidNumber",
    "gidNumber",
)  # keep in sync with test_route_user.py::MAPPED_UDM_PROPERTIES

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


class SchoolClassFactory(factory.Factory):
    class Meta:
        model = ucsschool.lib.models.group.SchoolClass

    name = factory.LazyFunction(lambda: f"DEMOSCHOOL-test.{fake.user_name()}")
    school = "DEMOSCHOOL"
    description = factory.Faker("text", max_nb_chars=50)
    users = factory.List([])


class UserFactory(factory.Factory):
    class Meta:
        model = ucsschool.lib.models.user.User

    name = factory.Faker("user_name")
    school = "DEMOSCHOOL"
    schools = factory.List(["DEMOSCHOOL"])
    firstname = factory.Faker("first_name")
    lastname = factory.Faker("last_name")
    birthday = factory.LazyFunction(
        lambda: fake.date_of_birth(minimum_age=6, maximum_age=65).strftime("%Y-%m-%d")
    )
    email = None
    description = factory.Faker("text", max_nb_chars=50)
    password = factory.Faker("password")
    disabled = False
    school_classes = factory.Dict({})


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


@pytest.fixture(scope="session")
def url_fragment():
    return f"http://{os.environ['DOCKER_HOST_NAME']}/kelvin/api/v1"


@pytest.fixture(scope="session")
def auth_header(url_fragment):
    response_json = requests.post(
        f"http://{os.environ['DOCKER_HOST_NAME']}/kelvin/api/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=dict(username="Administrator", password="univention"),
    ).json()
    auth_header = {"Authorization": f"Bearer {response_json['access_token']}"}
    return auth_header


@pytest.fixture
def setup_environ(monkeypatch):  # pragma: no cover
    """
    Monkey patch environment variables.
    Required for running unittests on outside Docker container (on developer
    machine).
    """
    if "DOCKER_HOST_NAME" not in os.environ:
        monkeypatch.setenv("DOCKER_HOST_NAME", "localhost")
    if "ldap_base" not in os.environ:
        monkeypatch.setenv("LDAP_BASE", "dc=foo,dc=bar")
    if "ldap_base" not in os.environ:
        monkeypatch.setenv("LDAP_HOSTDN", "localhost")
    if "ldap_base" not in os.environ:
        monkeypatch.setenv("LDAP_MASTER", "localhost")
    if "ldap_server_name" not in os.environ:
        monkeypatch.setenv("LDAP_SERVER_NAME", "localhost")
    if "ldap_server_port" not in os.environ:
        monkeypatch.setenv("LDAP_SERVER_PORT", "7389")


@pytest.fixture(scope="session")
def temp_dir_session():
    temp_dirs = []

    def _func(**mkdtemp_kwargs) -> Path:
        res = mkdtemp(**mkdtemp_kwargs)
        temp_dirs.append(res)
        return Path(res)

    yield _func

    for td in temp_dirs:
        shutil.rmtree(td)


@pytest.fixture
def temp_dir_func():
    temp_dirs = []

    def _func(**mkdtemp_kwargs) -> Path:
        res = mkdtemp(**mkdtemp_kwargs)
        temp_dirs.append(res)
        return Path(res)

    yield _func

    for td in temp_dirs:
        shutil.rmtree(td)


@pytest.fixture
def temp_file_func():
    temp_files: List[Path] = []

    def _func(**mkstemp_kwargs) -> Path:
        fd, res = mkstemp(**mkstemp_kwargs)
        os.close(fd)
        temp_files.append(Path(res))
        return Path(res)

    yield _func

    for tf in temp_files:
        try:
            tf.unlink()
        except FileNotFoundError:
            pass


# Monkey patch setup_logging() for the whole test session
@pytest.fixture(scope="session")
def setup_logging(temp_dir_session):
    tmp_log_file = Path(mkstemp()[1])

    with patch.object(ucsschool.kelvin.main, "LOG_FILE_PATH", tmp_log_file):
        print(f" -- logging to {tmp_log_file!s} --")
        yield

    try:
        tmp_log_file.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def random_name() -> Callable[[], str]:
    return fake.first_name


@pytest.fixture
def create_random_user_data(
    url_fragment,
):  # TODO: Extend with schools and school classes if resources are done
    def _create_random_user_data(**kwargs) -> UserCreateModel:
        f_name = fake.first_name()
        l_name = fake.last_name()
        name = f"test.{f_name}.{l_name}"
        domainname = env_or_ucr("domainname")
        data = dict(
            email=f"{name}mail@{domainname}".lower(),
            record_uid=name,
            source_uid="KELVIN",
            birthday=fake.date(),
            disabled=random.choice([True, False]),
            name=name,
            firstname=f_name,
            lastname=l_name,
            udm_properties={},
            school=f"{url_fragment}/schools/DEMOSCHOOL",
            schools=[f"{url_fragment}/schools/DEMOSCHOOL"],
            school_classes={"DEMOSCHOOL": ["DEMOSCHOOL-Democlass"]},
        )
        for key, value in kwargs.items():
            data[key] = value
        return UserCreateModel(**data)

    return _create_random_user_data


@pytest.fixture
def create_random_users(
    create_random_user_data, url_fragment, auth_header
):  # TODO: Extend with schools and school_classes if resources are done
    usernames = list()

    def _create_random_users(
        roles: Dict[str, int], **data_kwargs
    ) -> List[UserCreateModel]:
        users = []
        for role, amount in roles.items():
            for i in range(amount):
                if role == "teacher_and_staff":
                    roles_ulrs = [
                        f"{url_fragment}/roles/staff",
                        f"{url_fragment}/roles/teacher",
                    ]
                else:
                    roles_ulrs = [f"{url_fragment}/roles/{role}"]
                user_data = create_random_user_data(roles=roles_ulrs, **data_kwargs)
                response = requests.post(
                    f"{url_fragment}/users/",
                    headers={"Content-Type": "application/json", **auth_header},
                    data=user_data.json(),
                )
                assert response.status_code == 201, f"{response.__dict__}"
                users.append(user_data)
                usernames.append(user_data.name)
        return users

    yield _create_random_users

    for username in usernames:
        response = requests.delete(
            f"{url_fragment}/users/{username}", headers=auth_header
        )
        assert response.status_code in (204, 404)


@pytest.fixture
def new_school_class_obj():
    return lambda: SchoolClassFactory()


@pytest.fixture
async def new_school_class(udm_kwargs, ldap_base, new_school_class_obj):
    """Create a new school class"""
    created_school_classes = []

    async def _func(**kwargs) -> Tuple[str, Dict[str, Any]]:
        sc: ucsschool.lib.models.group.SchoolClass = new_school_class_obj()
        for k, v in kwargs.items():
            setattr(sc, k, v)

        async with UDM(**udm_kwargs) as udm:
            success = await sc.create(udm)
            assert success
            created_school_classes.append(sc.dn)
            print("Created new SchoolClass: {!r}".format(sc))

        return sc.dn, sc.to_dict()

    yield _func

    async with UDM(**udm_kwargs) as udm:
        for dn in created_school_classes:
            try:
                obj = await ucsschool.lib.models.group.SchoolClass.from_dn(
                    dn, None, udm
                )
            except ucsschool.lib.models.base.NoObject:
                print(f"SchoolClass {dn!r} does not exist (anymore).")
                continue
            await obj.remove(udm)
            print(f"Deleted SchoolClass {dn!r}.")


@pytest.fixture
async def create_random_schools(udm_kwargs):
    async def _create_random_schools(amount: int) -> List[Tuple[str, Any]]:
        if amount > 2:
            assert False, "At the moment only one or two schools can be requested."
        demo_school = (
            f"ou=DEMOSCHOOL,{env_or_ucr('ldap/base')}",
            dict(name="DEMOSCHOOL"),
        )
        demo_school_2 = (
            f"ou=DEMOSCHOOL2,{env_or_ucr('ldap/base')}",
            dict(name="DEMOSCHOOL2"),
        )
        if amount == 1:
            return [demo_school]
        async with UDM(**udm_kwargs) as udm:
            try:
                await udm.get("container/ou").get(demo_school_2[0])
            except NoObject:
                raise AssertionError(
                    "To run the tests properly you need to have a school named "
                    "DEMOSCHOOL2 at the moment! Execute *on the host*: "
                    "'/usr/share/ucs-school-import/scripts/create_ou DEMOSCHOOL2'"
                )
        return [demo_school, demo_school_2]

    return _create_random_schools


@pytest.fixture(scope="session")
def add_udm_properties_to_import_config():
    if IMPORT_CONFIG["active"].exists():
        print(f"Moving {IMPORT_CONFIG['active']!r} to {IMPORT_CONFIG['bak']!r}.")
        shutil.move(IMPORT_CONFIG["active"], IMPORT_CONFIG["bak"])
        config_file = IMPORT_CONFIG["bak"]
        with open(config_file, "r") as fp:
            config = json.load(fp)
    else:
        config = {"configuration_checks": ["defaults", "mapped_udm_properties"]}
    config["mapped_udm_properties"] = config.get("mapped_udm_properties", [])
    config["mapped_udm_properties"].extend(MAPPED_UDM_PROPERTIES)
    config["mapped_udm_properties"] = sorted(set(config["mapped_udm_properties"]))
    config["verbose"] = True
    with open(IMPORT_CONFIG["active"], "w") as fp:
        json.dump(config, fp, indent=4)
    print(f"Wrote config to {IMPORT_CONFIG['active']!r}: {config!r}")
    print("Restarting Kelvin API server...")
    subprocess.call(["/etc/init.d/kelvin-api", "restart"])
    time.sleep(3)

    yield

    if IMPORT_CONFIG["bak"].exists():
        print(f"Moving {IMPORT_CONFIG['bak']!r} to {IMPORT_CONFIG['active']!r}.")
        shutil.move(IMPORT_CONFIG["bak"], IMPORT_CONFIG["active"])
        print("Restarting Kelvin API server...")
        subprocess.call(["/etc/init.d/kelvin-api", "restart"])
        time.sleep(3)


@pytest.fixture(scope="session")
def import_config(add_udm_properties_to_import_config):
    # add_udm_properties_to_import_config() is already executed before collecting by setup.cfg
    config = get_import_config()
    assert set(MAPPED_UDM_PROPERTIES).issubset(
        set(config.get("mapped_udm_properties", []))
    )
    return config
