from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    Protocol,
    PydanticValueError,
    SecretStr,
    StrBytes,
    ValidationError,
    validator,
)
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from ucsschool.lib.roles import all_roles, create_ucsschool_role_string

from ..utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


class RoleModel(BaseModel):
    name: str


@router.get("/")
async def search(
    name_filer: str = Query(
        None,
        title="List roles with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
) -> List[RoleModel]:
    logger.debug("Searching for roles with: name_filer=%r", name_filer)
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
