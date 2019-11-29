from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import (
    BaseModel,
    Protocol,
    PydanticValueError,
    Field,
    HttpUrl,
    SecretStr,
    StrBytes,
    ValidationError,
    validator,
)
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from ucsschool.lib.models.attributes import SchoolClassName
from ucsschool.lib.models.base import NoObject
from ucsschool.lib.models.group import SchoolClass

from ..utils import get_lo_udm, get_logger, name_from_dn, url_to_dn, url_to_name

logger = get_logger(__name__)
router = APIRouter()


class SchoolClassModel(BaseModel):
    dn: str = None
    name: str
    school: HttpUrl
    description: str = None
    ucsschool_roles: List[str] = Schema(
        None, title="Roles of this object. Don't change if unsure."
    )
    url: HttpUrl = None
    users: List[HttpUrl] = None


    @classmethod
    def from_lib_model(cls, obj: SchoolClass, request: Request) -> "SchoolClassModel":
        kwargs = obj.to_dict()
        del kwargs["objectType"]
        kwargs["dn"] = kwargs.pop("$dn$")
        kwargs["school"] = request.url_for("get", school_name=obj.school)
        kwargs["url"] = request.url_for(
            "get", class_name=kwargs["name"], school=obj.school
        )
        kwargs["users"] = [
            request.url_for("get", username=name_from_dn(dn)) for dn in obj.users
        ]
        return cls(**kwargs)

    def as_lib_model(self, request: Request) -> SchoolClass:
        kwargs = self.dict()
        del kwargs["dn"]
        del kwargs["url"]
        # TODO: have an OU cache, to fix upper/lower/camel case of 'school'
        kwargs["school"] = url_to_name(request, "school", self.school)
        kwargs["name"] = f"{kwargs['school']}-{self.name}"
        kwargs["users"] = [
            url_to_dn(request, "user", user) for user in (self.users or [])
        ]  # this is expensive :/
        return SchoolClass(**kwargs)

    @validator("name")
    def check_name(cls, value):
        SchoolClassName("name").validate(value)
        return value


class SchoolClassPatchDocument(BaseModel):
    name: str = None
    description: str = None
    ucsschool_roles: List[str] = Schema(
        None, title="Roles of this object. Don't change if unsure."
    )
    users: List[UrlStr] = None

    def to_modify_kwargs(self, school, request: Request) -> Dict[str, Any]:
        res = {}
        if self.name:
            res["name"] = f"{school}-{self.name}"
        if self.description:
            res["description"] = self.description
        if self.ucsschool_roles:
            res["ucsschool_roles"] = self.ucsschool_roles
        if self.users:
            res["users"] = [
                url_to_dn(request, "user", user) for user in (self.users or [])
            ]  # this is expensive :/
        return res


@router.get("/")
async def search(
    request: Request,
    class_name: str = Query(
        None,
        title="List classes with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
    school_name: str = Query(
        ..., title="Name of school in which classes are (case sensitive)."
    ),
) -> List[SchoolClassModel]:
    """
	Search for school classes.

	- **name**: name of the school class, use '*' for inexact search (optional)
	- **school**: school the class belongs to, **case sensitive** (required)
	"""
    if class_name:
        filter_str = f"name={school_name}-{class_name}"
    else:
        filter_str = None
    scs = SchoolClass.get_all(get_lo_udm(), school_name, filter_str)
    return [SchoolClassModel.from_lib_model(sc, request) for sc in scs]


def get_lib_obj(class_name: str, school: str) -> SchoolClass:
    dn = SchoolClass(name=f"{school}-{class_name}", school=school).dn
    try:
        return SchoolClass.from_dn(dn, school, get_lo_udm())
    except NoObject:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No school class with name={class_name!r} and school={school!r} found.",
        )


@router.get("/{school}/{class_name}")
async def get(class_name: str, school: str, request: Request) -> SchoolClassModel:
    sc = get_lib_obj(class_name, school)
    return SchoolClassModel.from_lib_model(sc, request)


@router.post("/", status_code=HTTP_201_CREATED)
async def create(school_class: SchoolClassModel, request: Request) -> SchoolClassModel:
    """
	Create a school class with all the information:

	- **name**: name of the school class (required)
	- **school**: school the class belongs to (required)
	- **description**: additional text (optional)
	- **users**: list of URLs to User resources (optional)
	- **ucsschool_roles**: list of tags of the form $ROLE:$CONTEXT_TYPE:$CONTEXT (optional)
	"""
    sc = school_class.as_lib_model(request)
    if sc.exists(get_lo_udm()):
        raise HTTPException(
            status_code=HTTP_409_CONFLICT, detail="School class exists."
        )
    else:
        sc.create(get_lo_udm())
    return SchoolClassModel.from_lib_model(sc, request)


@router.patch("/{school}/{class_name}", status_code=HTTP_200_OK)
async def partial_update(
    class_name: str,
    school: str,
    school_class: SchoolClassPatchDocument,
    request: Request,
) -> SchoolClassModel:
    sc_current = get_lib_obj(class_name, school)
    changed = False
    for attr, new_value in school_class.to_modify_kwargs(school, request).items():
        current_value = getattr(sc_current, attr)
        if new_value != current_value:
            setattr(sc_current, attr, new_value)
            changed = True
    if changed:
        sc_current.modify(get_lo_udm())
    return SchoolClassModel.from_lib_model(sc_current, request)


@router.put("/{school}/{class_name}", status_code=HTTP_200_OK)
async def complete_update(
    class_name: str, school: str, school_class: SchoolClassModel, request: Request
) -> SchoolClassModel:
    sc_current = get_lib_obj(class_name, school)
    if school != url_to_name(request, "school", school_class.school):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Moving of class to other school is not allowed.",
        )
    changed = False
    sc_request = school_class.as_lib_model(request)
    for attr in SchoolClass._attributes.keys():
        current_value = getattr(sc_current, attr)
        new_value = getattr(sc_request, attr)
        if attr in ("ucsschool_roles", "users") and new_value is None:
            new_value = []
        if new_value != current_value:
            setattr(sc_current, attr, new_value)
            changed = True
    if changed:
        sc_current.modify(get_lo_udm())
    return SchoolClassModel.from_lib_model(sc_current, request)
