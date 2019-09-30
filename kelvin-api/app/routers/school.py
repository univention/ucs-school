import re
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
from ucsschool.lib.models.school import School
from ..utils import get_logger


logger = get_logger(__name__)
router = APIRouter()
_school_name_regex = re.compile('^[a-zA-Z0-9](([a-zA-Z0-9-]*)([a-zA-Z0-9]$))?$')


def validate_school_name(name):
    # TODO: this should use ucsschool.lib.models.attributes.SchoolName.validate()
    # but there is a useless conditional...
    if not _school_name_regex.match(name):
        raise ValueError(f"Invalid name for a school (OU): {name!r}")


class SchoolModel(BaseModel):
    dn: str = None
    name: str
    ucsschool_roles: List[str] = Schema(
        None, title="Roles of this object. Don't change if unsure."
    )


@router.get("/")
async def search(
    name_filer: str = Query(
        None,
        title="List schools with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
) -> List[SchoolModel]:
    logger.debug("Searching for schools with: name_filer=%r", name_filer)
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
