from ..utils import get_logger
from fastapi import APIRouter, HTTPException, Query
from pydantic import (
    BaseModel,
    Protocol,
    PydanticValueError,
    Schema,
    SecretStr,
    StrBytes,
    UrlStr,
    ValidationError,
    validator,
)
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)
from typing import List
from ucsschool.lib.models.user import Staff, Student, Teacher, TeachersAndStaff, User

logger = get_logger(__name__)
router = APIRouter()


class UserModel(BaseModel):
    dn: str = None
    name: str
    school: UrlStr
    ucsschool_roles: List[str] = Schema(
        None, title="Roles of this object. Don't change if unsure."
    )


@router.get("/")
async def search(
    name_filer: str = Query(
        None,
        title="List users with this name. '*' can be used for an inexact search.",
        min_length=3,
    ),
    school_filter: str = Query(
        None, title="List only users in school with this name (not URL). ", min_length=3
    ),
) -> List[UserModel]:
    logger.debug(
        "Searching for users with: name_filer=%r school_filter=%r",
        name_filer,
        school_filter,
    )
    return [
        UserModel(name="10a", school="https://foo.bar/schools/gsmitte"),
        UserModel(name="8b", school="https://foo.bar/schools/gsmitte"),
    ]


@router.get("/{username}")
async def get(username: str) -> UserModel:
    return UserModel(name=username, school=f"https://foo.bar/schools/foo")


@router.post("/", status_code=HTTP_201_CREATED)
async def create(user: UserModel) -> UserModel:
    if user.name == "alsoerror":
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Invalid user name."
        )
    user.dn = "cn=foo-bar,cn=users,dc=test"
    return user


@router.patch("/{username}", status_code=HTTP_200_OK)
async def partial_update(username: str, user: UserModel) -> UserModel:
    if username != user.name:
        logger.info("Renaming user from %r to %r.", username, user.name)
    return user


@router.put("/{username}", status_code=HTTP_200_OK)
async def complete_update(username: str, user: UserModel) -> UserModel:
    if username != user.name:
        logger.info("Renaming user from %r to %r.", username, user.name)
    return user
