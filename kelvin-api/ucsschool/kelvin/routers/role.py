from enum import Enum
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

# from ucsschool.lib.roles import all_roles, create_ucsschool_role_string
from udm_rest_client import UDM

from ..ldap_access import udm_kwargs
from ..utils import get_logger
from .base import get_lib_obj

logger = get_logger(__name__)
router = APIRouter()


class SchoolUserRole(str, Enum):
    staff = "staff"
    student = "student"
    teacher = "teacher"


class RoleModel(BaseModel):
    name: SchoolUserRole


@router.get("/")
async def search(
    name_filter: str = Query(
        None,
        title="List roles with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
) -> List[RoleModel]:
    logger.debug("Searching for roles with: name_filter=%r", name_filter)
    return [RoleModel(name="10a"), RoleModel(name="8b")]


@router.get("/{name}")
async def get(name: str) -> RoleModel:
    return RoleModel(name=name)


@router.post("/", status_code=HTTP_201_CREATED)
async def create(role: RoleModel) -> RoleModel:
    if role.name == "alsoerror":
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Invalid role name."
        )
    return role


@router.patch("/{name}", status_code=HTTP_200_OK)
async def partial_update(name: str, role: RoleModel) -> RoleModel:
    if name != role.name:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Renaming roles is not supported."
        )
    return role


@router.put("/{name}", status_code=HTTP_200_OK)
async def complete_update(name: str, role: RoleModel) -> RoleModel:
    if name != role.name:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Renaming roles is not supported."
        )
    return role


@router.delete("/{name}", status_code=HTTP_204_NO_CONTENT)
async def delete(name: str, request: Request) -> None:
    async with UDM(**await udm_kwargs()) as udm:
        sc = await get_lib_obj(udm, SchoolUserRole, name, None)
        if await sc.exists(udm):
            await sc.remove(udm)
        else:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="TODO")
    return None
