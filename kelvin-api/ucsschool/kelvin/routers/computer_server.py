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

# from typing import List
#
# from fastapi import APIRouter, HTTPException, Query
# from pydantic import (
#     BaseModel,
#     Field,
#     HttpUrl,
#     Protocol,
#     PydanticValueError,
#     SecretStr,
#     StrBytes,
#     ValidationError,
#     validator,
# )
# from starlette.status import (
#     HTTP_200_OK,
#     HTTP_201_CREATED,
#     HTTP_204_NO_CONTENT,
#     HTTP_400_BAD_REQUEST,
#     HTTP_401_UNAUTHORIZED,
#     HTTP_404_NOT_FOUND,
# )
#
# from ucsschool.lib.models.computer import SchoolDC, SchoolDCSlave
#
# from ..utils import get_logger
#
# router = APIRouter()
#
#
# class ComputerServerModel(UcsSchoolBaseModel):
#     dn: str = None
#     name: str
#     school: HttpUrl
#     description: str = None
#
#
# @router.get("/")
# async def search(
#     name_filter: str = Query(
#         None,
#         title="List servers with this name. '*' can be used for an inexact search.",
#         min_length=3,
#     ),
#     school_filter: str = Query(
#         None,
#         title="List only servers in school with this name (not URL). ",
#         min_length=3,
#     ),
# ) -> List[ComputerServerModel]:
#     logger.debug(
#         "Searching for servers with: name_filter=%r school_filter=%r",
#         name_filter,
#         school_filter,
#     )
#     return [
#         ComputerServerModel(name="10a", school="https://foo.bar/schools/gsmitte"),
#         ComputerServerModel(name="8b", school="https://foo.bar/schools/gsmitte"),
#     ]
#
#
# @router.get("/{name}")
# async def get(name: str, school: str) -> ComputerServerModel:
#     return ComputerServerModel(name=name, school=f"https://foo.bar/schools/{school}")
#
#
# @router.post("/", status_code=HTTP_201_CREATED)
# async def create(server: ComputerServerModel) -> ComputerServerModel:
#     if server.name == "alsoerror":
#         raise HTTPException(
#             status_code=HTTP_400_BAD_REQUEST, detail="Invalid server name."
#         )
#     server.dn = "cn=foo,cn=computers,dc=test"
#     return server
#
#
# @router.patch("/{name}", status_code=HTTP_200_OK)
# async def partial_update(name: str, server: ComputerServerModel) -> ComputerServerModel:
#     if name != server.name:
#         logger.info("Renaming server from %r to %r.", name, server.name)
#     return server
#
#
# @router.put("/{name}", status_code=HTTP_200_OK)
# async def complete_update(
#     name: str, server: ComputerServerModel
# ) -> ComputerServerModel:
#     if name != server.name:
#         logger.info("Renaming server from %r to %r.", name, server.name)
#     return server
#
#
# @router.delete("/{name}", status_code=HTTP_204_NO_CONTENT)
# async def delete(name: str, request: Request) -> None:
#     async with UDM(**await udm_kwargs()) as udm:
#         sc = await get_lib_obj(udm, SchoolDC, name, None)
#         if await sc.exists(udm):
#             await sc.remove(udm)
#         else:
#             raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="TODO")
#     return None
