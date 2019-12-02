import os
import shutil
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import Callable, List
from unittest.mock import patch

import pytest
from faker import Faker

import ucsschool.kelvin.constants
import ucsschool.kelvin.utils

faker = Faker()


@pytest.fixture
def setup_environ(monkeypatch):  # pragma: no cover
    """
    Monkey patch environment variables.
    Required for running unittests on outside Docker container (on developer
    machine).
    """
    if "docker_host_name" not in os.environ:
        monkeypatch.setenv("docker_host_name", "localhost")
    if "ldap_base" not in os.environ:
        monkeypatch.setenv("ldap_base", "dc=foo,dc=bar")
    if "ldap_server_name" not in os.environ:
        monkeypatch.setenv("ldap_server_name", "localhost")
    if "ldap_server_port" not in os.environ:
        monkeypatch.setenv("ldap_server_port", "7389")


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


# Monkey patch get_logger() for the whole test session
@pytest.fixture(scope="session")
def setup_logging(temp_dir_session):
    ori_get_logger = ucsschool.kelvin.utils.get_logger
    tmp_log_path = temp_dir_session()

    def utils_get_logger(
        name: str = None, path: Path = ucsschool.kelvin.constants.LOG_FILE_PATH
    ):
        path = tmp_log_path / path.name
        print(f"\n **** log directory is: {path} ****")
        return ori_get_logger(name, path)

    with patch(
        "ucsschool.kelvin.utils.get_logger", utils_get_logger,
    ):
        yield
    ucsschool.kelvin.utils.get_logger = ori_get_logger


@pytest.fixture
def random_name() -> Callable[[], str]:
    return faker.first_name
