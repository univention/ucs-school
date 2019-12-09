import os
import shutil
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import Callable, List, Dict
from unittest.mock import patch
import requests

import pytest
from faker import Faker

import ucsschool.kelvin.utils
from ucsschool.kelvin.routers.user import UserCreateModel

faker = Faker()


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

    with patch.object(ucsschool.kelvin.utils, "LOG_FILE_PATH", tmp_log_file):
        print(f" -- logging to {tmp_log_file!s} --")
        yield

    try:
        tmp_log_file.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def random_name() -> Callable[[], str]:
    return faker.first_name


@pytest.fixture
def create_random_user_data(
    url_fragment,
):  # TODO: Extend with schools and school classes if ressources are done
    def _create_random_user_data(role: str):
        f_name = faker.first_name()
        l_name = faker.last_name()
        name = f"{f_name}-{l_name}"
        data = dict(
            email="",
            record_uid=name,
            source_uid="KELVIN",
            birthday=faker.date(),
            disabled=False,
            name=name,
            firstname=f_name,
            lastname=l_name,
            udm_properties={},
            school=f"{url_fragment}/schools/DEMOSCHOOL",
            schools=[f"{url_fragment}/schools/DEMOSCHOOL"],
            school_classes={"DEMOSCHOOL": ["DEMOSCHOOL-Democlass"]},
            role=f"{url_fragment}/roles/{role}",
        )
        return UserCreateModel(**data)

    return _create_random_user_data


@pytest.fixture
def create_random_users(
    create_random_user_data, url_fragment, auth_header
):  # TODO: Extend with schools and school_classes if resources are done
    usernames = list()

    def _create_random_users(roles: Dict[str, int]):
        users = []
        for role, amount in roles.items():
            for i in range(amount):
                user_data = create_random_user_data(role)
                response = requests.post(
                    f"{url_fragment}/users/",
                    headers={"Content-Type": "application/json", **auth_header},
                    data=user_data.json(),
                )
                assert response.status_code == 201
                users.append(user_data)
                usernames.append(user_data.name)
        return users

    yield _create_random_users

    for username in usernames:
        response = requests.delete(
            f"{url_fragment}/users/{username}", headers=auth_header
        )
        assert response.status_code == 204
