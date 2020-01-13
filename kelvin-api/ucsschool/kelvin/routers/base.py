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

import re
from typing import Any, Dict, List, Type
from urllib.parse import ParseResult, quote, unquote, urlparse

import ujson
from fastapi import HTTPException
from pydantic import BaseModel, HttpUrl, validator
from starlette.requests import Request
from starlette.status import HTTP_404_NOT_FOUND

from ucsschool.lib.models.base import NoObject, UCSSchoolModel
from udm_rest_client import UDM

from ..ldap_access import udm_kwargs
from ..urls import url_to_name

school_name_regex = re.compile("^[a-zA-Z0-9](([a-zA-Z0-9-]*)([a-zA-Z0-9]$))?$")


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
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No {lib_cls.__name__} with name={name!r} dn={dn!r} and school={school!r} found.",
        )


class LibModelHelperMixin(BaseModel):
    class Config:
        lib_class: Type[UCSSchoolModel]
        json_loads = ujson.loads

    @staticmethod
    def scheme_and_quote(url: str) -> str:
        up: ParseResult = urlparse(url)
        replaced = up._replace(scheme="https", path=quote(up.path))
        return replaced.geturl()

    @staticmethod
    def unscheme_and_unquote(url: str) -> str:
        up: ParseResult = urlparse(url)
        replaced = up._replace(scheme="http", path=unquote(up.path))
        return replaced.geturl()

    @classmethod
    async def from_lib_model(
        cls, obj: UCSSchoolModel, request: Request, udm: UDM
    ) -> "LibModelHelperMixin":
        kwargs = await cls._from_lib_model_kwargs(obj, request, udm)
        return cls(**kwargs)

    @classmethod
    async def _from_lib_model_kwargs(
        cls, obj: UCSSchoolModel, request: Request, udm: UDM
    ) -> Dict[str, Any]:
        kwargs = obj.to_dict()
        if "objectType" in kwargs:
            del kwargs["objectType"]
        kwargs["dn"] = kwargs.pop("$dn$")
        if obj.supports_school():
            kwargs["school"] = cls.scheme_and_quote(
                request.url_for("get", school_name=obj.school)
            )
        return kwargs

    async def as_lib_model(self, request: Request) -> UCSSchoolModel:
        kwargs = await self._as_lib_model_kwargs(request)
        return self.Config.lib_class(**kwargs)

    async def _as_lib_model_kwargs(self, request: Request) -> Dict[str, Any]:
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
        if self.Config.lib_class.supports_school():
            # TODO: have an OU cache, to fix upper/lower/camel case of 'school'
            kwargs["school"] = url_to_name(
                request, "school", self.unscheme_and_unquote(self.school)
            )
            return self.Config.lib_class(**kwargs)

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
    async def to_modify_kwargs(self) -> Dict[str, Any]:
        res = {}
        for key, value in self.dict().items():
            if value is not None:
                res[key] = value
        return res


async def udm_ctx():
    async with UDM(**await udm_kwargs()) as udm:
        yield udm
