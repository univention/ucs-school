from enum import Enum
from typing import List
from urllib.parse import ParseResult, urlparse

from fastapi import APIRouter, Query
from pydantic import BaseModel, HttpUrl
from starlette.requests import Request

from ucsschool.importer.models.import_user import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
)
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_staff,
    role_student,
    role_teacher,
)

router = APIRouter()


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
