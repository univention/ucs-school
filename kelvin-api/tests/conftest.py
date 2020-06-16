# Copyright 2020 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

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

import ucsschool.kelvin.constants
import ucsschool.lib.models.base
import ucsschool.lib.models.group
import ucsschool.lib.models.user
from ucsschool.importer.configuration import Configuration, ReadOnlyDict
from ucsschool.kelvin.import_config import get_import_config
from ucsschool.kelvin.routers.user import UserCreateModel
from udm_rest_client import UDM, NoObject
from univention.config_registry import ConfigRegistry

# handle RuntimeError: Directory '/kelvin/kelvin-api/static' does not exist
with patch("ucsschool.kelvin.constants.STATIC_FILES_PATH", "/tmp"):
    import ucsschool.kelvin.main

APP_ID = "ucsschool-kelvin-rest-api"
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
    "organisation",
    "phone",
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
    password = factory.Faker("password", length=20)
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
    return f"http://{os.environ['DOCKER_HOST_NAME']}/ucsschool/kelvin/v1"


@pytest.fixture(scope="session")
def auth_header(url_fragment):
    url = url_fragment.replace("v1", "token")
    response = requests.post(
        url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=dict(username="Administrator", password="univention"),
    )
    assert response.status_code == 200, f"{response.__dict__!r}"
    response_json = response.json()
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

    with patch("ucsschool.kelvin.main.LOG_FILE_PATH", tmp_log_file):
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
def create_random_user_data(url_fragment, new_school_class):
    async def _create_random_user_data(**kwargs) -> UserCreateModel:
        f_name = fake.first_name()
        l_name = fake.last_name()
        name = f"test.{f_name[:8]}{fake.pyint(10, 99)}.{l_name}"[:15].rstrip(".")
        domainname = env_or_ucr("domainname")
        if set(url.split("/")[-1] for url in kwargs["roles"]) == {"staff"}:
            school_classes = {}
        else:
            sc_dn, sc_attr = await new_school_class()
            school_classes = {"DEMOSCHOOL": ["DEMOSCHOOL-Democlass", sc_attr["name"]]}
        data = dict(
            email=f"{name}mail{fake.pyint()}@{domainname}".lower(),
            record_uid=name,
            source_uid="Kelvin",
            birthday=fake.date(),
            disabled=random.choice([True, False]),
            name=name,
            firstname=f_name,
            lastname=l_name,
            udm_properties={},
            school=f"{url_fragment}/schools/DEMOSCHOOL",
            schools=[f"{url_fragment}/schools/DEMOSCHOOL"],
            school_classes=school_classes,
            password=fake.password(length=20),
        )
        for key, value in kwargs.items():
            data[key] = value
        res = UserCreateModel(**data)
        res.password = res.password.get_secret_value()
        return res

    return _create_random_user_data


@pytest.fixture
def create_random_users(
    create_random_user_data, url_fragment, auth_header, schedule_delete_user
):  # TODO: Extend with schools and school_classes if resources are done
    async def _create_random_users(
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
                user_data = await create_random_user_data(
                    roles=roles_ulrs, **data_kwargs
                )
                response = requests.post(
                    f"{url_fragment}/users/",
                    headers={"Content-Type": "application/json", **auth_header},
                    data=user_data.json(),
                )
                assert response.status_code == 201, f"{response.__dict__}"
                print(
                    f"Created user {user_data.name!r} ({user_data.roles!r}) "
                    f"with {user_data.dict()!r}."
                )
                users.append(user_data)
                schedule_delete_user(user_data.name)
        return users

    return _create_random_users


@pytest.fixture
def schedule_delete_user(auth_header, url_fragment):
    usernames = []

    def _func(username: str):
        usernames.append(username)

    yield _func

    for username in usernames:
        response = requests.delete(
            f"{url_fragment}/users/{username}", headers=auth_header
        )
        assert response.status_code in (204, 404)


@pytest.fixture
def schedule_delete_file():
    paths: List[Path] = []

    def _func(path: Path):
        paths.append(path)

    yield _func

    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


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


def restart_kelvin_api_server() -> None:
    print("Restarting Kelvin API server...")
    subprocess.call(["/etc/init.d/ucsschool-kelvin-rest-api", "restart"])
    while True:
        time.sleep(0.5)
        response = requests.get(
            f"http://{os.environ['DOCKER_HOST_NAME']}/ucsschool/kelvin/api/foobar"
        )
        if response.status_code == 404:
            break
        # else: 502 Proxy Error


@pytest.fixture(scope="module")
def restart_kelvin_api_server_module():
    return restart_kelvin_api_server


@pytest.fixture(scope="session")
def restart_kelvin_api_server_session():
    return restart_kelvin_api_server


@pytest.fixture(scope="session")  # noqa: C901
def add_to_import_config(restart_kelvin_api_server_session):
    def _func(**kwargs) -> None:
        if not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists():
            # not in Docker container
            return
        if IMPORT_CONFIG["active"].exists():
            no_restart = False
            with open(IMPORT_CONFIG["active"], "r") as fp:
                config = json.load(fp)
            for k, v in kwargs.items():
                if isinstance(v, list):
                    new_value = set(v)
                    old_value = set(config.get(k))
                    if new_value.issubset(old_value):
                        no_restart = True
                else:
                    new_value = v
                    old_value = config.get(k)
                    if old_value == new_value:
                        no_restart = True
            if no_restart:
                print(f"Import config contains {kwargs!r} -> not restarting server.")
                return

        if IMPORT_CONFIG["active"].exists():
            with open(IMPORT_CONFIG["active"], "r") as fp:
                config = json.load(fp)
            if not IMPORT_CONFIG["bak"].exists():
                print(
                    f"Moving {IMPORT_CONFIG['active']!s} to {IMPORT_CONFIG['bak']!s}."
                )
                shutil.move(IMPORT_CONFIG["active"], IMPORT_CONFIG["bak"])
            config.update(kwargs)
        else:
            config = kwargs
        with open(IMPORT_CONFIG["active"], "w") as fp:
            json.dump(config, fp, indent=4)
        print(f"Wrote config to {IMPORT_CONFIG['active']!s}: {config!r}")
        restart_kelvin_api_server_session()

    yield _func

    if IMPORT_CONFIG["bak"].exists():
        print(f"Moving {IMPORT_CONFIG['bak']!r} to {IMPORT_CONFIG['active']!r}.")
        shutil.move(IMPORT_CONFIG["bak"], IMPORT_CONFIG["active"])
        restart_kelvin_api_server_session()


@pytest.fixture(scope="session")
def setup_import_config(add_to_import_config) -> None:
    add_to_import_config(
        mapped_udm_properties=MAPPED_UDM_PROPERTIES,
        scheme={
            "firstname": "<lastname>",
            "username": {"default": "<:lower>test.<firstname>[:2].<lastname>[:3]"},
        },
    )


@pytest.fixture(scope="session")
def import_config(setup_import_config) -> ReadOnlyDict:
    # setup_import_config() is already executed before collecting by setup.cfg
    config = get_import_config()
    assert set(MAPPED_UDM_PROPERTIES).issubset(
        set(config.get("mapped_udm_properties", []))
    )
    assert "username" in config.get("scheme", {})
    return config


@pytest.fixture
def reset_import_config():
    def _func() -> None:
        ucsschool.kelvin.import_config._ucs_school_import_framework_initialized = False
        ucsschool.kelvin.import_config._ucs_school_import_framework_error = None
        Configuration._instance = None

    return _func