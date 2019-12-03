import logging
from functools import lru_cache
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from ldap.filter import escape_filter_chars
from pydantic import HttpUrl
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from ucsschool.lib.models.user import User  # Staff, Student, Teacher, TeachersAndStaff,
from udm_rest_client import UDM  # , NoObject as UdmNoObject

from ..ldap_access import udm_kwargs
from ..urls import url_to_name
from .base import UcsSchoolBaseModel, get_lib_obj
from .role import SchoolUserRole

router = APIRouter()


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    return logging.getLogger(__name__)


class UserModel(UcsSchoolBaseModel):
    dn: str = None
    name: str
    firstname: str
    lastname: str
    school: HttpUrl
    role: SchoolUserRole

    class Config(UcsSchoolBaseModel.Config):
        lib_class = User

    @classmethod
    def _from_lib_model_kwargs(cls, obj: User, request: Request) -> Dict[str, Any]:
        kwargs = super()._from_lib_model_kwargs(obj, request)
        kwargs["role"] = SchoolUserRole.from_lib_roles(obj.roles)
        kwargs["url"] = cls.scheme_and_quote(
            request.url_for("get", username=kwargs["name"])
        )
        return kwargs

    async def _as_lib_model_kwargs(self, request: Request) -> Dict[str, Any]:
        kwargs = await super()._as_lib_model_kwargs(request)
        if not kwargs["ucsschool_roles"]:
            kwargs["ucsschool_roles"] = self.role.as_lib_roles(
                url_to_name(request, "school", self.school)
            )
        return kwargs


@router.get("/")
async def search(
    request: Request,
    name_filter: str = Query(
        None,
        title="List users with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
    school_filter: str = Query(
        ..., title="List only users in school with this name (not URL). ", min_length=3
    ),
    logger: logging.Logger = Depends(get_logger),
) -> List[UserModel]:
    """
    Search for school users.

    - **name**: name of the school user, use '*' for inexact search (optional)
    - **school**: school the user belongs to, **case sensitive** (required)
    """
    logger.debug(
        "Searching for users with: name_filter=%r school_filter=%r",
        name_filter,
        school_filter,
    )
    if name_filter:
        filter_str = f"username={name_filter}"
    else:
        filter_str = None
    async with UDM(**await udm_kwargs()) as udm:
        users = await User.get_all(udm, school_filter, filter_str)
        return [UserModel.from_lib_model(user, request) for user in users]


@router.get("/{username}")
async def get(username: str, request: Request) -> UserModel:
    async with UDM(**await udm_kwargs()) as udm:
        async for udm_obj in udm.get("users/user").search(
            f"uid={escape_filter_chars(username)}"
        ):
            break
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"No User with username {username!r} found.",
            )
        user = await get_lib_obj(udm, User, dn=udm_obj.dn)
    return UserModel.from_lib_model(user, request)


@router.post("/", status_code=HTTP_201_CREATED)
async def create(user: UserModel, request: Request) -> UserModel:
    """
    Create a school user with all the information:

    - **name**: name of the school user (required)
    - **firstname**: name of the school user (required)
    - **lastname**: name of the school user (required)
    - **school**: school the class belongs to (required)
    - **role**: One of either student, staff, teacher, teachers_and_staff
    """
    user = await user.as_lib_model(request)
    async with UDM(**await udm_kwargs()) as udm:
        if await user.exists(udm):
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail="School user exists."
            )
        else:
            await user.create(udm)
    return UserModel.from_lib_model(user, request)


@router.patch("/{username}", status_code=HTTP_200_OK)
async def partial_update(
    username: str,
    user: UserModel,
    request: Request,
    logger: logging.Logger = Depends(get_logger),
) -> UserModel:
    if username != user.name:
        logger.info("Renaming user from %r to %r.", username, user.name)
    return user


@router.put("/{username}", status_code=HTTP_200_OK)
async def complete_update(
    username: str,
    user: UserModel,
    request: Request,
    logger: logging.Logger = Depends(get_logger),
) -> UserModel:
    if username != user.name:
        logger.info("Renaming user from %r to %r.", username, user.name)
    return user


@router.delete("/{username}", status_code=HTTP_204_NO_CONTENT)
async def delete(username: str, request: Request) -> None:
    async with UDM(**await udm_kwargs()) as udm:
        async for udm_obj in udm.get("users/user").search(
            f"uid={escape_filter_chars(username)}"
        ):
            break
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"No User with username {username!r} found.",
            )
        user = await get_lib_obj(udm, User, dn=udm_obj.dn)
        await user.remove(udm)
    return None
