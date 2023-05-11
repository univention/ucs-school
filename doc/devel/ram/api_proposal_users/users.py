from typing import List, Optional, Union

from authentication import get_username
from constants import other_common_responses, responses_authc
from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from models import (
    CreateUserModel,
    CreateUserResponseModel,
    DetailException,
    MultiUserResponse,
    PatchUser,
    SchoolUserRole,
    UserDetailResponseModel,
    UserListResponseModel,
    ValidationException,
)

router = APIRouter(
    tags=["users"],
    responses=responses_authc,
)


@router.get(
    "/users/{username}",
    response_model=UserDetailResponseModel,
    responses={
        403: responses_authc[403],  # get_username, get_authz_user (handling None's)
        404: other_common_responses[404],
        422: {"model": Union[ValidationException, DetailException]},
    },
)
async def get_user_detail(
    username: str,
    request: Request,
    login_id: str = Depends(get_username),
) -> UserDetailResponseModel:
    pass


@router.patch(
    "/users/{username}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: other_common_responses[404],
        403: {
            "model": Union[responses_authc[403].get("model"), DetailException],  # noqa: F821
            "description": (
                f"{responses_authc[403].get('description')} Or if the actor does not"
                " have enough permission to perform the requested modification on the"
                " target."
            ),
        },
        422: {"model": Union[ValidationException, DetailException]},
    },
)
async def patch_user(
    username: str,
    patch_user: PatchUser,
    login_id: str = Depends(get_username),
) -> Response:
    """
    Patch a specific school user.

    **Parameters**

    - **username**: name of the school user (**required**)
    **Request body**: Dictionary of attribute names and values (**required**)
        - firstname: first name
        - lastname: last name
        - name: user name
        - birthday: birthday
        - password: password
        - email: primary mail
        - disabled: disabled
        - expiration_date: expiration date
        - school: primary school
        - schools: list of schools
        - source_uid: source_uid
        - record_uid: record_uid
        - role: role
        - school_classes: mapping of schools to list of classes
        - workgroups: mapping of schools to list of work groups

    The request body is required but none of the attributes are. Only the ones
    to be modified need to be passed.

    **JSON Example**:

        {
            "name": "EXAMPLE_STUDENT",
            "firstname": "EXAMPLE",
            "lastname": "STUDENT",
            "school": "EXAMPLE_SCHOOL",
            "schools": [
                "EXAMPLE_SCHOOL"
            ],
            "role": "student"
            "ucsschool_roles": [
                "student:school:DEMOSCHOOL"
            ],
            "password": "examplepassword",
            "email": "example@email.com",
            "record_uid": "EXAMPLE_RECORD_UID",
            "source_uid": "EXAMPLE_SOURCE_UID",
            "school_classes": {
                "EXAMPLE_SCHOOL": ["CLASS_A"]
            },
            "workgroups": {
                "EXAMPLE_SCHOOL": ["WG_A"]
            },
            "birthday": "YYYY-MM-DD",
            "expiration_date": "YYYY-MM-DD",
            "disabled": false
        }

    """
    pass


@router.delete(
    "/users/{username}",
    status_code=204,
    responses={
        403: {
            "model": Union[responses_authc[403].get("model"), DetailException],  # noqa: F821
            "description": (
                f"{responses_authc[403].get('description')} "
                "Or if the actor does not have enough permission to delete the target."
            ),
        },
        404: {
            "model": Union[other_common_responses[404].get("model"), DetailException],  # noqa: F821
            "description": (
                f"{other_common_responses[404].get('description')} " "Or if the target does not exist."
            ),
        },
    },
)
async def delete_user(
    username: str,
    login_id: str = Depends(get_username),
) -> Response:
    """
    Delete a specific school user.

    **Parameters**

    - **username**: name of the school user (**required**)
    """
    pass


@router.patch(
    "/delete-users",
    status_code=200,
    responses={
        403: {
            "model": Union[responses_authc[403].get("model"), DetailException],  # noqa: F821
            "description": (
                f"{responses_authc[403].get('description')} "
                "Or if the actor does not have enough permission to delete the target."
            ),
        },
        404: {
            "model": Union[other_common_responses[404].get("model"), DetailException],  # noqa: F821
            "description": (
                f"{other_common_responses[404].get('description')} " "Or if none of targets exist."
            ),
        },
    },
)
async def delete_users(
    usernames: List[str],
    login_id: str = Depends(get_username),
) -> MultiUserResponse:
    """
    Delete multiple school users.

    **Parameters**

    - **usernames**: name of the school users (**required**)
    """
    pass


