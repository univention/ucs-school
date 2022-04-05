# Copyright 2020-2021 Univention GmbH
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

import base64
import datetime
import inspect
import json
import logging
import os
import random
import shutil
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import Any, Callable, Dict, Iterable, List, Tuple
from unittest.mock import patch

import factory
import pytest
import requests
from faker import Faker

import ucsschool.kelvin.constants
import ucsschool.kelvin.ldap_access
import ucsschool.lib.models.base
import ucsschool.lib.models.group
import ucsschool.lib.models.user
from ucsschool.importer.configuration import Configuration, ReadOnlyDict
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.kelvin.import_config import get_import_config
from ucsschool.kelvin.routers.school import SchoolCreateModel
from ucsschool.kelvin.routers.user import PasswordsHashes, UserCreateModel
from ucsschool.kelvin.token_auth import create_access_token
from ucsschool.lib.models.user import User
from ucsschool.lib.models.utils import env_or_ucr
from udm_rest_client import UDM, UdmObject
from univention.config_registry import ConfigRegistry

# handle RuntimeError: Directory '/kelvin/kelvin-api/static' does not exist
with patch("ucsschool.kelvin.constants.STATIC_FILES_PATH", "/tmp"):
    import ucsschool.kelvin.main

APP_ID = "ucsschool-kelvin-rest-api"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = APP_BASE_PATH / "conf"
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"
IMPORT_CONFIG = {
    "active": Path("/var/lib/ucs-school-import/configs/user_import.json"),
    "bak": Path(
        "/var/lib/ucs-school-import/configs/user_import.json.bak.{}".format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        )
    ),
}
MAPPED_UDM_PROPERTIES_CONFIG = {
    "active": Path("/etc/ucsschool/kelvin/mapped_udm_properties.json"),
    "bak": Path(
        "/etc/ucsschool/kelvin/mapped_udm_properties.json.bak.{}".format(
            datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        )
    ),
}
MAPPED_UDM_PROPERTIES = [
    "title",
    "description",
    "displayName",
    "e-mail",
    "employeeType",
    "organisation",
    "phone",
    "uidNumber",
    "gidNumber",
]  # keep in sync with MAPPED_UDM_PROPERTIES in [ucsschool-repo(4.4|5.0)]/ucs-test-ucsschool/modules/...
# .../univention/testing/ucsschool/conftest.py and [ucs-repo(4.4|5.0)]/test/utils/...
# .../ucsschool_id_connector.py
# if changed: check tests/test_route_user.test_search_filter_udm_properties()

# import fixtures from ucsschool.lib tests
# this also imports a fixture "event_loop()" that stabilizes async teardowns
pytest_plugins = ["ucsschool.lib.tests.conftest"]

fake = Faker()
logger = logging.getLogger("ucsschool")
logger.setLevel(logging.DEBUG)
logger = logging.getLogger("udm_rest_client")
logger.setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@lru_cache(maxsize=1)
def ucr() -> ConfigRegistry:
    ucr = ConfigRegistry()
    ucr.load()
    return ucr


class SchoolCreateModelFactory(factory.Factory):
    class Meta:
        model = SchoolCreateModel

    name = factory.Faker("hostname", levels=0)
    display_name = factory.LazyAttribute(lambda o: f"displ name {o.name}")
    educational_servers = factory.LazyAttribute(lambda o: [f"edu{o.name[:10]}"])
    administrative_servers = factory.LazyAttribute(lambda o: [f"adm{o.name[:10]}"])
    class_share_file_server = factory.LazyAttribute(
        lambda o: f"{random.choice(('adm', 'edu'))}{o.name[:10]}"
    )
    home_share_file_server = factory.LazyAttribute(
        lambda o: f"{random.choice(('adm', 'edu'))}{o.name[:10]}"
    )


class SchoolClassFactory(factory.Factory):
    class Meta:
        model = ucsschool.lib.models.group.SchoolClass

    name = factory.LazyAttribute(lambda o: f"{o.school}-test.{fake.user_name()}")
    school = factory.LazyFunction(lambda: fake.user_name()[:10])
    description = factory.Faker("text", max_nb_chars=50)
    users = factory.List([])


