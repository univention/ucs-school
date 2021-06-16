from datetime import datetime, timedelta

import jwt
import pytest
import requests

import ucsschool.kelvin.constants
from ucsschool.kelvin.constants import TOKEN_HASH_ALGORITHM
from ucsschool.kelvin.token_auth import get_token_ttl

pytestmark = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)


async def create_fake_access_token(*, data: dict, expires_delta: timedelta = None) -> bytes:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=get_token_ttl())
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        "ndchuio34z789ufwhisnjöfop83htINVALIDSECRETKEYslkdjngiwoujrkbgs",
        algorithm=TOKEN_HASH_ALGORITHM,
    )
    return encoded_jwt


@pytest.mark.asyncio
async def test_get_fake_token(retry_http_502, url_fragment):
    sub_data = {"username": "Administrator", "kelvin_admin": True, "schools": [], "roles": []}
    token = await create_fake_access_token(data={"sub": sub_data})
    auth_header = {"Authorization": f"Bearer {token}"}
    response = retry_http_502(requests.get, f"{url_fragment}/users/ARBITRARY", headers=auth_header)
    assert response.status_code == 401, "The route should return an Access denied 401"
