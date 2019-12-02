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
# from ucsschool.lib.models.computer import IPComputer, MacComputer, SchoolComputer, WindowsComputer
#
# from ..utils import get_logger
#
# logger = get_logger(__name__)
# router = APIRouter()
#
#
# class ComputerClientModel(UcsSchoolBaseModel):
#     dn: str = None
#     name: str
#     school: HttpUrl
#     description: str = None
#     ucsschool_roles: List[str] = Field(
#         None, title="Roles of this object. Don't change if unsure."
#     )
#
#
# @router.get("/")
# async def search(
#     name_filer: str = Query(
#         None,
#         title="List clients with this name. '*' can be used for an inexact search.",
#         min_length=3,
#     ),
#     school_filter: str = Query(
#         None,
#         title="List only clients in school with this name (not URL). ",
#         min_length=3,
#     ),
# ) -> List[ComputerClientModel]:
#     logger.debug(
#         "Searching for clients with: name_filer=%r school_filter=%r",
#         name_filer,
#         school_filter,
#     )
#     return [
#         ComputerClientModel(name="10a", school="https://foo.bar/schools/gsmitte"),
#         ComputerClientModel(name="8b", school="https://foo.bar/schools/gsmitte"),
#     ]
#
#
# @router.get("/{name}")
# async def get(name: str, school: str) -> ComputerClientModel:
#     return ComputerClientModel(name=name, school=f"https://foo.bar/schools/{school}")
#
#
# @router.post("/", status_code=HTTP_201_CREATED)
# async def create(client: ComputerClientModel) -> ComputerClientModel:
#     if client.name == "alsoerror":
#         raise HTTPException(
#             status_code=HTTP_400_BAD_REQUEST, detail="Invalid computer client name."
#         )
#     client.dn = "cn=foo,cn=computers,dc=test"
#     return client
#
#
# @router.patch("/{name}", status_code=HTTP_200_OK)
# async def partial_update(name: str, client: ComputerClientModel) -> ComputerClientModel:
#     if name != client.name:
#         logger.info("Renaming client from %r to %r.", name, client.name)
#     return client
#
#
# @router.put("/{name}", status_code=HTTP_200_OK)
# async def complete_update(
#     name: str, client: ComputerClientModel
# ) -> ComputerClientModel:
#     if name != client.name:
#         logger.info("Renaming client from %r to %r.", name, client.name)
#     return client
#
#
# @router.delete("/{name}", status_code=HTTP_204_NO_CONTENT)
# async def delete(name: str, request: Request) -> None:
#     async with UDM(**await udm_kwargs()) as udm:
#         sc = await get_lib_obj(udm, SchoolComputer, name, None)
#         if await sc.exists(udm):
#             await sc.remove(udm)
#         else:
#             raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="TODO")
#     return None