@router.post(
    "/users/",
    status_code=201,
    response_model=CreateUserResponseModel,
    responses={
        403: {
            "model": Union[responses_authc[403].get("model"), DetailException],  # noqa: F821
            "description": (
                f"{responses_authc[403].get('description')} "
                "Or if the actor does not have enough permission to create the target."
            ),
        },
        409: {
            "model": DetailException,
            "description": "If the user already exists (forwarded from Kelvin).",
        },
        422: {"model": Union[ValidationException, DetailException]},
    },
)
async def create_user(
    user_data: CreateUserModel,
    login_id: str = Depends(get_username),
) -> Union[Response, JSONResponse]:
    """
    Create a school user.

    - **firstname**: Given name of the user (**required**)
    - **lastname**: Family name of the user (**required**)
    - **name**: Name of the user (**required** if no schema is provided in the kelvin backend)
    - **school**: School organizational unit the user belongs to (**required**)
    - **school_classes**: School classes the user belongs to (if **role** is student,
     this is required to be non-empty)
    - **email**: The users email address (**mailPrimaryAddress**), used only
        when the email domain is hosted on UCS, not to be confused with the
        contact property **e-mail** (optional)
    - **birthday**: Birthday of user (optional, format: **YYYY-MM-DD**)
    - **password**: user password (optional)
    - **disabled**: whether the user should be created deactivated (optional, default: **false**)
    - **expiry_date**: date of password expiration (optional)

    **JSON Example**:

        {
            "name": "EXAMPLE_STUDENT",
            "firstname": "EXAMPLE",
            "lastname": "STUDENT",
            "school": "DEMOSCHOOL",
            "role": "student",
            "password": "examplepassword",
            "email": "example@email.com",
            "school_classes": ["1a", "2b"],
            "birthday": "2022-09-02",
            "expiry_date": "2023-09-02",
            "disabled": false
        }
    """
    pass


@router.get(
    "/users",
    response_model=List[UserListResponseModel],
    responses={
        422: {"model": Union[ValidationException, DetailException]},
        404: {
            "model": Union[other_common_responses[404].get("model"), DetailException],  # noqa: F821
            "description": (
                f"{other_common_responses[404].get('description')} " "Or if the target does not exist."
            ),
        },
    },
)
async def list_users(
    school: str = Query(description="Name of the school (OU) users must be members of."),
    group: str = Query(
        None,
        description=(
            "Name of school class or work group (in the chosen school), users must be " "members of."
        ),
    ),
    role: SchoolUserRole = Query(
        None,
        description=(
            "Role users must have (one of 'generic_user', 'student', 'teacher', "
            "'school_admin', 'technical_admin')."
        ),
    ),
    source_uid: str = Query(None, description="Source database ID."),
    disabled: bool = Query(None, description="Whether the account is disabled."),
    quick_search: str = Query(
        None,
        description=(
            "Text will be searched for in 'firstname', 'lastname', 'username' and" " 'record_uid'."
        ),
    ),
    inexact_quick_search: Optional[bool] = Query(
        True,
        description=(
            "Asterisks within a quick_earch query will be interpreted as placeholders."
            " If no asterisks are present in the search string an asterisk is added"
            " automatically at the start and at the end of the string."
        ),
    ),
    limit: int = Query(0, description="Maximum number of returned items."),
    login_id: str = Depends(get_username),
) -> List[UserListResponseModel]:
    """
    Fetch list of school users.

    **Parameters (filter the list of returned users)**

    - **school**: name of the school users must be members of (**required**)
    - **class**: name of class in the above school, users must be members of
    - **role**: role users must have (one of ``staff``, ``student``, ``teacher``, ``teacher_and_staff``)
    - **source_uid**: source database ID
    - **disabled**: whether the account is disabled
    - **quick_earch**: text will be searched for in ``lastname``, ``firstname``, ``username`` and
        ``record_uid``
    - **inexact_quick_search**: if ``True`` (default), asterisks within a quick_earch query will be
        interpreted as placeholders. If no asterisks are present in the search string an asterisk is
        added automatically at the start and at the end of the string.
    - **limit**: Maximum number of returned items
    """
    pass
