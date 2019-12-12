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
from ucsschool.lib.models.utils import get_file_handler
from .import_config import get_import_config

from . import __version__
from .constants import (
    LOG_FILE_PATH,
    STATIC_FILE_CHANGELOG,
    STATIC_FILE_README,
    STATIC_FILES_PATH,
    URL_API_PREFIX,
    URL_TOKEN_BASE,
)
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


@app.on_event("startup")
def configure_import():
    get_import_config()


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    return logging.getLogger(__name__)


@app.on_event("startup")
def setup_logging() -> None:
    for name in (
        None,
        "requests",
        "univention",
        "ucsschool",
        "uvicorn.access",
        "uvicorn.error",
    ):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
    file_handler = get_file_handler(logging.DEBUG, str(LOG_FILE_PATH))
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger = logging.getLogger("uvicorn.access")
    logger.addHandler(file_handler)


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
