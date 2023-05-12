"""Authorization endpoints"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from .models import (
    AuthzPermissionsCheckPostRequest,
    AuthzPermissionsCheckPostResponse,
    AuthzPermissionsPostRequest,
    AuthzPermissionsPostResponse,
    BaseModel,
    GuardianBaseModel,
)

http_bearer_scheme = HTTPBearer()
router = APIRouter(tags=["Authorization"])


# C8: Permission checks
# NOTE: This endpoint should be configurable to require authentication as well!
@router.post("/permissions/check")
async def check_permissions(
    permissions_check_request: AuthzPermissionsCheckPostRequest,
) -> AuthzPermissionsCheckPostResponse:
    """Check one or more permissions for an actor"""
    pass


# C9: List permissions
# NOTE: This endpoint should be configurable to require authentication as well!
@router.post("/permissions")
async def get_permissions(
    permissions_fetch_request: AuthzPermissionsPostRequest,
) -> AuthzPermissionsPostResponse:
    pass


@router.post("/permissions/check/with-lookup")
async def get_permissions_with_information_retrieval(
    permissions_get_request: AuthzPermissionsPostRequest,
    token: Annotated[str, Depends(http_bearer_scheme)],
) -> AuthzPermissionsCheckPostResponse:
    pass


@router.post("/permissions/with-lookup")
async def check_permissions_with_information_retrieval(
    permissions_get_request: AuthzPermissionsPostRequest,
    token: Annotated[str, Depends(http_bearer_scheme)],
) -> AuthzPermissionsPostResponse:
    """Check permissions"""
    pass


@router.post("/permissions/custom/{app_name}/{namespace_name}/{endpoint_name}")
async def custom_permissions_endpoint(
    app_name: str, namespace_name: str, endpoint_name: str, custom_endpoint_request: GuardianBaseModel
) -> BaseModel:
    pass
