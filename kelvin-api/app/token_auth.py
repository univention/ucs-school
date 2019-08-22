# -*- coding: utf-8 -*-

# Copyright 2019 Univention GmbH
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

from datetime import datetime, timedelta
import aiofiles
import jwt
from jwt import PyJWTError
import lazy_object_proxy
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED
from .constants import (
    TOKEN_HASH_ALGORITHM,
    TOKEN_SIGN_SECRET_FILE,
    URL_TOKEN_BASE,
    UCRV_TOKEN_TTL,
)
from .ldap_access import LDAPAccess, LdapUser
from .utils import get_logger
from ucsschool.lib.models.utils import ucr

logger = get_logger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=URL_TOKEN_BASE)
_secret_key = ""
ldap_auth_instance: LDAPAccess = lazy_object_proxy.Proxy(LDAPAccess)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = None


async def get_secret_key() -> str:
    global _secret_key

    if not _secret_key:
        async with aiofiles.open(TOKEN_SIGN_SECRET_FILE, "r") as fp:
            key = await fp.read()
        _secret_key = key.strip()
    return _secret_key


def get_token_ttl() -> int:
    return int(ucr.get(UCRV_TOKEN_TTL, 60))


async def create_access_token(*, data: dict, expires_delta: timedelta = None) -> bytes:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=get_token_ttl())
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, await get_secret_key(), algorithm=TOKEN_HASH_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> LdapUser:
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, await get_secret_key(), algorithms=[TOKEN_HASH_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except PyJWTError:
        raise credentials_exception
    user = await ldap_auth_instance.get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: LdapUser = Depends(get_current_user)
) -> LdapUser:
    if current_user.disabled:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return current_user
