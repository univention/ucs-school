from enum import Enum
from typing import List, Type
from urllib.parse import ParseResult, urlparse

from fastapi import APIRouter, Query
from pydantic import BaseModel, HttpUrl
from starlette.requests import Request

from ucsschool.importer.factory import Factory
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_staff,
    role_student,
    role_teacher,
)

from ..import_config import init_ucs_school_import_framework

router = APIRouter()
_roles_to_class = {}


class SchoolUserRole(str, Enum):
    staff = "staff"
    student = "student"
    teacher = "teacher"

    @classmethod
    def from_lib_role(cls, lib_role: str) -> "SchoolUserRole":
        if role_student in lib_role:
            return cls.student
        if role_teacher in lib_role:
            return cls.teacher
        if role_staff in lib_role:
            return cls.staff
        else:  # Should never happen and throws exception
            return cls(lib_role)

    @classmethod
    def get_lib_class(cls, roles: List["SchoolUserRole"]) -> Type[ImportUser]:
        role_names = sorted(role.name for role in roles) if roles else []
        key = tuple(role_names)
        if key not in _roles_to_class:
            init_ucs_school_import_framework()
            factory = Factory()
            user: ImportUser = factory.make_import_user(role_names)
            _roles_to_class[key] = user.__class__
        return _roles_to_class[key]

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
            return create_ucsschool_role_string(role_student, school)
        elif self.value == self.teacher:
            return create_ucsschool_role_string(role_teacher, school)

    def to_url(self, request: Request) -> HttpUrl:
        url = request.url_for("get", role_name=self.value)
        up: ParseResult = urlparse(url)
        replaced = up._replace(scheme="https")
        return HttpUrl(replaced.geturl(), scheme="https", host=up.netloc)


class RoleModel(BaseModel):
    name: str
    display_name: str
    url: HttpUrl


@router.get("/", response_model=List[RoleModel])
async def search(request: Request,) -> List[RoleModel]:
    """
    List all available roles.
    """
    return [
        RoleModel(name=role.name, display_name=role.name, url=role.to_url(request))
        for role in (
            SchoolUserRole.staff,
            SchoolUserRole.student,
            SchoolUserRole.teacher,
        )
    ]


@router.get("/{role_name}", response_model=RoleModel)
async def get(
    request: Request,
    role_name: SchoolUserRole = Query(..., alias="name", title="name",),
) -> RoleModel:
    return RoleModel(
        name=role_name,
        display_name=role_name,
        url=SchoolUserRole(role_name).to_url(request),
    )