@pytest.fixture(scope="session")
def udm_kwargs() -> Dict[str, Any]:
    with open(CN_ADMIN_PASSWORD_FILE, "r") as fp:
        cn_admin_password = fp.read().strip()
    host = env_or_ucr("ldap/server/name")
    return {
        "username": "cn=admin",
        "password": cn_admin_password,
        "url": f"https://{host}/univention/udm/",
    }


@pytest.fixture(scope="session")
def url_fragment():
    return f"http://{os.environ['DOCKER_HOST_NAME']}/ucsschool/kelvin/v1"


def get_access_token(username: str = "Administrator", password: str = "univention") -> str:
    response = requests.post(
        url=f"http://{os.environ['DOCKER_HOST_NAME']}/ucsschool/kelvin/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=dict(username=username, password=password),
    )
    assert response.status_code == 200, f"{response.__dict__!r}"
    response_json = response.json()
    return response_json["access_token"]


@pytest.fixture(scope="session")
def auth_header():
    token = get_access_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def generate_jwt():
    async def _generate_jwt(
        username: str, is_admin: bool, schools: Iterable[str], roles: Iterable[str]
    ) -> str:
        sub_data = dict(username=username, kelvin_admin=is_admin, schools=schools, roles=roles)
        return (await create_access_token(data=dict(sub=sub_data))).decode()

    return _generate_jwt


@pytest.fixture
def generate_auth_header(generate_jwt):
    async def _generate_auth_header(
        username: str,
        is_admin: bool = False,
        schools: Iterable[str] = (),
        roles: Iterable[str] = (),
    ):
        generated_token = await generate_jwt(username, is_admin, schools, roles)
        return {"Authorization": f"Bearer {generated_token}"}

    return _generate_auth_header


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
        logger.debug(" -- Kelvin logging redirected to %s --", tmp_log_file)
        yield

    try:
        tmp_log_file.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def random_name() -> Callable[[], str]:
    return fake.first_name


@pytest.fixture
def random_school_create_model() -> Callable[[], SchoolCreateModel]:
    return SchoolCreateModelFactory


@pytest.fixture
def random_user_create_model(
    url_fragment, new_school_class_using_lib, udm_users_user_props, mail_domain
):
    async def _create_random_user_data(ou_name: str, **kwargs) -> UserCreateModel:
        user_props = await udm_users_user_props(ou_name)
        try:
            school = kwargs.pop("school")
        except KeyError:
            school = f"{url_fragment}/schools/{ou_name}"
        try:
            schools = kwargs.pop("schools")
        except KeyError:
            schools = [school]
        try:
            school_classes = kwargs.pop("school_classes")
        except KeyError:
            if {url.split("/")[-1] for url in kwargs["roles"]} == {"staff"}:
                school_classes = {}
            else:
                sc_dn, sc_attr = await new_school_class_using_lib(ou_name)
                school_classes = {ou_name: [sc_attr["name"]]}
        data = dict(
            email=f"{user_props['username']}mail{fake.pyint()}@{mail_domain}".lower(),
            record_uid=user_props["username"],
            source_uid="Kelvin",
            birthday=fake.date_of_birth(minimum_age=6, maximum_age=18).strftime("%Y-%m-%d"),
            expiration_date=fake.date_between(start_date="+1y", end_date="+10y").strftime("%Y-%m-%d"),
            disabled=random.choice([True, False]),
            name=user_props["username"],
            firstname=user_props["firstname"],
            lastname=user_props["lastname"],
            udm_properties={},
            school=school,
            schools=schools,
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
    auth_header,
    retry_http_502,
    random_user_create_model,
    schedule_delete_user_name_using_udm,
    url_fragment,
):
    async def _create_random_users(
        ou_name: str, roles: Dict[str, int], **data_kwargs
    ) -> List[UserCreateModel]:
        users = []
        if "school" not in data_kwargs:
            data_kwargs["school"] = f"{url_fragment}/schools/{ou_name}"
        for role, amount in roles.items():
            for _ in range(amount):
                if role == "teacher_and_staff":
                    roles_ulrs = [
                        f"{url_fragment}/roles/staff",
                        f"{url_fragment}/roles/teacher",
                    ]
                else:
                    roles_ulrs = [f"{url_fragment}/roles/{role}"]
                user_data = await random_user_create_model(ou_name, roles=roles_ulrs, **data_kwargs)
                response = retry_http_502(
                    requests.post,
                    f"{url_fragment}/users/",
                    headers={"Content-Type": "application/json", **auth_header},
                    data=user_data.json(),
                )
                assert response.status_code == 201, f"{response.__dict__}"
                logger.debug(
                    "Created user %r (%r) with %r.", user_data.name, user_data.roles, user_data.dict()
                )
                users.append(user_data)
                schedule_delete_user_name_using_udm(user_data.name)
        return users

    return _create_random_users


