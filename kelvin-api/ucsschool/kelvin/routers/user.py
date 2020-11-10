# Copyright 2020 Univention GmbH
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

import base64
import datetime
import logging
from collections.abc import Sequence
from functools import lru_cache
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
)

if TYPE_CHECKING:  # pragma: no cover
    from pydantic.main import Model

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from ldap.filter import escape_filter_chars
from pydantic import BaseModel, Field, HttpUrl, SecretStr, root_validator
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from ucsschool.importer.configuration import ReadOnlyDict
from ucsschool.importer.default_user_import_factory import DefaultUserImportFactory
from ucsschool.importer.exceptions import UcsSchoolImportError
from ucsschool.importer.factory import Factory
from ucsschool.importer.mass_import.user_import import UserImport
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.lib.models.attributes import ValidationError as LibValidationError
from udm_rest_client import (
    UDM,
    APICommunicationError,
    CreateError,
    ModifyError,
    MoveError,
    UdmObject,
)
from univention.admin.filter import conjunction, expression

from ..exceptions import UnknownUDMProperty
from ..import_config import get_import_config, init_ucs_school_import_framework
from ..ldap_access import LDAPAccess
from ..urls import url_to_name
from .base import (
    APIAttributesMixin,
    BasePatchModel,
    UcsSchoolBaseModel,
    get_lib_obj,
    get_logger,
    udm_ctx,
)
from .role import SchoolUserRole

router = APIRouter()


@lru_cache(maxsize=1)
def accepted_udm_properties() -> Set[str]:
    return set(ImportUser._attributes.keys()).union(
        set(get_import_config().get("mapped_udm_properties", []))
    )


@lru_cache(maxsize=1)
def get_factory() -> DefaultUserImportFactory:
    init_ucs_school_import_framework()
    return Factory()


@lru_cache(maxsize=1)
def get_user_importer() -> UserImport:
    factory = get_factory()
    return factory.make_user_importer(False)


@lru_cache(maxsize=1)
def ldap_access_obj() -> LDAPAccess:
    return LDAPAccess()


def get_udm_properties(udm_obj: UdmObject) -> Dict[str, Any]:
    config: ReadOnlyDict = get_import_config()
    udm_properties = {}
    for prop in config.get("mapped_udm_properties", []):
        try:
            udm_properties[prop] = udm_obj.props[prop]
        except KeyError:
            raise UnknownUDMProperty(f"Unknown UDM property {prop!r}.")
    return udm_properties


async def get_import_user(udm: UDM, dn: str) -> ImportUser:
    user = await get_lib_obj(udm, ImportUser, dn=dn)
    udm_user_current = await user.get_udm_object(udm)
    current_udm_properties = get_udm_properties(udm_user_current)
    user.udm_properties.update(current_udm_properties)
    return user


