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

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from ldap.filter import escape_filter_chars
from starlette.requests import Request

from ucsschool.lib.models.school import School
from udm_rest_client import UDM

from .base import APIAttributesMixin, LibModelHelperMixin, udm_ctx

router = APIRouter()


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    return logging.getLogger(__name__)


class SchoolCreateModel(LibModelHelperMixin):
    name: str
    display_name: str = None
    administrative_servers: List[str] = []
    class_share_file_server: str = None
    dc_name: str = None
    dc_name_administrative: str = None
    educational_servers: List[str] = []
    home_share_file_server: str = None
    ucsschool_roles: List[str] = []

    class Config(LibModelHelperMixin.Config):
        lib_class = School


class SchoolModel(SchoolCreateModel, APIAttributesMixin):

    _dn2name: Dict[str, str] = {}

    class Config(SchoolCreateModel.Config):
        ...

    @classmethod
    async def _from_lib_model_kwargs(
        cls, obj: School, request: Request, udm: UDM
    ) -> Dict[str, Any]:
        kwargs = await super()._from_lib_model_kwargs(obj, request, udm)
        kwargs["url"] = cls.scheme_and_quote(
            request.url_for("get", school_name=kwargs["name"])
        )
        kwargs["administrative_servers"] = [
            await cls.computer_dn2name(udm, dn) for dn in obj.administrative_servers
        ]
        kwargs["class_share_file_server"] = await cls.computer_dn2name(
            udm, obj.class_share_file_server
        )
        kwargs["educational_servers"] = [
            await cls.computer_dn2name(udm, dn) for dn in obj.educational_servers
        ]
        kwargs["home_share_file_server"] = await cls.computer_dn2name(
            udm, obj.home_share_file_server
        )
        return kwargs

    @classmethod
    async def computer_dn2name(cls, udm: UDM, dn: str) -> Optional[str]:
        if not dn:
            return None
        if dn not in cls._dn2name:
            obj = await udm.obj_by_dn(dn)
            cls._dn2name[dn] = obj.props.name
        return cls._dn2name[dn]


@router.get("/", response_model=List[SchoolModel])
async def search(
    request: Request,
    name_filter: str = Query(
        None,
        alias="name",
        description="List schools with this name. '*' can be used for an "
        "inexact search. (optional)",
        title="name",
    ),
    logger: logging.Logger = Depends(get_logger),
    udm: UDM = Depends(udm_ctx),
) -> List[SchoolModel]:
    """
    Search for schools (OUs).

    The **name** parameter is optional and supports the use of ``*`` for wildcard
    searches. No other properties can be used to filter.
    """
    logger.debug("Searching for schools with: name_filter=%r", name_filter)
    if name_filter:
        filter_str = "ou={}".format(
            escape_filter_chars(name_filter).replace(r"\2a", "*")
        )
    else:
        filter_str = None
    schools = await School.get_all(udm, filter_str=filter_str)
    return [
        await SchoolModel.from_lib_model(school, request, udm) for school in schools
    ]


@router.get("/{school_name}", response_model=SchoolModel)
async def get(
    request: Request,
    school_name: str = Query(
        None, alias="name", description="School (OU) with this name.", title="name",
    ),
    udm: UDM = Depends(udm_ctx),
) -> SchoolModel:
    """
    Fetch a specific school (OU).

    - **name**: name of the school (required)
    """
    school = await School.from_dn(School(name=school_name).dn, None, udm)
    return await SchoolModel.from_lib_model(school, request, udm)


# @router.post("/", status_code=HTTP_201_CREATED, response_model=SchoolModel)
# async def create(school: SchoolCreateModel) -> SchoolModel:
#     """
#     **Not implemented yet!**
#     """
#     raise HTTPException(
#         status_code=HTTP_405_METHOD_NOT_ALLOWED, detail="NotImplementedError"
#     )