@pytest.fixture
def create_exam_user(new_udm_user, ldap_base, random_name, udm_kwargs):
    async def _func(school: str, **school_user_kwargs) -> Tuple[str, Dict[str, Any]]:
        dn, user = await new_udm_user(school, "student", **school_user_kwargs)
        user["ucsschoolRole"] = [
            f"exam_user:school:{school}",
            f"exam_user:exam:{random_name()}-{school}",
        ]
        logger.debug("Modifying student %r to be an exam user...", user["username"])
        async with UDM(**udm_kwargs) as udm:
            udm_user: UdmObject = await udm.get("users/user").get(dn)
            udm_user.options["ucsschoolExam"] = True
            udm_user.position = f"cn=examusers,ou={school},{ldap_base}"
            udm_user.props.groups.append(
                f"cn=OU{school.lower()}-Klassenarbeit,cn=ucsschool,cn=groups,{ldap_base}"
            )
            udm_user.props.ucsschoolRole = user["ucsschoolRole"]
            await udm_user.save()
        logger.debug("Done: %r", dn)
        return dn, user

    return _func


@pytest.fixture
def new_import_user(new_school_user, udm_kwargs):
    """Create a new import user using UDM."""

    async def _func(
        school: str, role: str, udm_properties: Dict[str, Any] = None, **school_user_kwargs
    ) -> ImportUser:
        lib_user: User = await new_school_user(school, role, udm_properties, **school_user_kwargs)
        async with UDM(**udm_kwargs) as udm:
            user = await ImportUser.from_dn(lib_user.dn, school, udm)
            user.password = lib_user.password
            return user

    return _func


@pytest.fixture
def schedule_delete_user_name_using_kelvin(auth_header, retry_http_502, url_fragment):
    usernames = []

    def _func(username: str):
        usernames.append(username)

    yield _func

    for username in usernames:
        response = retry_http_502(
            requests.delete, f"{url_fragment}/users/{username}", headers=auth_header
        )
        assert response.status_code in (204, 404), response.reason
        if response.status_code == 204:
            logger.debug("Deleted user %r through Kelvin API.", username)
        else:
            logger.debug("User %r does not exist (anymore)", username)


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
def new_school_class_using_lib_obj():
    def _func(school: str, **kwargs) -> ucsschool.lib.models.group.SchoolClass:
        return SchoolClassFactory.build(school=school, **kwargs)

    return _func


