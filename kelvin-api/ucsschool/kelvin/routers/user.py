from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import Field, HttpUrl
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from ucsschool.lib.models.user import User  # Staff, Student, Teacher, TeachersAndStaff,
from udm_rest_client import UDM  # , NoObject as UdmNoObject

from ..ldap_access import udm_kwargs
from ..utils import get_logger
from .base import UcsSchoolBaseModel, get_lib_obj
from .role import SchoolUserRole

logger = get_logger(__name__)
router = APIRouter()


class UserModel(UcsSchoolBaseModel):
    dn: str = None
    name: str
    school: HttpUrl
    role: SchoolUserRole

    class Config(UcsSchoolBaseModel.Config):
        lib_class = User


@router.get("/")
async def search(
    request: Request,
    name_filter: str = Query(
        None,
        title="List users with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
    school_filter: str = Query(
        None, title="List only users in school with this name (not URL). ", min_length=3
    ),
) -> List[UserModel]:
    logger.debug(
        "Searching for users with: name_filter=%r school_filter=%r",
        name_filter,
        school_filter,
    )
    return [
        UserModel(name="10a", school="https://foo.bar/schools/gsmitte"),
        UserModel(name="8b", school="https://foo.bar/schools/gsmitte"),
    ]


@router.get("/{username}")
async def get(username: str) -> UserModel:
    return UserModel(name=username, school=f"https://foo.bar/schools/foo")


@router.post("/", status_code=HTTP_201_CREATED)
async def create(user: UserModel) -> UserModel:
    if user.name == "alsoerror":
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Invalid user name."
        )
    user.dn = "cn=foo-bar,cn=users,dc=test"
    return user


@router.patch("/{username}", status_code=HTTP_200_OK)
async def partial_update(username: str, user: UserModel) -> UserModel:
    if username != user.name:
        logger.info("Renaming user from %r to %r.", username, user.name)
    return user


@router.put("/{username}", status_code=HTTP_200_OK)
async def complete_update(username: str, user: UserModel) -> UserModel:
    if username != user.name:
        logger.info("Renaming user from %r to %r.", username, user.name)
    return user


@router.delete("/{username}", status_code=HTTP_204_NO_CONTENT)
async def delete(username: str, request: Request) -> None:
    async with UDM(**await udm_kwargs()) as udm:
        sc = await get_lib_obj(udm, User, username, None)
        if await sc.exists(udm):
            await sc.remove(udm)
        else:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="TODO")
    return None
