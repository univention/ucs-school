import os
from asyncio import TimeoutError

from molotov import get_var, global_setup, scenario, set_var

from ucsschool.veyon_client.client import VeyonClient
from ucsschool.veyon_client.models import AuthenticationMethod

_VEYON_KEY_FILE = "/etc/ucsschool-veyon/key.pem"
_API = "http://127.0.0.1:11080/api/v1"


@global_setup()
def init_test(args):
    WINDOWS_HOST = os.environ.get("UCS_ENV_WINDOWS_CLIENTS")
    assert WINDOWS_HOST, "No windows clients in env var UCS_ENV_WINDOWS_CLIENT!"
    host_exists = WINDOWS_HOST.split(" ")[0]
    host_not_exists = "192.168.4.2"  # TODO fix
    with open(_VEYON_KEY_FILE, "r") as fp:
        key_data = fp.read().strip()
        credentials = {"keyname": "teacher", "keydata": key_data}
    auth_headers = get_veyon_session(host_exists, credentials)
    set_var("credentials", credentials)
    set_var("host_not_exists", host_not_exists)
    set_var("host_exists", host_exists)
    set_var("auth_headers", auth_headers)


def get_veyon_session(host, credentials):
    vc = VeyonClient(
        _API,
        credentials=credentials,
        auth_method=AuthenticationMethod.AUTH_KEYS,
    )
    return vc._get_headers(host=host)


@scenario(weight=40)
async def authenticated_existing_session(session):
    """test existing session (using computerroom)"""
    uri = f"{_API}/user"
    try:
        res = await session.get(uri, timeout=20, headers=get_var("auth_headers"))
        assert res.status in (200, 429), f"response: {res} {res.status}"
    except TimeoutError:
        print("We have a timeout error")
        assert False


@scenario(weight=40)
async def authenticated_new_session(session):
    """test new session to WINDOWS_HOST (open computerroom)"""
    headers = get_veyon_session(get_var("host_exists"), get_var("credentials"))
    uri = f"{_API}/user"
    try:
        res = await session.get(uri, timeout=20, headers=headers)
        print(res.status)
        assert res.status == 200, f"response: {res} {res.status}"
    except TimeoutError:
        print("We have a timeout error")
        assert False


@scenario(weight=40)
async def unauthenticated_not_exists(session):
    """test connection if host is down"""
    host = get_var("host_not_exists")
    uri = f"{_API}/authentication/{host}"
    try:
        res = await session.get(uri, timeout=20)
        assert res.status in (408, 429), f"response: {res} {res.status}"
    except TimeoutError:
        print("We have a timeout error")
        assert False


@scenario(weight=40)
async def unauthenticated_exists(session):
    """test new connections"""
    host = get_var("host_exists")
    uri = f"{_API}/authentication/{host}"
    try:
        res = await session.get(uri, timeout=20)
        assert res.status in (200, 429), f"response: {res} {res.status}"
    except TimeoutError:
        print("We have a timeout error")
        assert False
