from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from ucsschool.lib.models.group import SchoolClass
from udm_rest_client import UDM, APICommunicationError

from ..ldap_access import udm_kwargs
from ..urls import name_from_dn, url_to_dn, url_to_name
from .base import APIAttributesMixin, UcsSchoolBaseModel, get_lib_obj

router = APIRouter()


class SchoolClassCreateModel(UcsSchoolBaseModel):
    description: str = None
    users: List[HttpUrl] = None

    class Config(UcsSchoolBaseModel.Config):
        lib_class = SchoolClass

    @classmethod
    async def _from_lib_model_kwargs(
        cls, obj: SchoolClass, request: Request, udm: UDM
    ) -> Dict[str, Any]:
        kwargs = await super()._from_lib_model_kwargs(obj, request, udm)
        kwargs["url"] = cls.scheme_and_quote(
            request.url_for("get", class_name=kwargs["name"], school=obj.school)
        )
        kwargs["users"] = [
            cls.scheme_and_quote(request.url_for("get", username=name_from_dn(dn)))
            for dn in obj.users
        ]
        return kwargs

    async def _as_lib_model_kwargs(self, request: Request) -> Dict[str, Any]:
        kwargs = await super()._as_lib_model_kwargs(request)
        school_name = url_to_name(
            request, "school", self.unscheme_and_unquote(kwargs["school"])
        )
        kwargs["name"] = f"{school_name}-{self.name}"
        kwargs["users"] = [
            await url_to_dn(request, "user", self.unscheme_and_unquote(user))
            for user in (self.users or [])
        ]  # this is expensive :/
        return kwargs


class SchoolClassModel(SchoolClassCreateModel, APIAttributesMixin):
    pass


class SchoolClassPatchDocument(BaseModel):
    name: str = None
    description: str = None
    ucsschool_roles: List[str] = Field(
        None, title="Roles of this object. Don't change if unsure."
    )
    users: List[HttpUrl] = None

    async def to_modify_kwargs(self, school, request: Request) -> Dict[str, Any]:
        res = {}
        if self.name:
            res["name"] = f"{school}-{self.name}"
        if self.description:
            res["description"] = self.description
        if self.ucsschool_roles:
            res["ucsschool_roles"] = self.ucsschool_roles
        if self.users:
            res["users"] = [
                await url_to_dn(
                    request, "user", UcsSchoolBaseModel.unscheme_and_unquote(user)
                )
                for user in (self.users or [])
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
    async with UDM(**await udm_kwargs()) as udm:
        try:
            scs = await SchoolClass.get_all(udm, school_name, filter_str)
        except APICommunicationError as exc:
            raise HTTPException(status_code=exc.status, detail=exc.reason)
        return [await SchoolClassModel.from_lib_model(sc, request, udm) for sc in scs]


@router.get("/{school}/{class_name}")
async def get(class_name: str, school: str, request: Request) -> SchoolClassModel:
    async with UDM(**await udm_kwargs()) as udm:
        sc = await get_lib_obj(udm, SchoolClass, f"{school}-{class_name}", school)
        return await SchoolClassModel.from_lib_model(sc, request, udm)


@router.post("/", status_code=HTTP_201_CREATED)
async def create(
    school_class: SchoolClassCreateModel, request: Request
) -> SchoolClassModel:
    """
    Create a school class with all the information:

    - **name**: name of the school class (required)
    - **school**: school the class belongs to (required)
    - **description**: additional text (optional)
    - **users**: list of URLs to User resources (optional)
    - **ucsschool_roles**: list of tags of the form $ROLE:$CONTEXT_TYPE:$CONTEXT (optional)
    """
    sc = await school_class.as_lib_model(request)
    async with UDM(**await udm_kwargs()) as udm:
        if await sc.exists(udm):
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail="School class exists."
            )
        else:
            await sc.create(udm)
        return await SchoolClassModel.from_lib_model(sc, request, udm)


@router.patch("/{school}/{class_name}", status_code=HTTP_200_OK)
async def partial_update(
    class_name: str,
    school: str,
    school_class: SchoolClassPatchDocument,
    request: Request,
) -> SchoolClassModel:
    async with UDM(**await udm_kwargs()) as udm:
        sc_current = await get_lib_obj(
            udm, SchoolClass, f"{school}-{class_name}", school
        )
        changed = False
        for attr, new_value in (
            await school_class.to_modify_kwargs(school, request)
        ).items():
            current_value = getattr(sc_current, attr)
            if new_value != current_value:
                setattr(sc_current, attr, new_value)
                changed = True
        if changed:
            await sc_current.modify(udm)
        return await SchoolClassModel.from_lib_model(sc_current, request, udm)


@router.put("/{school}/{class_name}", status_code=HTTP_200_OK)
async def complete_update(
    class_name: str, school: str, school_class: SchoolClassCreateModel, request: Request
) -> SchoolClassModel:
    if school != url_to_name(
        request, "school", UcsSchoolBaseModel.unscheme_and_unquote(school_class.school)
    ):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Moving of class to other school is not allowed.",
        )
    async with UDM(**await udm_kwargs()) as udm:
        sc_current = await get_lib_obj(
            udm, SchoolClass, f"{school}-{class_name}", school
        )
        changed = False
        sc_request = await school_class.as_lib_model(request)
        for attr in SchoolClass._attributes.keys():
            current_value = getattr(sc_current, attr)
            new_value = getattr(sc_request, attr)
            if attr in ("ucsschool_roles", "users") and new_value is None:
                new_value = []
            if new_value != current_value:
                setattr(sc_current, attr, new_value)
                changed = True
        if changed:
            await sc_current.modify(udm)
        return await SchoolClassModel.from_lib_model(sc_current, request, udm)


@router.delete("/{school}/{class_name}", status_code=HTTP_204_NO_CONTENT)
async def delete(class_name: str, school: str, request: Request) -> None:
    async with UDM(**await udm_kwargs()) as udm:
        sc = await get_lib_obj(udm, SchoolClass, f"{school}-{class_name}", school)
        await sc.remove(udm)
    return None
