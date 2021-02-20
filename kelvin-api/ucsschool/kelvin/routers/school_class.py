# Copyright 2020-2021 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, HttpUrl, root_validator, validator

from ucsschool.lib.models.attributes import ValidationError as LibValidationError
from ucsschool.lib.models.group import SchoolClass
from udm_rest_client import UDM, APICommunicationError, CreateError, ModifyError

from ..opa import OPAClient
from ..token_auth import oauth2_scheme
from ..urls import name_from_dn, url_to_dn, url_to_name
from .base import APIAttributesMixin, UcsSchoolBaseModel, get_lib_obj, get_logger, udm_ctx

router = APIRouter()


def check_name(value: str) -> str:
    """
    The SchoolClass.name is checked in check_name2.
    This function is reused as a pass-through validator,
    root_validator can't be reused this way.
    """
    return value


class SchoolClassCreateModel(UcsSchoolBaseModel):
    description: str = None
    users: List[HttpUrl] = None

    class Config(UcsSchoolBaseModel.Config):
        lib_class = SchoolClass

    _validate_name = validator("name", allow_reuse=True)(check_name)

    @root_validator
    def check_name2(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate 'OU-name' to prevent 'must be at least 2 characters long'
        error when checking a class name with just one char.
        """
        school = values["school"].split("/")[-1]
        class_name = f"{school}-{values['name']}"
        cls.Config.lib_class.name.validate(class_name)
        return values

    @classmethod
    async def _from_lib_model_kwargs(
        cls, obj: SchoolClass, request: Request, udm: UDM
    ) -> Dict[str, Any]:
        kwargs = await super()._from_lib_model_kwargs(obj, request, udm)
        kwargs["url"] = cls.scheme_and_quote(
            request.url_for("get", class_name=kwargs["name"], school=obj.school)
        )
        kwargs["users"] = [
            cls.scheme_and_quote(request.url_for("get", username=name_from_dn(dn))) for dn in obj.users
        ]
        return kwargs

    async def _as_lib_model_kwargs(self, request: Request) -> Dict[str, Any]:
        kwargs = await super()._as_lib_model_kwargs(request)
        school_name = url_to_name(request, "school", self.unscheme_and_unquote(kwargs["school"]))
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
    ucsschool_roles: List[str] = Field(None, title="Roles of this object. Don't change if unsure.")
    users: List[HttpUrl] = None

    class Config(UcsSchoolBaseModel.Config):
        lib_class = SchoolClass

    @validator("name")
    def check_name(cls, value: str) -> str:
        """
        At this point we know `school` is valid, but
        we don't have it in the values. Thus we use
        the dummy school name DEMOSCHOOL.
        """
        class_name = f"DEMOSCHOOL-{value}"
        cls.Config.lib_class.name.validate(class_name)
        return value

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
                await url_to_dn(request, "user", UcsSchoolBaseModel.unscheme_and_unquote(user))
                for user in (self.users or [])
            ]  # this is expensive :/
        return res


@router.get("/", response_model=List[SchoolClassModel])
async def search(
    request: Request,
    school: str = Query(
        ...,
        description="Name of school (``OU``) in which to search for classes "
        "(**case sensitive, exact match, required**).",
        min_length=2,
    ),
    class_name: str = Query(
        None,
        alias="name",
        description="List classes with this name. (optional, ``*`` can be used "
        "for an inexact search).",
        title="name",
    ),
    udm: UDM = Depends(udm_ctx),
    token: str = Depends(oauth2_scheme),
) -> List[SchoolClassModel]:
    """
    Search for school classes.

    - **school**: school (``OU``) the classes belong to, **case sensitive**,
        exact match only (required)
    - **name**: names of school classes to look for, use ``*`` for inexact
        search (optional)
    """
    if not await OPAClient.instance().check_policy_true(
        policy="classes",
        token=token,
        request=dict(method="GET", path=["classes"]),
        target={},
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to list school classes.",
        )
    if class_name:
        filter_str = f"name={school}-{class_name}"
    else:
        filter_str = None
    try:
        scs = await SchoolClass.get_all(udm, school, filter_str)
    except APICommunicationError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.reason)
    return [await SchoolClassModel.from_lib_model(sc, request, udm) for sc in scs]


@router.get("/{school}/{class_name}", response_model=SchoolClassModel)
async def get(
    class_name: str,
    school: str,
    request: Request,
    udm: UDM = Depends(udm_ctx),
    token: str = Depends(oauth2_scheme),
) -> SchoolClassModel:
    if not await OPAClient.instance().check_policy_true(
        policy="classes",
        token=token,
        request=dict(method="GET", path=["classes", class_name]),
        target={},
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to list school classes.",
        )
    sc = await get_lib_obj(udm, SchoolClass, f"{school}-{class_name}", school)
    return await SchoolClassModel.from_lib_model(sc, request, udm)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchoolClassModel)
async def create(
    school_class: SchoolClassCreateModel,
    request: Request,
    udm: UDM = Depends(udm_ctx),
    logger: logging.Logger = Depends(get_logger),
    token: str = Depends(oauth2_scheme),
) -> SchoolClassModel:
    """
    Create a school class with all the information:

    - **name**: name of the school class (**required**)
    - **school**: school the class belongs to (**required**)
    - **description**: additional text (optional)
    - **users**: list of URLs to User resources (optional)
    - **ucsschool_roles**: list of tags of the form
        $ROLE:$CONTEXT_TYPE:$CONTEXT (optional)
    """
    if not await OPAClient.instance().check_policy_true(
        policy="classes",
        token=token,
        request=dict(method="POST", path=["classes"]),
        target={},
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to create school classes.",
        )
    sc: SchoolClass = await school_class.as_lib_model(request)
    if await sc.exists(udm):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="School class exists.")
    else:
        try:
            await sc.create(udm)
        except (LibValidationError, CreateError) as exc:
            error_msg = f"Failed to create school class {sc!r}: {exc}"
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    return await SchoolClassModel.from_lib_model(sc, request, udm)


@router.patch(
    "/{school}/{class_name}",
    status_code=status.HTTP_200_OK,
    response_model=SchoolClassModel,
)
async def partial_update(
    class_name: str,
    school: str,
    school_class: SchoolClassPatchDocument,
    request: Request,
    udm: UDM = Depends(udm_ctx),
    logger: logging.Logger = Depends(get_logger),
    token: str = Depends(oauth2_scheme),
) -> SchoolClassModel:
    if not await OPAClient.instance().check_policy_true(
        policy="classes",
        token=token,
        request=dict(method="PATCH", path=["classes", class_name]),
        target={},
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to edit school classes.",
        )
    sc_current = await get_lib_obj(udm, SchoolClass, f"{school}-{class_name}", school)
    changed = False
    for attr, new_value in (await school_class.to_modify_kwargs(school, request)).items():
        current_value = getattr(sc_current, attr)
        if new_value != current_value:
            setattr(sc_current, attr, new_value)
            changed = True
    if changed:
        try:
            await sc_current.modify(udm)
        except (LibValidationError, ModifyError) as exc:
            logger.warning(
                "Error modifying school class %r with %r: %s",
                sc_current,
                await request.json(),
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
    return await SchoolClassModel.from_lib_model(sc_current, request, udm)


@router.put(
    "/{school}/{class_name}",
    status_code=status.HTTP_200_OK,
    response_model=SchoolClassModel,
)
async def complete_update(
    class_name: str,
    school: str,
    school_class: SchoolClassCreateModel,
    request: Request,
    udm: UDM = Depends(udm_ctx),
    logger: logging.Logger = Depends(get_logger),
    token: str = Depends(oauth2_scheme),
) -> SchoolClassModel:
    if not await OPAClient.instance().check_policy_true(
        policy="classes",
        token=token,
        request=dict(method="PUT", path=["classes", class_name]),
        target={},
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to edit school classes.",
        )
    if school != url_to_name(
        request, "school", UcsSchoolBaseModel.unscheme_and_unquote(school_class.school)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Moving of class to other school is not allowed.",
        )
    sc_current = await get_lib_obj(udm, SchoolClass, f"{school}-{class_name}", school)
    changed = False
    sc_request: SchoolClass = await school_class.as_lib_model(request)
    for attr in SchoolClass._attributes.keys():
        current_value = getattr(sc_current, attr)
        new_value = getattr(sc_request, attr)
        if attr in ("ucsschool_roles", "users") and new_value is None:
            new_value = []
        if new_value != current_value:
            setattr(sc_current, attr, new_value)
            changed = True
    if changed:
        try:
            await sc_current.modify(udm)
        except (LibValidationError, ModifyError) as exc:
            logger.warning(
                "Error modifying school class %r with %r: %s",
                sc_current,
                await request.json(),
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
    return await SchoolClassModel.from_lib_model(sc_current, request, udm)


@router.delete("/{school}/{class_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    class_name: str,
    school: str,
    request: Request,
    udm: UDM = Depends(udm_ctx),
    token: str = Depends(oauth2_scheme),
) -> None:
    if not await OPAClient.instance().check_policy_true(
        policy="classes",
        token=token,
        request=dict(method="DELETE", path=["classes", class_name]),
        target={},
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to delete school classes.",
        )
    sc = await get_lib_obj(udm, SchoolClass, f"{school}-{class_name}", school)
    await sc.remove(udm)
