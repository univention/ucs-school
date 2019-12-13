import datetime
import logging
from functools import lru_cache
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from ldap.filter import escape_filter_chars
from pydantic import HttpUrl
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from ucsschool.importer.models.import_user import ImportUser
from ucsschool.lib.models.user import User
from udm_rest_client import UDM, APICommunicationError

from ..ldap_access import udm_kwargs
from ..urls import url_to_name
from .base import BasePatchModel, UcsSchoolBaseModel, get_lib_obj, APIAttributesMixin
from .role import SchoolUserRole

router = APIRouter()


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    return logging.getLogger(__name__)


class UserBaseModel(UcsSchoolBaseModel):
    email: str = None
    record_uid: str = None
    source_uid: str = None
    birthday: datetime.date = None
    disabled: bool = False
    firstname: str
    lastname: str
    udm_properties: Dict[str, Any] = {}
    schools: List[HttpUrl]
    school_classes: Dict[str, List[str]] = {}
    roles: List[HttpUrl]

    class Config(UcsSchoolBaseModel.Config):
        lib_class = ImportUser


class UserCreateModel(UserBaseModel):
    async def _as_lib_model_kwargs(self, request: Request) -> Dict[str, Any]:
        kwargs = await super()._as_lib_model_kwargs(request)
        kwargs["school"] = url_to_name(
            request, "school", self.unscheme_and_unquote(self.school)
        )
        kwargs["schools"] = [
            url_to_name(request, "school", self.unscheme_and_unquote(school))
            for school in self.schools
        ]
        kwargs["ucsschool_roles"] = [
            SchoolUserRole(url_to_name(request, "role", role)).as_lib_role(
                kwargs["school"]
            )
            for role in self.roles
        ]
        kwargs["birthday"] = str(self.birthday)
        if not kwargs["email"]:
            del kwargs["email"]
        return kwargs


class UserModel(UserBaseModel, APIAttributesMixin):
    @classmethod
    async def _from_lib_model_kwargs(
        cls, obj: User, request: Request, udm: UDM
    ) -> Dict[str, Any]:
        kwargs = await super()._from_lib_model_kwargs(obj, request, udm)
        kwargs["schools"] = [kwargs["school"]]
        kwargs["url"] = cls.scheme_and_quote(
            request.url_for("get", username=kwargs["name"])
        )
        udm_obj = await obj.get_udm_object(udm)
        roles = [SchoolUserRole.from_lib_role(role) for role in obj.ucsschool_roles]
        kwargs["source_uid"] = udm_obj.props.ucsschoolSourceUID
        kwargs["record_uid"] = udm_obj.props.ucsschoolRecordUID
        kwargs["roles"] = [cls.scheme_and_quote(role.to_url(request)) for role in roles]

        return kwargs


class UserPatchModel(BasePatchModel):
    email: str = ""
    record_uid: str = ""
    source_uid: str = ""
    birthday: datetime.date = None
    disabled: bool = False
    name: str = ""
    firstname: str = ""
    lastname: str = ""
    udm_properties: Dict[str, Any] = {}
    school: HttpUrl = None
    schools: List[HttpUrl] = None
    school_classes: Dict[str, List[str]] = {}

    async def to_modify_kwargs(self) -> Dict[str, Any]:
        kwargs = await super().to_modify_kwargs()
        for key, value in kwargs.items():
            if key == "schools":
                print(kwargs)
                kwargs["schools"] = [str(school).split("/")[-1] for school in value]
            elif key == "school":
                kwargs["school"] = str(value).split("/")[-1]
            elif key == "birthday":
                kwargs[key] = str(value)
        return kwargs


@router.get("/", response_model=List[UserModel])
async def search(
    request: Request,
    name_filter: str = Query(
        None,
        title="List users with this name. '*' can be used for an inexact search.",
        min_length=2,
    ),
    school_filter: str = Query(
        ..., title="List only users in school with this name (not URL). ", min_length=2
    ),
    logger: logging.Logger = Depends(get_logger),
) -> List[UserModel]:
    """
    Search for school users.

    - **name**: name of the school user, use '*' for inexact search (optional)
    - **school**: school the user belongs to, **case sensitive** (required)
    """
    logger.debug(
        "Searching for users with: name_filter=%r school_filter=%r",
        name_filter,
        school_filter,
    )
    if name_filter:
        filter_str = f"username={name_filter}"
    else:
        filter_str = None
    async with UDM(**await udm_kwargs()) as udm:
        try:
            users = await User.get_all(udm, school_filter, filter_str)
        except APICommunicationError as exc:
            raise HTTPException(status_code=exc.status, detail=exc.reason)
        return [await UserModel.from_lib_model(user, request, udm) for user in users]


