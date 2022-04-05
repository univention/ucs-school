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
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type
from urllib.parse import ParseResult, quote, unquote, urlparse

import psutil
import ujson
from fastapi import HTTPException, Request, status
from pydantic import BaseModel, HttpUrl, validator

from ucsschool.lib.models.base import NoObject, UCSSchoolModel
from udm_rest_client import UDM, UdmObject

from ..config import UDM_MAPPING_CONFIG
from ..exceptions import UnknownUDMProperty
from ..ldap_access import udm_kwargs
from ..urls import url_to_name

if TYPE_CHECKING:  # pragma: no cover
    from pydantic.main import Model

school_name_regex = re.compile("^[a-zA-Z0-9](([a-zA-Z0-9-_]*)([a-zA-Z0-9]$))?$")


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    logger = logging.getLogger(__name__)
    if psutil.Process().terminal():
        _handler = logging.StreamHandler()
        _handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_handler)
    return logger


async def get_lib_obj(
    udm: UDM,
    lib_cls: Type[UCSSchoolModel],
    name: str = None,
    school: str = None,
    dn: str = None,
) -> UCSSchoolModel:
    """
    Either `dn` or both `name` and `school` must be provided.

    :param UDM udm: already open()ed UDM instance
    :param type lib_cls: class (type) the object should be of
    :param str name: `name` attribute of object
    :param str school: `school` (OU) attribute of object
    :param str dn: DN of object
    :return: ucsschool.lib.model object
    :raises HTTPException: if no object could be found
    """
    if not dn and not (name and school):
        raise TypeError("Either 'dn' or both 'name' and 'school' must be provided.")
    dn = dn or lib_cls(name=name, school=school).dn
    try:
        return await lib_cls.from_dn(dn, school, udm)
    except NoObject:
        logger = get_logger()
        logger.warning(
            f"No {lib_cls.__name__} with name={name!r} dn={dn!r} and school={school!r} found."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No object with name={name!r} found or not authorized.",
        )


class LibModelHelperMixin(BaseModel):

    udm_properties: Dict[str, Any] = None

    class Config:
        lib_class: Type[UCSSchoolModel]
        config_id: str = "LibModelHelperMixin"
        json_loads = ujson.loads

    @staticmethod
    def scheme_and_quote(url: str) -> str:
        """Add 's' to scheme (http) and quote characters for HTTP URL."""
        up: ParseResult = urlparse(url)
        replaced = up._replace(scheme="https", path=quote(up.path))
        return replaced.geturl()

    @staticmethod
    def unscheme_and_unquote(url: str) -> str:
        """
        Remove 's' from https and replace '%xx' escapes with their
        single-character equivalents.
        """
        up: ParseResult = urlparse(url)
        replaced = up._replace(scheme="http", path=unquote(up.path))
        return replaced.geturl()

    @validator("udm_properties")
    def only_known_udm_properties(cls, udm_properties: Optional[Dict[str, Any]]):
        property_list = getattr(UDM_MAPPING_CONFIG, cls.Config.config_id, [])
        if not udm_properties:
            return udm_properties
        for key in udm_properties:
            if key not in property_list:
                raise ValueError(
                    f"The udm property {key!r} was not configured for this resource "
                    f"and thus is not allowed."
                )
        return udm_properties

    @classmethod
    def parse_obj(cls: Type["Model"], obj: Any) -> "Model":
        res: LibModelHelperMixin = super(LibModelHelperMixin, cls).parse_obj(obj)
        if res.udm_properties is None:
            res.udm_properties = {}
        return res

    @classmethod
    def get_mapped_udm_properties(cls, udm_obj: UdmObject) -> Dict[str, Any]:
        udm_properties = {}
        property_list = getattr(UDM_MAPPING_CONFIG, cls.Config.config_id, [])
        for prop in property_list:
            try:
                udm_properties[prop] = udm_obj.props[prop]
            except KeyError:
                raise UnknownUDMProperty(f"Unknown UDM property {prop!r}.")
        return udm_properties

    @classmethod
    def filter_udm_properties(cls, udm_properties: Dict[str, Any]) -> Dict[str, Any]:
        property_list = getattr(UDM_MAPPING_CONFIG, cls.Config.config_id, [])
        return {key: value for key, value in udm_properties.items() if key in property_list}

    @classmethod
    async def from_lib_model(
        cls, obj: UCSSchoolModel, request: Request, udm: UDM
    ) -> "LibModelHelperMixin":
        """
        Get the Kelvin object corresponding to the ucsschool.lib object `obj`.
        """
        kwargs = await cls._from_lib_model_kwargs(obj, request, udm)
        return cls(**kwargs)

    @classmethod
    async def _from_lib_model_kwargs(
        cls, obj: UCSSchoolModel, request: Request, udm: UDM
    ) -> Dict[str, Any]:
        """
        Get ucsschool.lib object data as dict that can be used to create a
        Kelvin object.

        kwargs = kelvin_object._from_lib_model_kwargs(LibObject)
        kelvin_object = KelvinClass(**kwargs)
        """
        kwargs = obj.to_dict()
        if "objectType" in kwargs:
            del kwargs["objectType"]
        kwargs["dn"] = kwargs.pop("$dn$")
        if obj.supports_school():
            kwargs["school"] = cls.scheme_and_quote(request.url_for("get", school_name=obj.school))
        udm_obj = await obj.get_udm_object(udm)
        kwargs["udm_properties"] = cls.get_mapped_udm_properties(udm_obj)
        return kwargs

    def __init__(self, **kwargs):
        super(LibModelHelperMixin, self).__init__(**kwargs)
        # Bug #51766: setting udm_properties = {} in model
        # leads to invalid java code.
        if self.udm_properties is None:
            self.udm_properties = {}

    async def as_lib_model(self, request: Request) -> UCSSchoolModel:
        """Get the corresponding ucsschool.lib object to this Kelvin object."""
        kwargs = await self._as_lib_model_kwargs(request)
        udm_properties = kwargs.pop("udm_properties") if "udm_properties" in kwargs else {}
        filtered_udm_properties = self.filter_udm_properties(udm_properties)
        lib_obj: UCSSchoolModel = self.Config.lib_class(**kwargs)
        lib_obj.udm_properties = filtered_udm_properties
        return lib_obj

    async def _as_lib_model_kwargs(self, request: Request) -> Dict[str, Any]:
        """
        Get object data as dict that can be used to create the ucsschool.lib
        object corresponding to this Kelvin object.

        kwargs = kelvin_object._as_lib_model_kwargs()
        lib_object = LibClass(**kwargs)
        """
        kwargs = self.dict()
        if "dn" in kwargs:
            del kwargs["dn"]
        if "url" in kwargs:
            del kwargs["url"]
        return kwargs


