from typing import Dict, List, Union

from authentication import get_username
from constants import responses_authc
from fastapi import APIRouter, Depends
from models import PageAddViewResponseModel, PageListViewResponseModel

router = APIRouter(
    prefix="/pageconf",
    tags=["pages"],
    responses=responses_authc,
)
_roles_cache: List[Dict[str, str]] = []


@router.get(
    "/add-view",
    response_model=PageAddViewResponseModel,
    responses={
        403: {
            "model": Union[responses_authc[403].get("model"), None],  # noqa: F821
            "description": (
                f"{responses_authc[403].get('description')} "
                "Or if the logged in user is not the same as the requested user."
            ),
        }  # get_username, get_authz_user (handling None's)
    },
)
async def get_add_view_settings(
    login_id: str = Depends(get_username),
) -> PageAddViewResponseModel:
    """Fetch settings of add-view page for current actor."""
    pass


@router.get(
    "/list-view",
    response_model=PageListViewResponseModel,
    responses={
        403: {
            "model": Union[responses_authc[403].get("model"), None],  # noqa: F821
            "description": (
                f"{responses_authc[403].get('description')} "
                "Or if the logged in user is not the same as the requested user."
            ),
        }
    },
)
async def get_list_view_settings(
    login_id: str = Depends(get_username),
) -> PageListViewResponseModel:
    """Fetch settings of list-view page for current actor."""
    pass
