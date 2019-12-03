import os
import shutil
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import Callable, List
from unittest.mock import patch

import pytest
from faker import Faker

import ucsschool.kelvin.utils

faker = Faker()


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