class APIAttributesMixin(BaseModel):
    dn: str
    url: HttpUrl
    ucsschool_roles: List[str]


class UcsSchoolBaseModel(LibModelHelperMixin):
    name: str
    school: HttpUrl

    class Config(LibModelHelperMixin.Config):
        ...

    async def as_lib_model(self, request: Request) -> UCSSchoolModel:
        kwargs = await self._as_lib_model_kwargs(request)
        udm_properties = kwargs.pop("udm_properties") if "udm_properties" in kwargs else {}
        filtered_udm_properties = self.filter_udm_properties(udm_properties)
        if self.Config.lib_class.supports_school():
            kwargs["school"] = (
                url_to_name(request, "school", self.unscheme_and_unquote(self.school))
                if self.school
                else self.school
            )
            lib_obj: UCSSchoolModel = self.Config.lib_class(**kwargs)
            lib_obj.udm_properties = filtered_udm_properties
            return lib_obj

    @validator("name", check_fields=False)
    def check_name(cls, value: str) -> str:
        cls.Config.lib_class.name.validate(value)
        return value

    @validator("school", check_fields=False)
    def check_school_name(cls, value: str) -> str:
        if cls.Config.lib_class.supports_school():
            # ucsschool.lib.models.attributes.SchoolName.validate has a
            # conditional we can't fulfill, so this is a copy of that code
            if isinstance(value, HttpUrl):
                check_val = value.path.rsplit("/", 1)[-1]
            else:
                check_val = value
            if not school_name_regex.match(check_val):
                raise ValueError(f"Invalid name for a school (OU): {value!r}")
        return value


class BasePatchModel(BaseModel):
    _guard = object()

    async def to_modify_kwargs(self, request: Request) -> Dict[str, Any]:
        json_body = await request.json()
        # ignore (default) None values unless explicitly requested
        return {
            key: value
            for key, value in self.dict().items()
            if value is not None or json_body.get(key, self._guard) is None
        }


async def udm_ctx():
    async with UDM(**await udm_kwargs()) as udm:
        yield udm
