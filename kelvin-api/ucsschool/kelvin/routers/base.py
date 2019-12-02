import abc
from typing import Any, Dict, Type
from urllib.parse import ParseResult, quote, unquote, urlparse

import ujson
from fastapi import HTTPException
from pydantic import BaseModel, validator
from starlette.requests import Request
from starlette.status import HTTP_404_NOT_FOUND

from ucsschool.lib.models.base import UCSSchoolModel
from udm_rest_client import UDM, NoObject as UdmNoObject

from ..urls import url_to_name


async def get_lib_obj(
    udm: UDM,
    lib_cls: Type[UCSSchoolModel],
    name: str,
    school: str = None,
    dn: str = None,
) -> UCSSchoolModel:
    dn = dn or lib_cls(name=name, school=school).dn
    try:
        return await lib_cls.from_dn(dn, school, udm)
    except UdmNoObject:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No {lib_cls} with name={name!r} and school={school!r} found.",
        )


class UcsSchoolBaseModel(BaseModel, abc.ABC):
    class Config:
        lib_class: Type[UCSSchoolModel]
        json_loads = ujson.loads

    @classmethod
    def scheme_and_quote(cls, url: str) -> str:
        up: ParseResult = urlparse(url)
        replaced = up._replace(scheme="https", path=quote(up.path))
        return replaced.geturl()

    @classmethod
    def unscheme_and_unquote(cls, url: str) -> str:
        up: ParseResult = urlparse(url)
        replaced = up._replace(scheme="http", path=unquote(up.path))
        return replaced.geturl()

    @classmethod
    def from_lib_model(
        cls, obj: UCSSchoolModel, request: Request
    ) -> "UcsSchoolBaseModel":
        kwargs = cls._from_lib_model_kwargs(obj, request)
        return cls(**kwargs)

    @classmethod
    def _from_lib_model_kwargs(
        cls, obj: UCSSchoolModel, request: Request
    ) -> Dict[str, Any]:
        kwargs = obj.to_dict()
        del kwargs["objectType"]
        kwargs["dn"] = kwargs.pop("$dn$")
        if obj.supports_school():
            kwargs["school"] = cls.scheme_and_quote(
                request.url_for("get", school_name=obj.school)
            )
        kwargs["url"] = cls.scheme_and_quote(
            request.url_for("get", class_name=kwargs["name"], school=obj.school)
        )
        return kwargs

    async def as_lib_model(self, request: Request) -> UCSSchoolModel:
        kwargs = await self._as_lib_model_kwargs(request)
        return self.Config.lib_class(**kwargs)

    async def _as_lib_model_kwargs(self, request: Request) -> Dict[str, Any]:
        kwargs = self.dict()
        del kwargs["dn"]
        del kwargs["url"]
        if self.Config.lib_class.supports_school():
            # TODO: have an OU cache, to fix upper/lower/camel case of 'school'
            kwargs["school"] = url_to_name(
                request, "school", self.unscheme_and_unquote(self.school)
            )
        return kwargs

    @validator("name", check_fields=False)
    def check_name(cls, value: str) -> str:
        cls.Config.lib_class.name.validate(value)
        return value

    @validator("school", check_fields=False)
    def check_school_name(cls, value: str) -> str:
        if cls.Config.lib_class.supports_school():
            cls.Config.lib_class.school.validate(value)
        return value
