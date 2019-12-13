import logging
from enum import Enum
from functools import lru_cache
from typing import List, Type

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from ucsschool.importer.models.import_user import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
)
from ucsschool.lib.models.base import UCSSchoolModel
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_pupil,
    role_staff,
    role_student,
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

    @classmethod
    def from_lib_role(cls, lib_role: str) -> "SchoolUserRole":
        if role_pupil in lib_role or role_student in lib_role:
            return cls.student
        if role_teacher in lib_role:
            return cls.teacher
        if role_staff in lib_role:
            return cls.staff
        else:  # Should never happen and throws exception
            return cls(lib_role)

    @classmethod
    def get_lib_class(cls, roles: List["SchoolUserRole"]):
        mapping = dict(staff=ImportStaff, student=ImportStudent, teacher=ImportTeacher)
        if cls.staff in roles and cls.teacher in roles:
            return ImportTeachersAndStaff
        elif len(roles) == 1:
            return mapping[roles[0].value]
        else:
            raise Exception(
                f"This should never happen! Tried to get LibClass for {roles}"
            )

    def as_lib_role(self, school: str) -> str:
        """
        Creates a list containing the role(s) in lib format.
        :param school: The school to create the role for.
        :return: The list containing the SchoolUserRole representation for
            consumation by the school lib.
        """
        if self.value == self.staff:
            return create_ucsschool_role_string(role_staff, school)
        elif self.value == self.student:
            return create_ucsschool_role_string(role_pupil, school)
        elif self.value == self.teacher:
            return create_ucsschool_role_string(role_teacher, school)

    def to_url(self, request: Request):
        return request.url_for("get", role_name=self.value)


class RoleModel(BaseModel):
    name: str
    display_name: str
    url: HttpUrl


@router.get("/")
async def search(
    request: Request,
    name_filter: str = Query(
        None,
        title="List roles with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
    logger: logging.Logger = Depends(get_logger),
) -> List[RoleModel]:
    logger.debug("Searching for roles with: name_filter=%r", name_filter)
    return [
        RoleModel(name=role.name, display_name=role.name, url=role.to_url(request))
        for role in (
            SchoolUserRole.staff,
            SchoolUserRole.teacher,
            SchoolUserRole.student,
        )
    ]


@router.get("/{role_name}")
async def get(request: Request, role_name: str) -> RoleModel:
    return RoleModel(
        name=role_name,
        display_name=role_name,
        url=SchoolUserRole(role_name).to_url(request),
    )


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