@router.get("/{username}", response_model=UserModel)
async def get(
    username: str, request: Request, logger: logging.Logger = Depends(get_logger)
) -> UserModel:
    """
    Search for specific school user.

    - **username**: name of the school user (required)
    """
    async with UDM(**await udm_kwargs()) as udm:
        async for udm_obj in udm.get("users/user").search(
            f"uid={escape_filter_chars(username)}"
        ):
            break
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"No User with username {username!r} found.",
            )
        user = await get_lib_obj(udm, User, dn=udm_obj.dn)
        return await UserModel.from_lib_model(user, request, udm)


@router.post("/", status_code=HTTP_201_CREATED, response_model=UserModel)
async def create(
    user: UserCreateModel,
    request: Request,
    logger: logging.Logger = Depends(get_logger),
) -> UserModel:
    """
    Create a school user with all the information:

    - **name**: name of the school user (required)
    - **firstname**: name of the school user (required)
    - **lastname**: name of the school user (required)
    - **school**: school the class belongs to (required)
    - **role**: One of either student, staff, teacher, teachers_and_staff
    """
    user.Config.lib_class = SchoolUserRole.get_lib_class(
        [
            SchoolUserRole(
                url_to_name(
                    request, "role", UcsSchoolBaseModel.unscheme_and_unquote(role)
                )
            )
            for role in user.roles
        ]
    )
    user = await user.as_lib_model(request)
    async with UDM(**await udm_kwargs()) as udm:
        if await user.exists(udm):
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail="School user exists."
            )
        else:
            await user.create(udm)
        return await UserModel.from_lib_model(user, request, udm)


@router.patch("/{username}", status_code=HTTP_200_OK, response_model=UserModel)
async def partial_update(
    username: str,
    user: UserPatchModel,
    request: Request,
    logger: logging.Logger = Depends(get_logger),
) -> UserModel:
    """
    Patch a school user with partial information

    - **name**: name of the school user
    - **firstname**: first name of the school user
    - **lastname**: last name of the school user
    - **role**: One of either student, staff, teacher, teachers_and_staff
    """
    async with UDM(**await udm_kwargs()) as udm:
        async for udm_obj in udm.get("users/user").search(
            f"uid={escape_filter_chars(username)}"
        ):
            break
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"No User with username {username!r} found.",
            )
        user_current = await get_lib_obj(udm, User, dn=udm_obj.dn)
        changed = False
        to_change = await user.to_modify_kwargs()
        for attr, new_value in to_change.items():
            if attr in ("school", "schools"):
                continue  # School move handled separately
            current_value = getattr(user_current, attr)
            if new_value != current_value:
                setattr(user_current, attr, new_value)
                changed = True
        if changed:
            await user_current.modify(udm)
        if "school" in to_change:
            await user_current.change_school(to_change["school"], udm)
        return await UserModel.from_lib_model(user_current, request, udm)


@router.put("/{username}", status_code=HTTP_200_OK, response_model=UserModel)
async def complete_update(
    username: str,
    user: UserCreateModel,
    request: Request,
    logger: logging.Logger = Depends(get_logger),
) -> UserModel:
    """
    Update a school user with all the information:

    - **name**: name of the school user (required)
    - **firstname**: name of the school user (required)
    - **lastname**: name of the school user (required)
    - **school**: school the class belongs to (required)
    - **role**: One of either student, staff, teacher, teachers_and_staff
    """
    user.Config.lib_class = SchoolUserRole.get_lib_class(
        [
            SchoolUserRole(
                url_to_name(
                    request, "role", UcsSchoolBaseModel.unscheme_and_unquote(role)
                )
            )
            for role in user.roles
        ]
    )
    async with UDM(**await udm_kwargs()) as udm:
        async for udm_obj in udm.get("users/user").search(
            f"uid={escape_filter_chars(username)}"
        ):
            break
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"No User with username {username!r} found.",
            )
        user_current = await get_lib_obj(udm, User, dn=udm_obj.dn)
        changed = False
        user_request = await user.as_lib_model(request)
        for (
            attr
        ) in User._attributes.keys():  # TODO: Should not access private interface!
            if attr in ("school", "schools"):
                continue  # school change is handled separately
            current_value = getattr(user_current, attr)
            new_value = getattr(user_request, attr)
            if attr in ("ucsschool_roles", "users") and new_value is None:
                new_value = []
            if new_value != current_value:
                setattr(user_current, attr, new_value)
                changed = True
        if changed:
            await user_current.modify(udm)
        return await UserModel.from_lib_model(user_current, request, udm)


@router.delete("/{username}", status_code=HTTP_204_NO_CONTENT)
async def delete(username: str, request: Request) -> None:
    """
    Delete a school user
    """
    async with UDM(**await udm_kwargs()) as udm:
        async for udm_obj in udm.get("users/user").search(
            f"uid={escape_filter_chars(username)}"
        ):
            break
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"No User with username {username!r} found.",
            )
        user = await get_lib_obj(udm, User, dn=udm_obj.dn)
        await user.remove(udm)
    return None
