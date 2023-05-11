from typing import Any, Dict, List

from authentication import get_username
from constants import responses_authc
from fastapi import APIRouter, Depends, Query
from models import GroupKind

router = APIRouter(
    tags=["groups"],
    responses=responses_authc,
)


@router.get(
    "/{group_kind}",
    response_model=List[Dict[str, Any]],
    responses={
        401: responses_authc[401],  # get_username
        403: responses_authc[403],  # get_username, get_authz_user (handling None's)
    },
)
async def get_groups(
    group_kind: GroupKind,
    school: str = Query(description="Name of the school (OU) groups must be members of."),
    login_id: str = Depends(get_username),
) -> List[Dict[str, Any]]:
    """
    Fetch all groups of a school.

    **Parameters**

    - **school**: name of the school (**required**)
    - **group_kind*: type of the group which is to be returned (**required**).
    """
    pass
