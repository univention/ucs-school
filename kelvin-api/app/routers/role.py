from typing import List
from pydantic import (
    BaseModel,
    Protocol,
    PydanticValueError,
    Schema,
    SecretStr,
    StrBytes,
    UrlStr,
    validator,
    ValidationError,
)
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)
from fastapi import APIRouter, HTTPException, Query
from starlette.responses import UJSONResponse
from ucsschool.lib.roles import all_roles, create_ucsschool_role_string
from ..utils import get_logger


logger = get_logger(__name__)
router = APIRouter()


class RoleModel(BaseModel):
    name: str


@router.get("/", response_class=UJSONResponse)
async def search(
    name_filer: str = Query(
        None,
        title="List roles with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
) -> List[RoleModel]:
    logger.debug("Searching for roles with: name_filer=%r", name_filer)
    return [RoleModel(name="10a"), RoleModel(name="8b")]


@router.get("/{name}", response_class=UJSONResponse)
async def get(name: str) -> RoleModel:
    return RoleModel(name=name)


@router.post("/", response_class=UJSONResponse, status_code=HTTP_201_CREATED)
async def create(role: RoleModel) -> RoleModel:
    if role.name == "alsoerror":
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Invalid role name."
        )
    return role


@router.patch("/{name}", response_class=UJSONResponse, status_code=HTTP_200_OK)
async def partial_update(name: str, role: RoleModel) -> RoleModel:
    if name != role.name:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Renaming roles is not supported."
        )
    return role


@router.put("/{name}", response_class=UJSONResponse, status_code=HTTP_200_OK)
async def complete_update(name: str, role: RoleModel) -> RoleModel:
    if name != role.name:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Renaming roles is not supported."
        )
    return role
