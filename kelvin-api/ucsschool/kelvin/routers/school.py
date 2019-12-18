import logging

# import re
from functools import lru_cache
from typing import List

import ujson
from fastapi import APIRouter, Depends, HTTPException, Query
from ldap.filter import escape_filter_chars
from pydantic import BaseModel
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from ucsschool.lib.models.school import School
from udm_rest_client import UDM

from .base import udm_ctx

router = APIRouter()
# _school_name_regex = re.compile("^[a-zA-Z0-9](([a-zA-Z0-9-]*)([a-zA-Z0-9]$))?$")


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    return logging.getLogger(__name__)


# def validate_school_name(name):
#     # TODO: this should use ucsschool.lib.models.attributes.SchoolName.validate()
#     # but there is a useless conditional...
#     if not _school_name_regex.match(name):
#         raise ValueError(f"Invalid name for a school (OU): {name!r}")


class SchoolModel(BaseModel):
    dn: str = None
    name: str
    display_name: str = None
    dc_name: str = None
    dc_name_administrative: str = None
    class_share_file_server: str = None
    home_share_file_server: str = None
    educational_servers: List[str] = []
    administrative_servers: List[str] = []
    ucsschool_roles: List[str] = []

    class Config:
        json_loads = ujson.loads


@router.get("/", response_model=List[SchoolModel])
async def search(
    name_filter: str = Query(
        None,
        alias="name",
        description="List schools with this name. '*' can be used for an inexact search.",
        title="name",
    ),
    logger: logging.Logger = Depends(get_logger),
    udm: UDM = Depends(udm_ctx),
) -> List[SchoolModel]:
    logger.debug("Searching for schools with: name_filter=%r", name_filter)
    if name_filter:
        filter_str = "ou={}".format(
            escape_filter_chars(name_filter).replace(r"\2a", "*")
        )
    else:
        filter_str = None
    logger.debug("*** filter_str=%r", filter_str)
    schools = [
        school.to_dict() for school in await School.get_all(udm, filter_str=filter_str)
    ]
    for school in schools:
        school["dn"] = school.pop("$dn$")
    return [SchoolModel(**school) for school in schools]


@router.get("/{school_name}", response_model=SchoolModel)
async def get(
    school_name: str = Query(
        None, alias="name", description="School (OU) with this name.", title="name",
    ),
    udm: UDM = Depends(udm_ctx),
) -> SchoolModel:
    school_udm = await School(name=school_name).get_udm_object(udm)
    if not school_udm:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="School not found.")
    school = await School.from_udm_obj(school_udm, school_name, udm)
    school_dict = school.to_dict()
    school_dict["dn"] = school_dict.pop("$dn$")
    return SchoolModel(**school_dict)


@router.post("/", status_code=HTTP_201_CREATED, response_model=SchoolModel)
async def create(school: SchoolModel) -> SchoolModel:
    raise NotImplementedError
