from datetime import timedelta
from pathlib import Path

import aiofiles
import lazy_object_proxy
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette.requests import Request
from starlette.responses import HTMLResponse, UJSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from ucsschool.lib.models.base import NoObject
from ucsschool.lib.models.attributes import ValidationError as SchooLibValidationError

from .constants import (
    __version__,
    STATIC_FILE_CHANGELOG,
    STATIC_FILE_README,
    URL_TOKEN_BASE,
    URL_API_PREFIX,
)
from .ldap_access import LDAPAccess
from .routers import (
    computer_client,
    computer_room,
    computer_server,
    role,
    school,
    school_class,
    user,
)
from .token_auth import (
    create_access_token,
    get_current_active_user,
    get_token_ttl,
    Token,
)
from .utils import enable_ucsschool_lib_debugging, get_logger


enable_ucsschool_lib_debugging()
logger = get_logger(__name__)
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


@app.exception_handler(NoObject)
async def no_object_exception_handler(request: Request, exc: NoObject):
    return UJSONResponse(status_code=HTTP_404_NOT_FOUND, content={"message": str(exc)})


@app.exception_handler(SchooLibValidationError)
async def school_lib_validation_exception_handler(request: Request, exc: SchooLibValidationError):
    return UJSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"message": str(exc)})


@app.post(URL_TOKEN_BASE, response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
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
    # TODO: use starlette.staticfiles instead (https://fastapi.tiangolo.com/tutorial/static-files/)
    async with aiofiles.open(
        Path(__file__).parent.parent / STATIC_FILE_CHANGELOG
    ) as fp:
        return await fp.read()


@app.get(f"{URL_API_PREFIX}/readme", response_class=HTMLResponse)
async def get_readme():
    # TODO: use starlette.staticfiles instead (https://fastapi.tiangolo.com/tutorial/static-files/)
    async with aiofiles.open(Path(__file__).parent.parent / STATIC_FILE_README) as fp:
        return await fp.read()


app.include_router(
    school_class.router,
    prefix="/classes",
    tags=["classes"],
    dependencies=[Depends(get_current_active_user)],
)
app.include_router(
    computer_room.router,
    prefix="/computer_rooms",
    tags=["computer_rooms"],
    dependencies=[Depends(get_current_active_user)],
)
app.include_router(
    computer_client.router,
    prefix="/computers",
    tags=["computers"],
    dependencies=[Depends(get_current_active_user)],
)
app.include_router(
    role.router,
    prefix="/roles",
    tags=["roles"],
    dependencies=[Depends(get_current_active_user)],
)
app.include_router(
    school.router,
    prefix="/schools",
    tags=["schools"],
    dependencies=[Depends(get_current_active_user)],
)
app.include_router(
    computer_server.router,
    prefix="/servers",
    tags=["servers"],
    dependencies=[Depends(get_current_active_user)],
)
app.include_router(
    user.router,
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_active_user)],
)