@pytest.fixture
async def new_school_class_using_lib(ldap_base, new_school_class_using_lib_obj, udm_kwargs):
    """Create a new school class"""
    created_school_classes = []

    async def _func(school: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        sc: ucsschool.lib.models.group.SchoolClass = new_school_class_using_lib_obj(school, **kwargs)
        assert sc.name.startswith(f"{sc.school}-")

        async with UDM(**udm_kwargs) as udm:
            success = await sc.create(udm)
            assert success
            created_school_classes.append(sc.dn)
            logger.debug("Created new SchoolClass: %r", sc)

        return sc.dn, sc.to_dict()

    yield _func

    async with UDM(**udm_kwargs) as udm:
        for dn in created_school_classes:
            try:
                obj = await ucsschool.lib.models.group.SchoolClass.from_dn(dn, None, udm)
            except ucsschool.lib.models.base.NoObject:
                logger.debug("SchoolClass %r does not exist (anymore).", dn)
                continue
            await obj.remove(udm)
            logger.debug("Deleted SchoolClass %r through UDM.", dn)


def restart_kelvin_api_server() -> None:
    logger.debug("Restarting Kelvin API server...")
    subprocess.call(["/etc/init.d/ucsschool-kelvin-rest-api", "restart"])
    while True:
        time.sleep(0.5)
        try:
            get_access_token()
            break
        except AssertionError:
            # Kelvin API not ready -> 502 Proxy Error
            pass


@pytest.fixture(scope="module")
def restart_kelvin_api_server_module():
    return restart_kelvin_api_server


@pytest.fixture(scope="session")
def restart_kelvin_api_server_session():
    return restart_kelvin_api_server


@pytest.fixture(scope="session")
def mapped_udm_properties_test_config(restart_kelvin_api_server_session):
    def _func():
        if not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists():
            # not in Docker container
            return
        if MAPPED_UDM_PROPERTIES_CONFIG["active"].exists():
            shutil.move(MAPPED_UDM_PROPERTIES_CONFIG["active"], MAPPED_UDM_PROPERTIES_CONFIG["bak"])

        config = {"school": ["description"], "school_class": ["mailAddress"]}

        with open(MAPPED_UDM_PROPERTIES_CONFIG["active"], "w") as fd:
            json.dump(config, fd, indent=4)

        restart_kelvin_api_server_session()

    yield _func

    if MAPPED_UDM_PROPERTIES_CONFIG["bak"].exists():
        shutil.move(MAPPED_UDM_PROPERTIES_CONFIG["bak"], MAPPED_UDM_PROPERTIES_CONFIG["active"])


@pytest.fixture(scope="session")
def setup_mapped_udm_properties_config(mapped_udm_properties_test_config):
    mapped_udm_properties_test_config()


@pytest.fixture(scope="session")
def add_to_import_config(restart_kelvin_api_server_session):  # noqa: C901
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
                    old_value = set(config.get(k, []))
                    if new_value.issubset(old_value):
                        no_restart = True
                else:
                    new_value = v
                    old_value = config.get(k)
                    if old_value == new_value:
                        no_restart = True
            if no_restart:
                logger.debug("Import config contains %r -> not restarting server.", kwargs)
                return

        if IMPORT_CONFIG["active"].exists():
            with open(IMPORT_CONFIG["active"], "r") as fp:
                config = json.load(fp)
            if not IMPORT_CONFIG["bak"].exists():
                logger.debug("Moving %s to %s.", IMPORT_CONFIG["active"], IMPORT_CONFIG["bak"])
                shutil.move(IMPORT_CONFIG["active"], IMPORT_CONFIG["bak"])
            config.update(kwargs)
        else:
            config = kwargs
        with open(IMPORT_CONFIG["active"], "w") as fp:
            json.dump(config, fp, indent=4)
        logger.debug("Wrote config to %s: %r", IMPORT_CONFIG["active"], config)
        restart_kelvin_api_server_session()

    yield _func

    if IMPORT_CONFIG["bak"].exists():
        logger.debug("Moving %r to %r.", IMPORT_CONFIG["bak"], IMPORT_CONFIG["active"])
        shutil.move(IMPORT_CONFIG["bak"], IMPORT_CONFIG["active"])
        restart_kelvin_api_server_session()


@pytest.fixture(scope="session")
def setup_import_config(add_to_import_config) -> None:
    add_to_import_config(
        mapped_udm_properties=MAPPED_UDM_PROPERTIES,
        scheme={
            "record_uid": "<lastname>",
            "username": {"default": "<:lower>test.<firstname>[:2].<lastname>[:3]"},
        },
    )


@pytest.fixture(scope="session")
def import_config(setup_import_config) -> ReadOnlyDict:
    # setup_import_config() is already executed before collecting by setup.cfg
    config = get_import_config()
    assert set(MAPPED_UDM_PROPERTIES).issubset(set(config.get("mapped_udm_properties", [])))
    assert "username" in config.get("scheme", {})
    return config


@pytest.fixture
def reset_import_config():
    def _func() -> None:
        ucsschool.kelvin.import_config._ucs_school_import_framework_initialized = False
        ucsschool.kelvin.import_config._ucs_school_import_framework_error = None
        Configuration._instance = None

    return _func


@pytest.fixture
def check_password():
    async def _func(bind_dn: str, bind_pw: str) -> None:
        ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
        search_kwargs = {
            "filter_s": f"({bind_dn.split(',')[0]})",
            "attributes": ["uid"],
            "bind_dn": bind_dn,
            "bind_pw": bind_pw,
            "raise_on_bind_error": True,
        }
        logger.debug("Testing login (making LDAP search) with: %r", search_kwargs)
        results = await ldap_access.search(**search_kwargs)
        logger.debug("Login success.")
        assert len(results) == 1
        result = results[0]
        expected_uid = bind_dn.split(",")[0].split("=")[1]
        assert expected_uid == result["uid"].value

    return _func


@pytest.fixture
def password_hash(check_password, create_ou_using_python, new_udm_user):
    async def _func(password: str = None) -> Tuple[str, PasswordsHashes]:
        password = password or fake.password(length=20)
        ou = await create_ou_using_python()
        user_dn, user = await new_udm_user(
            ou, "student", disabled=False, password=password, school_classes={}
        )
        ldap_access = ucsschool.kelvin.ldap_access.LDAPAccess()
        await check_password(user_dn, password)
        # get hashes of user2
        filter_s = f"(uid={user['username']})"
        attributes = [
            "userPassword",
            "sambaNTPassword",
            "krb5Key",
            "krb5KeyVersionNumber",
            "sambaPwdLastSet",
        ]
        ldap_results = await ldap_access.search(filter_s=filter_s, attributes=attributes)
        if len(ldap_results) == 1:
            ldap_result = ldap_results[0]
        else:
            raise RuntimeError(
                f"More than 1 result when searching LDAP with filter {filter_s!r}: {ldap_results!r}."
            )
        user_password = ldap_result["userPassword"].value
        if not isinstance(user_password, list):
            user_password = [user_password]
        user_password = [pw.decode("ascii") for pw in user_password]
        krb_5_key = [base64.b64encode(v).decode("ascii") for v in ldap_result["krb5Key"].value]
        return password, PasswordsHashes(
            user_password=user_password,
            samba_nt_password=ldap_result["sambaNTPassword"].value,
            krb_5_key=krb_5_key,
            krb5_key_version_number=ldap_result["krb5KeyVersionNumber"].value,
            samba_pwd_last_set=ldap_result["sambaPwdLastSet"].value,
        )

    return _func


@pytest.fixture(scope="session")
def log_http_502():
    msgs = []
    log_file = "/tmp/http502.log"

    def _func(caller, func, args, kwargs):
        msg = (
            f"=> HTTP 502 in {caller}() by request.{func}({', '.join(repr(a) for a in args)}, "
            f"{', '.join(f'{k!r}={v!r}'for k, v in kwargs.items())})"
        )
        logger.debug(msg)
        msgs.append(msg)

    yield _func

    if not msgs:
        return
    logger.debug(" *** HTTP 502: %d times, see %r. ***", len(msgs), log_file)
    with open(log_file, "w") as fp:
        fp.write("\n".join(msgs))


@pytest.fixture
def retry_http_502(log_http_502):
    def _func(request_method: Callable[..., requests.Response], *args, **kwargs) -> requests.Response:
        retries = 5
        while retries > 0:
            response = request_method(*args, **kwargs)
            if response.status_code == 502:
                caller = inspect.stack()[1].function
                log_http_502(caller, request_method.__name__, args, kwargs)
                retries -= 1
                time.sleep(2)
                continue
            return response

    return _func
