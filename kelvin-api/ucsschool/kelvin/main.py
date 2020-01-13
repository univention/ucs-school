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

import logging
from datetime import timedelta
from functools import lru_cache

import aiofiles
import lazy_object_proxy
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette.requests import Request
from starlette.responses import HTMLResponse, UJSONResponse
from starlette.staticfiles import StaticFiles
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from ucsschool.lib.models.attributes import ValidationError as SchooLibValidationError
from ucsschool.lib.models.base import NoObject
from ucsschool.lib.models.utils import env_or_ucr, get_file_handler

from . import __version__
from .constants import (
    DEFAULT_LOG_LEVELS,
    LOG_FILE_PATH,
    STATIC_FILE_CHANGELOG,
    STATIC_FILE_README,
    STATIC_FILES_PATH,
    URL_API_PREFIX,
    URL_TOKEN_BASE,
)
from .import_config import get_import_config
from .ldap_access import LDAPAccess
from .routers import role, school, school_class, user
from .token_auth import (
    Token,
    create_access_token,
    get_current_active_user,
    get_token_ttl,
)

ldap_auth_instance: LDAPAccess = lazy_object_proxy.Proxy(LDAPAccess)


app = FastAPI(
    title="Kelvin API",
    description="UCS@school objects HTTP API",
    version=__version__,
    docs_url=f"{URL_API_PREFIX}/docs",
    redoc_url=f"{URL_API_PREFIX}/redoc",
    openapi_url=f"{URL_API_PREFIX}/openapi.json",
    default_response_class=UJSONResponse,
)


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    return logging.getLogger(__name__)


@app.on_event("startup")
def setup_logging() -> None:
    min_level = env_or_ucr("ucsschool/kelvin/log_level")
    if min_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        min_level = logging.ERROR
    min_level = logging._checkLevel(min_level)
    abs_min_level = min_level
    for name, default_level in DEFAULT_LOG_LEVELS.items():
        logger = logging.getLogger(name)
        logger.setLevel(min(default_level, min_level))
        abs_min_level = min(min_level, logger.level)

    file_handler = get_file_handler(abs_min_level, str(LOG_FILE_PATH))
    logger = logging.getLogger("uvicorn.access")
    logger.addHandler(file_handler)
    logger = logging.getLogger()
    logger.setLevel(abs_min_level)
    logger.addHandler(file_handler)


@app.on_event("startup")
def configure_import():
    get_import_config()


@app.exception_handler(NoObject)
async def no_object_exception_handler(request: Request, exc: NoObject):
    return UJSONResponse(status_code=HTTP_404_NOT_FOUND, content={"message": str(exc)})


@app.exception_handler(SchooLibValidationError)
async def school_lib_validation_exception_handler(
    request: Request, exc: SchooLibValidationError
):
    return UJSONResponse(
        status_code=HTTP_400_BAD_REQUEST, content={"message": str(exc)}
    )


@app.post(URL_TOKEN_BASE, response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    logger: logging.Logger = Depends(get_logger),
):
    user = await ldap_auth_instance.check_auth_and_get_user(
        form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=get_token_ttl())
    access_token = await create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    logger.debug("User %r retrieved access_token.", user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get(f"{URL_API_PREFIX}/changelog", response_class=HTMLResponse)
async def get_history():
    async with aiofiles.open(STATIC_FILE_CHANGELOG) as fp:
        return await fp.read()


@app.get(f"{URL_API_PREFIX}/readme", response_class=HTMLResponse)
async def get_readme():
    async with aiofiles.open(STATIC_FILE_README) as fp:
        return await fp.read()


app.include_router(
    school_class.router,
    prefix=f"{URL_API_PREFIX}/classes",
    tags=["classes"],
    dependencies=[Depends(get_current_active_user)],
)
# app.include_router(
#     computer_room.router,
#     prefix=f"{URL_API_PREFIX}/computer_rooms",
#     tags=["computer_rooms"],
#     dependencies=[Depends(get_current_active_user)],
# )
# app.include_router(
#     computer_client.router,
#     prefix=f"{URL_API_PREFIX}/computers",
#     tags=["computers"],
#     dependencies=[Depends(get_current_active_user)],
# )
app.include_router(
    role.router,
    prefix=f"{URL_API_PREFIX}/roles",
    tags=["roles"],
    dependencies=[Depends(get_current_active_user)],
)
app.include_router(
    school.router,
    prefix=f"{URL_API_PREFIX}/schools",
    tags=["schools"],
    dependencies=[Depends(get_current_active_user)],
)
# app.include_router(
#     computer_server.router,
#     prefix=f"{URL_API_PREFIX}/servers",
#     tags=["servers"],
#     dependencies=[Depends(get_current_active_user)],
# )
app.include_router(
    user.router,
    prefix=f"{URL_API_PREFIX}/users",
    tags=["users"],
    dependencies=[Depends(get_current_active_user)],
)
app.mount(
    f"{URL_API_PREFIX}/static",
    StaticFiles(directory=str(STATIC_FILES_PATH)),
    name="static",
)
