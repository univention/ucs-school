import os
import time

import pytest

from ucsschool.veyon_client.client import VeyonClient
from ucsschool.veyon_client.models import AuthenticationMethod, Feature

VEYON_KEY_FILE = "/etc/ucsschool-veyon/key.pem"
API = "http://localhost:11080/api/v1"


@pytest.fixture
def windows_client():
    windows_hosts = os.environ.get("UCS_ENV_WINDOWS_CLIENTS")
    assert windows_hosts, "No windows clients in env var UCS_ENV_WINDOWS_CLIENT!"
    return windows_hosts.split(" ")[0]


@pytest.fixture
def veyon_key_data():
    with open(VEYON_KEY_FILE) as fp:
        return fp.read().strip()


@pytest.fixture
def get_veyon_client(veyon_key_data):
    def _func(host):
        credentials = {"keyname": "teacher", "keydata": veyon_key_data}
        return VeyonClient(
            API,
            credentials=credentials,
            auth_method=AuthenticationMethod.AUTH_KEYS,
            default_host=host,
            idle_timeout=60,
        )

    return _func


@pytest.fixture
def wait_for_demo_mode():
    def _func(client, desired_status):
        feature = Feature.DEMO_SERVER
        for i in range(120):
            actual_status = client.get_feature_status(feature)
            print(
                f"Checking for feature {i} {feature.name} {actual_status} (should be {desired_status})"
            )
            if actual_status is desired_status:
                break
            time.sleep(1)
        else:
            raise Exception("Feature state did not change")

    return _func


@pytest.fixture
def set_demo_mode():
    def _func(client, status):
        feature = Feature.DEMO_SERVER
        client.set_feature(feature, active=status)

    return _func
