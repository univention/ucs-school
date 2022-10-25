import random
from collections import deque
from functools import lru_cache
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List

import requests
from diskcache import Index
from pydantic import BaseSettings, Field
from requests.exceptions import HTTPError

try:
    import univention.testing.ucr

    ucr = univention.testing.ucr.UCSTestConfigRegistry()
    ucr.load()
    HOSTNAME = ucr.get("hostname")
    DOMAIN_NAME = ucr.get("domainname")
    KEYCLOAK_DEFAULT_FQDN = f"ucs-sso-ng.{DOMAIN_NAME}"
    BFF_DEFAULT_HOST = f"{HOSTNAME}.{DOMAIN_NAME}"
except ImportError:
    KEYCLOAK_DEFAULT_FQDN = "ucs-sso-ng.ram.local"
    BFF_DEFAULT_HOST = "rankine.ram.local"

KELVIN_DEFAULT_HOST = BFF_DEFAULT_HOST

logger = getLogger(__name__)


class Settings(BaseSettings):
    KEYCLOAK_FQDN: str = Field(
        env="UCS_ENV_KEYCLOAK_BASE_URL",
        default=KEYCLOAK_DEFAULT_FQDN,
    )
    BFF_TEST_DATA_PATH: Path = Field(env="UCS_ENV_BFF_TEST_DATA_PATH", default="/var/lib/test-data")
    BFF_USERS_HOST: str = Field(env="UCS_ENV_BFF_USERS_HOST", default=BFF_DEFAULT_HOST)
    BFF_GROUPS_HOST: str = Field(env="UCS_ENV_BFF_GROUPS_HOST", default=BFF_DEFAULT_HOST)
    BFF_TEST_ADMIN_PASSWORD: str = Field(env="UCS_ENV_BFF_TEST_ADMIN_PASSWORD", default="univention")
    BFF_TEST_ADMIN_USERNAME: str = Field(env="UCS_ENV_BFF_TEST_ADMIN_USERNAME", default="Administrator")
    BFF_TEST_TOKEN_RENEW_PERIOD: int = Field(env="UCS_ENV_BFF_TEST_TOKEN_RENEW_PERIOD", default=60)
    KELVIN_HOST: str = Field(env="UCS_ENV_KELVIN_HOST", default=KELVIN_DEFAULT_HOST)

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"


class TestCleaner:
    def __init__(self):
        self.settings = get_settings()
        self._users_to_delete: deque = deque()

    def delete_later_user(self, username: str):
        self._users_to_delete.append(username)

    def delete(self):
        for username in self._users_to_delete:
            logger.info(f"Removing user {username} ...")
            response = requests.delete(
                f"http://{self.settings.BFF_USERS_HOST}/ucsschool/bff-users/v1/users/{username}"
            )
            if response.status_code != 204:
                logger.warning(
                    f"Deleting user {username} failed with"
                    f" {response.status_code} / {str(response.content)}"
                )
            else:
                logger.info(f"Removed user {username}")


class TestData(object):
    def __init__(self):
        self.settings = get_settings()
        self.db = Index(str(self.settings.BFF_TEST_DATA_PATH))

    @property
    def schools(self) -> List[str]:
        return self.db["schools"]

    def random_school(self) -> str:
        """Return a random school from the dataset"""
        return random.choice(self.schools)

    def school_staff(self, school: str) -> List[str]:
        """Return all staff ``username``s of ``school``"""
        return list(self.db[school]["staff"].keys())

    def school_user(self, school: str, username: str) -> Dict[str, Any]:
        """Return the detailed``username`` of a random user from ``school``"""
        return self.db[school]["users"][username]

    def random_user(self, school: str) -> str:
        """Return the ``username`` of a random user from ``school``"""
        return random.choice(list(self.db[school]["users"].keys()))

    def random_users(self, school: str, k: int = 10) -> List[str]:
        """Return ``k`` random ``username``s from ``school``"""
        return random.choices(list(self.db[school]["users"].keys()), k=k)

    def random_student(self, school: str) -> str:
        """Return the ``username`` of a random student from ``school``"""
        return random.choice(list(self.db[school]["students"].keys()))

    def random_students(self, school: str, k: int = 10) -> List[str]:
        """Return ``k`` random ``username``s from ``school`` which have the role student"""
        return random.choices(list(self.db[school]["students"].keys()), k=k)

    def random_workgroup(self, school: str) -> str:
        """Return a random workgroup from ``school``"""
        return random.choice(self.db[school]["workgroups"])

    def random_class(self, school: str) -> str:
        """Return a random class from ``school``"""
        return random.choice(self.db[school]["classes"])


def get_token_info(username: str, password: str, client_id: str = "school-ui-users-dev") -> Dict:
    settings = get_settings()
    url = f"https://{settings.KEYCLOAK_FQDN}/realms/ucs/protocol/openid-connect/token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "username": username,
        "password": password,
        "client_id": client_id,
        "grant_type": "password",
    }

    response = requests.post(url, data=data, verify=False, headers=headers)  # nosec
    if response.status_code != 200:
        raise HTTPError(f"{response.content!r}/{response.status_code}")
    return response.json()


@lru_cache(maxsize=1)
def get_settings():
    return Settings()
