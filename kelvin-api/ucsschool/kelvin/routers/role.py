import logging
from enum import Enum
from functools import lru_cache
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_pupil,
    role_staff,
    role_teacher,
)
from udm_rest_client import UDM

from ..ldap_access import udm_kwargs
from .base import get_lib_obj

router = APIRouter()


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    return logging.getLogger(__name__)


class SchoolUserRole(str, Enum):
    staff = "staff"
    student = "student"
    teacher = "teacher"
    teachers_and_staff = "teachers_and_staff"

    @classmethod
    def from_lib_roles(cls, lib_roles: List[str]):
        role_concat = ','.join(lib_roles)
        if role_pupil in role_concat:
            return cls.student
        if role_staff in role_concat and role_teacher in role_concat:
            return cls.teachers_and_staff
        if role_teacher in role_concat:
            return cls.teacher
        if role_staff in role_concat:
            return cls.staff
        else:  # Should never happen and throws exception
            return cls(lib_roles[0])

    def as_lib_roles(self, school: str) -> List[str]:
        """
        Creates a list containing the role(s) in lib format.
        :param school: The school to create the role for.
        :return: The list containing the SchoolUserRole representation for
            consumation by the school lib.
        """
        if self.value == self.staff:
            return [create_ucsschool_role_string(role_staff, school)]
        elif self.value == self.student:
            return [create_ucsschool_role_string(role_pupil, school)]
        elif self.value == self.teacher:
            return [create_ucsschool_role_string(role_teacher, school)]
        elif self.value == self.teachers_and_staff:
            return [
                create_ucsschool_role_string(role_staff, school),
                create_ucsschool_role_string(role_teacher, school),
            ]


class RoleModel(BaseModel):
    name: SchoolUserRole


@router.get("/")
async def search(
    name_filter: str = Query(
        None,
        title="List roles with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
    logger: logging.Logger = Depends(get_logger),
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