class PasswordsHashes(BaseModel):
    user_password: List[str] = Field(
        ...,
        title="'userPassword' in OpenLDAP.",
    )
    samba_nt_password: str = Field(
        ...,
        title="'sambaNTPassword' in OpenLDAP.",
    )
    krb_5_key: List[str] = Field(
        ...,
        title="'krb5Key' in OpenLDAP. **Items are base64 encoded bytes.**",
    )
    krb5_key_version_number: int = Field(
        ...,
        title="'krb5KeyVersionNumber' in OpenLDAP.",
    )
    samba_pwd_last_set: int = Field(
        ...,
        title="'sambaPwdLastSet' in OpenLDAP.",
    )

    def dict_with_ldap_attr_names(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Wrapper around `dict()` that renames the keys to those used in a UCS'
        OpenLDAP.
        """
        res = self.dict(*args, **kwargs)
        res["userPassword"] = res.pop("user_password")
        res["sambaNTPassword"] = res.pop("samba_nt_password")
        res["krb5Key"] = res.pop("krb_5_key")
        res["krb5KeyVersionNumber"] = res.pop("krb5_key_version_number")
        res["sambaPwdLastSet"] = res.pop("samba_pwd_last_set")
        return res

    @property
    def krb_5_key_as_bytes(self) -> List[bytes]:
        """Value of `krb_5_key` as a list of bytes."""
        return [base64.b64decode(k) for k in self.krb_5_key]

    @krb_5_key_as_bytes.setter
    def krb_5_key_as_bytes(self, value: List[bytes]) -> None:
        """Set value of `krb_5_key` from a list of bytes."""
        if not isinstance(value, list):
            raise TypeError("Argument 'value' must be a list.")
        self.krb_5_key = [base64.b64encode(v).decode("ascii") for v in value]


class UserBaseModel(UcsSchoolBaseModel):
    firstname: str
    lastname: str
    birthday: datetime.date = None
    disabled: bool = False
    email: str = None
    record_uid: str = None
    roles: List[HttpUrl]
    schools: List[HttpUrl]
    school_classes: Dict[str, List[str]] = {}
    source_uid: str = None
    ucsschool_roles: List[str] = []
    udm_properties: Dict[str, Any] = None

    def __init__(self, **data: Any) -> None:
        super(UserBaseModel, self).__init__(**data)
        # Bug #51766: setting udm_properties = {} in model
        # leads to invalid java code.
        if self.udm_properties is None:
            self.udm_properties = {}

    @classmethod
    def parse_obj(cls: Type["Model"], obj: Any) -> "Model":
        res: UserBaseModel = super(UserBaseModel, cls).parse_obj(obj)
        if res.udm_properties is None:
            res.udm_properties = {}
        return res

    class Config(UcsSchoolBaseModel.Config):
        lib_class = ImportUser


class UserCreateModel(UserBaseModel):
    name: str = None
    password: SecretStr = None
    school: HttpUrl = None
    schools: List[HttpUrl] = []
    kelvin_password_hashes: PasswordsHashes = None

    class Config(UserBaseModel.Config):
        ...

    @root_validator
    def not_no_school_and_schools(cls, values):
        if not values.get("school") and not values.get("schools"):
            raise ValueError("At least one of 'school' and 'schools' must be set.")
        return values

    @root_validator
    def not_password_and_password_hashes(cls, values):
        if values.get("password") and values.get("kelvin_password_hashes"):
            raise ValueError(
                "Only one of 'password' and 'kelvin_password_hashes' must be set."
            )
        return values

    async def _as_lib_model_kwargs(self, request: Request) -> Dict[str, Any]:
        kwargs = await super()._as_lib_model_kwargs(request)
        if isinstance(kwargs["password"], SecretStr):
            kwargs["password"] = kwargs["password"].get_secret_value()
        kwargs["school"] = (
            url_to_name(request, "school", self.unscheme_and_unquote(self.school))
            if self.school
            else self.school
        )
        kwargs["schools"] = (
            [
                url_to_name(request, "school", self.unscheme_and_unquote(school))
                for school in self.schools
            ]
            if self.schools
            else self.schools
        )
        kwargs["ucsschool_roles"] = [
            SchoolUserRole(
                url_to_name(request, "role", self.unscheme_and_unquote(role))
            ).as_lib_role(school)
            for role in self.roles
            for school in kwargs["schools"]
        ]
        kwargs["birthday"] = str(self.birthday) if self.birthday else self.birthday
        if not kwargs["email"]:
            del kwargs["email"]
        kwargs["roles"] = [
            url_to_name(request, "role", self.unscheme_and_unquote(role_url))
            for role_url in self.roles
        ]
        return kwargs


class UserModel(UserBaseModel, APIAttributesMixin):
    class Config(UserBaseModel.Config):
        ...

    @classmethod
    async def _from_lib_model_kwargs(
        cls, obj: ImportUser, request: Request, udm: UDM
    ) -> Dict[str, Any]:
        kwargs = await super()._from_lib_model_kwargs(obj, request, udm)
        kwargs["schools"] = sorted(
            cls.scheme_and_quote(request.url_for("get", school_name=school))
            for school in obj.schools
        )
        kwargs["url"] = cls.scheme_and_quote(
            request.url_for("get", username=kwargs["name"])
        )
        udm_obj = await obj.get_udm_object(udm)
        roles = sorted(
            {SchoolUserRole.from_lib_role(role) for role in obj.ucsschool_roles}
        )
        kwargs["roles"] = [cls.scheme_and_quote(role.to_url(request)) for role in roles]
        kwargs["source_uid"] = udm_obj.props.ucsschoolSourceUID
        kwargs["record_uid"] = udm_obj.props.ucsschoolRecordUID
        kwargs["school_classes"] = dict(
            (
                school,
                sorted(
                    kls.replace("{}-".format(school), "")
                    for kls in kwargs["school_classes"][school]
                ),
            )
            for school in sorted(kwargs["school_classes"].keys())
        )
        kwargs["udm_properties"] = get_udm_properties(udm_obj)
        return kwargs


class UserPatchModel(BasePatchModel):
    name: str = None
    firstname: str = None
    lastname: str = None
    birthday: datetime.date = None
    disabled: bool = None
    email: str = None
    password: SecretStr = None
    record_uid: str = None
    school: HttpUrl = None
    schools: List[HttpUrl] = None
    school_classes: Dict[str, List[str]] = None
    source_uid: str = None
    udm_properties: Dict[str, Any] = None
    kelvin_password_hashes: PasswordsHashes = None

    @root_validator
    def not_password_and_password_hashes(cls, values):
        if values.get("password") and values.get("kelvin_password_hashes"):
            raise ValueError(
                "Only one of 'password' and 'kelvin_password_hashes' must be set."
            )
        return values

    async def to_modify_kwargs(self, request: Request) -> Dict[str, Any]:  # noqa: C901
        kwargs = await super().to_modify_kwargs(request)
        for key, value in kwargs.items():
            if key == "schools":
                if not isinstance(value, list) or value == []:
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="No or empty list of school URLs in 'schools' property.",
                    )
                kwargs["schools"] = [
                    url_to_name(
                        request, "school", UserCreateModel.unscheme_and_unquote(school)
                    )
                    for school in value
                ]
            elif key == "school":
                if not value:
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="No school URL in 'school' property.",
                    )
                kwargs["school"] = url_to_name(
                    request, "school", UserCreateModel.unscheme_and_unquote(value)
                )
            elif key == "birthday":
                kwargs[key] = str(value) if value else None
            elif key == "disabled":
                if not isinstance(value, bool):
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Non-boolean value in 'disabled' property.",
                    )
            elif key in ("school_classes", "udm_properties"):
                if not isinstance(value, dict):
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Non-object/dict value in {key!r} property.",
                    )
            elif key == "password" and isinstance(value, SecretStr):
                kwargs[key] = value.get_secret_value()
        return kwargs


def all_query_params(
    query_params: Mapping[str, Any], the_locals: Dict[str, Any], known_args: List[str]
) -> Tuple[str, Any]:
    for var in known_args:
        if var == "username":
            yield "name", the_locals[var]
            continue
        yield var, the_locals[var]
    for param, values in query_params.items():
        if param not in known_args + ["name"]:
            yield param, values


def search_query_params_to_udm_filter(  # noqa: C901
    query_params: Iterable[Tuple[str, Any]],
    user_class: Type[ImportUser],
    accepted_properties: Set[str],
) -> Optional[str]:
    filter_parts = []
    for param, values in query_params:
        if param == "roles":
            # already handled
            continue
        if values is None:
            # unused parameter
            continue
        if param == "birthday":
            values = values.strftime("%Y-%m-%d")
        if param == "disabled":
            values = str(int(values))
        if param == "school":
            # already handled
            continue
        if param in accepted_properties:
            if param in user_class._attributes.keys():
                udm_name = user_class._attributes[param].udm_name
            else:
                # mapped_udm_properties
                udm_name = param
            if not isinstance(values, Sequence) or isinstance(values, str):
                # prevent iterating over string, bool etc
                values = [values]
            filter_parts.extend(
                [
                    expression(udm_name, escape_filter_chars(val).replace(r"\2a", "*"))
                    for val in values
                ]
            )
    if filter_parts:
        return str(conjunction("&", filter_parts))
    else:
        return None


@router.get("/", response_model=List[UserModel])  # noqa: C901
async def search(
    request: Request,
    school: str = Query(
        None,
        description="List only users that are members of matching school(s) (OUs).",
    ),
    username: str = Query(
        None,
        alias="name",
        description="List users with this username.",
        title="name",
    ),
    ucsschool_roles: List[str] = Query(
        None,
        regex="^.+:.+:.+$",
    ),
    email: str = Query(
        None,
        regex="^.+@.+$",
    ),
    record_uid: str = Query(None),
    source_uid: str = Query(None),
    birthday: datetime.date = Query(
        None,
        alias="birthday",
        description="Exact match only. Format must be YYYY-MM-DD.",
    ),
    disabled: bool = Query(None),
    firstname: str = Query(None),
    lastname: str = Query(None),
    roles: List[SchoolUserRole] = Query(None),
    logger: logging.Logger = Depends(get_logger),
    accepted_properties: Set[str] = Depends(accepted_udm_properties),
    udm: UDM = Depends(udm_ctx),
) -> List[UserModel]:
    """
    Search for school users.

    All parameters are optional and (unless noted) support the use of ``*``
    for wildcard searches.

    - **school**: list users enlisted in matching school(s) (name of OU, not
        URL)
    - **username**: list users with matching username
    - **ucsschool_roles**: list users that have such an entry in their list of
        ucsschool_roles
    - **email**: the users "primaryMailAddress", used only when the email is
        hosted on UCS, not to be confused with the contact property "e-mail"
    - **record_uid**: identifier unique to the upstream database referenced in
        source_uid, used by the UCS@school import
    - **source_uid**: identifier of the upstream database, used by the
        UCS@school import
    - **birthday**: birthday of user, **exact match only, format: YYYY-MM-DD**
    - **disabled**: **true** to list only disabled users, **false** to list
        only active users
    - **firstname**: given name of users to look for
    - **lastname**: family name of users to look for
    - **roles**: **list** of roles the user should have, **allowed values:
        ["staff"], ["student"], ["teacher"], ["staff", "teacher"]**
    - **additional query parameters**: additionally to the above parameters,
        any UDM property can be used to filter, e.g.
        **?uidNumber=12345&city=Bremen**
    """
    logger.debug(
        "Searching for users with: school=%r username=%r ucsschool_roles=%r "
        "email=%r record_uid=%r source_uid=%r birthday=%r disabled=%r "
        "roles=%r request.query_params=%r",
        school,
        username,
        ucsschool_roles,
        email,
        record_uid,
        source_uid,
        birthday,
        disabled,
        roles,
        request.query_params,
    )
    _known_args = [
        "school",
        "username",
        "ucsschool_roles",
        "email",
        "record_uid",
        "source_uid",
        "birthday",
        "disabled",
        "roles",
    ]
    if roles and set(roles) not in (
        {SchoolUserRole.staff},
        {SchoolUserRole.student},
        {SchoolUserRole.teacher},
        {SchoolUserRole.staff, SchoolUserRole.teacher},
    ):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown value for 'roles' property: {roles!r}",
        )
    user_class = SchoolUserRole.get_lib_class(roles)

    if school:
        school_pattern = escape_filter_chars(school).replace(r"\2a", "*")
        school_filter = f"(ucsschoolSchool={school_pattern})"
    else:
        school_filter = ""

    query_params = all_query_params(request.query_params, locals(), _known_args)
    filter_str = (
        search_query_params_to_udm_filter(query_params, user_class, accepted_properties)
        or ""
    )
    if school_filter or filter_str:
        udm_filter = f"(&{user_class.type_filter}{school_filter}{filter_str})"
    else:
        udm_filter = user_class.type_filter
    logger.debug("Looking for %r with filter %r...", user_class.__name__, udm_filter)
    users: List[ImportUser] = []
    try:
        async for udm_obj in udm.get("users/user").search(udm_filter):
            users.append(await user_class.from_udm_obj(udm_obj, None, udm))
    except APICommunicationError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.reason)
    users.sort(key=attrgetter("name"))
    return [await UserModel.from_lib_model(user, request, udm) for user in users]


@router.get("/{username}", response_model=UserModel)
async def get(
    username: str,
    request: Request,
    logger: logging.Logger = Depends(get_logger),
    udm: UDM = Depends(udm_ctx),
) -> UserModel:
    """
    Fetch a specific school user.

    - **username**: name of the school user (required)
    """
    async for udm_obj in udm.get("users/user").search(
        f"uid={escape_filter_chars(username)}"
    ):
        break
    else:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No User with username {username!r} found.",
        )
    user = await get_import_user(udm, udm_obj.dn)
    return await UserModel.from_lib_model(user, request, udm)


@router.post("/", status_code=HTTP_201_CREATED, response_model=UserModel)
async def create(
    request: Request,
    request_user: UserCreateModel = Body(
        ...,
        alias="user",
        title="user",
    ),
    logger: logging.Logger = Depends(get_logger),
    udm: UDM = Depends(udm_ctx),
) -> UserModel:
    """
    Create a school user with all the information:

    - **name**: name of the user (**required**, unless a template is configured)
    - **firstname**: given name of the user (**required**)
    - **lastname**: family name of the user (**required**)
    - **school**: school (OU) the user belongs to (**required unless
        schools is set**, URL of a **school** resource)
    - **schools**: list of schools the user belongs to (**required unless
        school is set**, list of URLs to **school** resources)
    - **roles**: user type, one of staff, student, teacher or teacher and staff
        (**required**, list of URLs to **role** resources)
    - **password**: users password, a random one will be generated if unset
        (optional)
    - **email**: the users email address (**mailPrimaryAddress**), used only
        when the email domain is hosted on UCS, not to be confused with the
        contact property **e-mail** (optional)
    - **record_uid**: identifier unique to the upstream database referenced by
        **source_uid** (**required**, used by the UCS@school import)
    - **source_uid**: identifier of the upstream database (optional, will be
        **Kelvin** if unset, used by the UCS@school import)
    - **school_classes**: school classes the user is a member of (optional,
        format: **{"school1": ["class1", "class2"], "school2": ["class3"]}**)
    - **birthday**: birthday of user (optional, format: **YYYY-MM-DD**)
    - **disabled**: whether the user should be created deactivated (optional,
        default if **false**)
    - **ucsschool_roles**: list of roles the user has in to each school
        (optional, auto-managed by system, setting and changing discouraged)
    - **udm_properties**: object with UDM properties (optional, e.g.
        **{"street": "Luise Av."}**, must be configured in **kelvin.json** in
        **mapped_udm_properties**, see documentation)
    - **kelvin_password_hashes**: Password hashes to be stored unchanged in
        OpenLDAP (optional)
    """
    request_user.Config.lib_class = SchoolUserRole.get_lib_class(
        [
            SchoolUserRole(
                url_to_name(
                    request, "role", UcsSchoolBaseModel.unscheme_and_unquote(role)
                )
            )
            for role in request_user.roles
        ]
    )
    user: ImportUser = await request_user.as_lib_model(request)
    if await user.exists(udm):
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail="School user exists.")

    try:
        user.prepare_uids()
        user_importer = get_user_importer()
        # user_importer.determine_add_modify_action() will call user.prepare_all()
        user = await user_importer.determine_add_modify_action(user)
        if user.action != "A":
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail=f"School user exists (name={user.name!r}, "
                f"record_uid={user.record_uid!r}, "
                f"source_uid={user.source_uid!r}).",
            )
        await user.validate(udm, validate_unlikely_changes=True, check_username=True)
        logger.info("Going to create %s with %r...", user, user.to_dict())
        res = await user.create(udm)
    except (CreateError, LibValidationError, UcsSchoolImportError) as exc:
        error_msg = f"Failed to create {user!r}: {exc}"
        logger.exception(error_msg)
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=error_msg)

    if res:
        logger.info("Success creating %r.", user)
    else:
        error_msg = f"Error creating {user!r}: {user.errors!r}"
        logger.error(error_msg)
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=error_msg)

    if request_user.kelvin_password_hashes:
        await set_password_hashes(user.dn, request_user.kelvin_password_hashes)

    return await UserModel.from_lib_model(user, request, udm)


async def change_school(
    udm: UDM,
    logger: logging.Logger,
    user: ImportUser,
    new_school: str,
    new_schools: List[str],
) -> ImportUser:
    if new_school not in (new_schools or user.schools):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"New 'school' {new_school!r} not in current or future 'schools'.",
        )
    if new_school == user.school:
        return user
    logger.info("Moving %r from OU %r to OU %r...", user, user.school, new_school)
    new_schools = new_schools or list(set(user.schools + [new_school]))
    user.schools = new_schools
    try:
        await user.change_school(new_school, udm)
    except (LibValidationError, MoveError) as exc:
        error_msg = (
            f"Moving {user!r} from OU {user.school!r} to OU {new_school!r}: {exc}"
        )
        logger.exception(error_msg)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    return await get_import_user(udm, user.dn)


async def rename_user(
    udm: UDM, logger: logging.Logger, user: ImportUser, new_name: str
) -> ImportUser:
    if user.name == new_name:
        return user
    logger.info("Renaming %r to %r...", user, new_name)
    old_name = user.name
    user.name = new_name
    try:
        res = await user.move(udm, force=True)
    except (LibValidationError, ModifyError, MoveError) as exc:
        error_msg = f"Renaming {user!r} from {old_name!r} to {user.name!r}: {exc}"
        logger.exception(error_msg)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    if not res:
        user.name = old_name
        error_msg = f"Failed to rename {user!r} to {new_name!r}: {user.errors!r}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    user = await get_import_user(udm, user.dn)
    return user


@router.patch("/{username}", status_code=HTTP_200_OK, response_model=UserModel)
async def partial_update(  # noqa: C901
    username: str,
    user: UserPatchModel,
    request: Request,
    logger: logging.Logger = Depends(get_logger),
    udm: UDM = Depends(udm_ctx),
) -> UserModel:
    """
    Patch a school user with partial information

    - **name**: name of the school user
    - **firstname**: first name of the school user
    - **lastname**: last name of the school user
    - **role**: One of either student, staff, teacher, teacher_and_staff
    """
    async for udm_obj in udm.get("users/user").search(
        f"uid={escape_filter_chars(username)}"
    ):
        break
    else:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No User with username {username!r} found.",
        )
    to_change = await user.to_modify_kwargs(request)
    user_current = await get_import_user(udm, udm_obj.dn)

    # 1. move
    try:
        new_school = to_change["school"]
        new_schools = to_change.get("schools", [])
        user_current = await change_school(
            udm, logger, user_current, new_school, new_schools
        )
    except KeyError:
        pass

    # 2. rename
    try:
        new_name = to_change["name"]
        user_current = await rename_user(udm, logger, user_current, new_name)
    except KeyError:
        pass

    # 3. modify
    changed = False
    for attr, new_value in to_change.items():
        if attr == "kelvin_password_hashes":
            # handled below
            continue
        current_value = getattr(user_current, attr)
        if new_value != current_value:
            setattr(user_current, attr, new_value)
            changed = True
    if changed:
        try:
            await user_current.modify(udm)
        except (LibValidationError, ModifyError, UcsSchoolImportError) as exc:
            logger.warning(
                "Error modifying user %r with %r: %s",
                user_current,
                await request.json(),
                exc,
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    # 4. password hashes
    if user.kelvin_password_hashes:
        await set_password_hashes(user_current.dn, user.kelvin_password_hashes)

    return await UserModel.from_lib_model(user_current, request, udm)


@router.put("/{username}", status_code=HTTP_200_OK, response_model=UserModel)
async def complete_update(
    username: str,
    user: UserCreateModel,
    request: Request,
    logger: logging.Logger = Depends(get_logger),
    udm: UDM = Depends(udm_ctx),
) -> UserModel:
    """
    Update a school user with all the information:

    - **name**: name of the school user (required)
    - **firstname**: name of the school user (required)
    - **lastname**: name of the school user (required)
    - **school**: school the class belongs to (required)
    - **role**: One of either student, staff, teacher, teacher_and_staff
    """
    async for udm_obj in udm.get("users/user").search(
        f"uid={escape_filter_chars(username)}"
    ):
        break
    else:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No User with username {username!r} found.",
        )
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
    user_request: ImportUser = await user.as_lib_model(request)
    user_current: ImportUser = await get_import_user(udm, udm_obj.dn)

    # 1. move
    new_school = user_request.school
    new_schools = user_request.schools
    user_current = await change_school(
        udm, logger, user_current, new_school, new_schools
    )

    # 2. rename
    new_name = user_request.name
    user_current = await rename_user(udm, logger, user_current, new_name)

    # 3. modify
    changed = False
    # TODO: Should not access private interface:
    for attr in list(ImportUser._attributes.keys()) + ["udm_properties"]:
        if attr == "kelvin_password_hashes":
            # handled below
            continue
        if attr in ("school", "schools"):
            continue  # school change was already handled above
        current_value = getattr(user_current, attr)
        new_value = getattr(user_request, attr)
        if attr == "ucsschool_roles" and new_value is None:
            new_value = []
        if new_value != current_value:
            setattr(user_current, attr, new_value)
            changed = True
    if changed:
        try:
            await user_current.modify(udm)
        except (LibValidationError, ModifyError, UcsSchoolImportError) as exc:
            logger.warning(
                "Error modifying user %r with %r: %s",
                user_current,
                await request.json(),
                exc,
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    # 4. password hashes
    if user.kelvin_password_hashes:
        await set_password_hashes(user_current.dn, user.kelvin_password_hashes)

    return await UserModel.from_lib_model(user_current, request, udm)


@router.delete("/{username}", status_code=HTTP_204_NO_CONTENT)
async def delete(
    username: str,
    request: Request,
    udm: UDM = Depends(udm_ctx),
) -> None:
    """
    Delete a school user
    """
    async for udm_obj in udm.get("users/user").search(
        f"uid={escape_filter_chars(username)}"
    ):
        break
    else:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No User with username {username!r} found.",
        )
    user = await get_lib_obj(udm, ImportUser, dn=udm_obj.dn)
    await user.remove(udm)


async def set_password_hashes(dn: str, kelvin_password_hashes: PasswordsHashes) -> None:
    logger: logging.Logger = get_logger()
    ldap_access = ldap_access_obj()
    pw_hashes = kelvin_password_hashes.dict_with_ldap_attr_names()
    pw_hashes["krb5Key"] = kelvin_password_hashes.krb_5_key_as_bytes
    for key, value in pw_hashes.items():
        pw_hashes[key] = value if isinstance(value, list) else [value]
    res = await ldap_access.modify(dn, pw_hashes)
    if res:
        logger.info("Successfully set password hashes of %r.", dn)
    else:
        logger.error("Error modifying password hashes of %r.", dn)
