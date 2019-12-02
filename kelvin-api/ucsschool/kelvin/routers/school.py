import re
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from ucsschool.lib.models.school import School
from udm_rest_client import UDM

from ..ldap_access import udm_kwargs
from ..utils import get_logger
from .base import UcsSchoolBaseModel, get_lib_obj

logger = get_logger(__name__)
router = APIRouter()
_school_name_regex = re.compile("^[a-zA-Z0-9](([a-zA-Z0-9-]*)([a-zA-Z0-9]$))?$")


def validate_school_name(name):
    # TODO: this should use ucsschool.lib.models.attributes.SchoolName.validate()
    # but there is a useless conditional...
    if not _school_name_regex.match(name):
        raise ValueError(f"Invalid name for a school (OU): {name!r}")


class SchoolModel(UcsSchoolBaseModel):
    dn: str = None
    name: str
    ucsschool_roles: List[str] = Field(
        None, title="Roles of this object. Don't change if unsure."
    )

    class Config(UcsSchoolBaseModel.Config):
        lib_class = School


@router.get("/")
async def search(
    name_filter: str = Query(
        None,
        title="List schools with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
) -> List[SchoolModel]:
    logger.debug("Searching for schools with: name_filter=%r", name_filter)
    return [SchoolModel(name="10a"), SchoolModel(name="8b")]


@router.get("/{school_name}")
async def get(school_name: str) -> SchoolModel:
    return SchoolModel(name=school_name)


@router.post("/", status_code=HTTP_201_CREATED)
async def create(school: SchoolModel) -> SchoolModel:
    if school.name == "alsoerror":
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Invalid school name."
        )
    school.dn = f"ou={school.name},dc=test"
    return school


@router.patch("/{name}", status_code=HTTP_200_OK)
async def partial_update(name: str, school: SchoolModel) -> SchoolModel:
    if name != school.name:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Renaming schools is not supported.",
        )
    return school


@router.put("/{name}", status_code=HTTP_200_OK)
async def complete_update(name: str, school: SchoolModel) -> SchoolModel:
    if name != school.name:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Renaming schools is not supported.",
        )
    return school


@router.delete("/{name}", status_code=HTTP_204_NO_CONTENT)
async def delete(name: str, request: Request) -> None:
    async with UDM(**await udm_kwargs()) as udm:
        sc = await get_lib_obj(udm, School, name, None)
        if await sc.exists(udm):
            await sc.remove(udm)
        else:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="TODO")
    return None
