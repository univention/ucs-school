"""CRUD operations on Guardian data"""


from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer

from .models import (
    AppResponse,
    AppsGetAllResponse,
    AppsPatchRequest,
    AppsPostRequest,
    ConditionGetAllResponse,
    ConditionGetResponse,
    ConditionPatchRequest,
    ConditionPostRequest,
    ContextGetAllResponse,
    ContextPostRequest,
    ContextResponse,
    CustomEndpointPatchRequest,
    CustomEndpointPostRequest,
    CustomEndpointResponse,
    GenericError,
    NamespacePatchResponse,
    NamespacePostResponse,
    NamespacesGetAllResponse,
    NamespacesGetResponse,
    NamespacesPatchRequest,
    NamespacesPostRequest,
    PermissionPostRequest,
    PermissionPostResponse,
    PermissionsGetAllResponse,
    PermissionsGetResponse,
    RoleCapabilityMapping,
    RoleCapabilityMappingNamespaced,
    RolesGetAllResponse,
    RolesPatchRequest,
    RolesPostRequest,
    RolesResponse,
)

http_bearer_scheme = HTTPBearer()
router = APIRouter(tags=["Guardian Data Management"], dependencies=[Depends(http_bearer_scheme)])


@router.post("/apps/register")
def register_app(apps_register_post_request: AppsPostRequest) -> AppResponse:
    # This endpoint is only authorized for Guardian superadmins.
    # Intended to be used during join scripts.
    # This will also create an app-admin as a side effect.
    pass


@router.post("/apps")
def create_app(apps_post_request: AppsPostRequest) -> AppResponse:
    # This endpoint is only authorized for Guardian superusers.
    # Intended to be used during join scripts.
    pass


@router.get("/apps")
def get_all_apps(offset: int = 0, limit: int = 1000) -> AppsGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/apps/{app_name}")
def get_app(app_name: str) -> AppResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.patch("/apps/{app_name}")
def update_app(app_name: str, apps_patch_request: AppsPatchRequest) -> AppResponse:
    # Only for Guardian superusers and app admins.
    pass


# TODO pagination (offset pagination) via query parameter or header
# C1, C2 and D1: Register a namespace
@router.post(
    "/namespaces",
    responses={
        409: {
            "model": GenericError,
            "description": "Status code 409 is returned when the namespace already exist.",
        },
    },
)
async def create_namespace(
    namespace_post_request: NamespacesPostRequest, request: Request
) -> NamespacePostResponse:
    """Register a namespace"""
    # Only for Guardian superusers and app admins.
    # App admin must match the app they're trying to create a namespace for.
    pass


# C1 and D1: Update a namespace
@router.patch("/namespaces/{app_name}/{namespace_name}")
async def update_namespace(
    app_name: str, namespace_name: str, namespace_patch_request: NamespacesPatchRequest, request: Request
) -> NamespacePatchResponse:
    """Update a namespace. Only the displayname can be updated."""
    # Only for Guardian superusers and app admins.
    pass


# C1 and D1: Get a namespace
@router.get("/namespaces/{app_name}/{namespace_name}")
async def get_namespace(app_name: str, namespace_name: str, request: Request) -> NamespacesGetResponse:
    """Get information about a namespace"""
    # Any authenticated user/service can access this endpoint.
    pass


# C1 and D3: Get multiple namespaces
@router.get("/namespaces/{app_name}")
async def get_namespaces_by_app_name(
    app_name: str, offset: int = 0, limit: int = 1000
) -> NamespacesGetAllResponse:
    """Get information about all namespace"""
    # Any authenticated user/service can access this endpoint.
    pass


# C1 and D3: Get multiple namespaces
@router.get("/namespaces")
async def get_all_namespaces(offset: int = 0, limit: int = 1000) -> NamespacesGetAllResponse:
    """Get information about all namespace"""
    # Any authenticated user/service can access this endpoint.
    pass


# C3 and D1: Register a role
@router.post(
    "/roles",
    responses={
        409: {
            "model": GenericError,
            "description": "Status code 409 is returned when "
            "the role within the namespace already exists.",
        },
    },
)
async def create_role(roles_post_request: RolesPostRequest, request: Request) -> RolesResponse:
    """Register a role within a namespace"""
    # Only for Guardian superusers and app admins.
    # App admin must match the app they're trying to create a role for.
    pass


# D1: Read multiple roles
@router.get("/roles/{app_name}/{namespace_name}")
async def get_roles_by_namespace(
    app_name: str, namespace_name: str, offset: int = 0, limit: int = 1000
) -> RolesGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


# D1/D3: Read multiple roles
@router.get("/roles/{app_name}")
async def get_roles_by_app_name(
    app_name: str, offset: int = 0, limit: int = 1000
) -> RolesGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


# D1: Read multiple roles
@router.get("/roles")
async def get_roles(
    app_name: str, namespace_name: str, offset: int = 0, limit: int = 1000
) -> RolesGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


# D1: Read a single role
@router.get("/roles/{app_name}/{namespace_name}/{role_name}")
async def get_role(
    app_name: str,
    namespace_name: str,
    role_name: str,
) -> RolesResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.patch("/roles/{app_name}/{namespace_name}/{role_name}")
async def update_role(
    app_name: str,
    namespace_name: str,
    role_name: str,
    roles_patch_request: RolesPatchRequest,
    request: Request,
) -> RolesResponse:
    # Only for Guardian superusers and app admins.
    pass


# C4 / D1: Contexts
@router.post(
    "/contexts",
    responses={
        409: {
            "model": GenericError,
            "description": "Status code 409 is returned when "
            "the context within the namespace already exists.",
        },
    },
)
async def create_context(context_post_request: ContextPostRequest) -> ContextResponse:
    # Only for Guardian superusers and app admins.
    # App admin must match the app they're trying to create a context for.
    pass


@router.patch("/contexts/{app_name}/{namespace_name}/{context_name}")
async def update_context(app_name: str, namespace_name: str, context_name: str) -> ContextResponse:
    # Only for Guardian superusers and app admins.
    pass


@router.get("/contexts/{app_name}/{namespace_name}/{context_name}")
async def get_context(app_name: str, namespace_name: str, context_name: str) -> ContextResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/contexts/{app_name}/{namespace_name}")
async def get_all_contexts_by_namespace(
    app_name: str, namespace_name: str, offset: int = 0, limit: int = 1000
) -> ContextGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/contexts/{app_name}")
async def get_all_contexts_by_app_name(
    app_name: str, offset: int = 0, limit: int = 1000
) -> ContextGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/contexts/")
async def get_all_contexts(offset: int = 0, limit: int = 1000) -> ContextGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


# C5 and D1: Permissions
@router.post(
    "/permissions",
    responses={
        409: {
            "model": GenericError,
            "description": "Status code 409 is returned when "
            "the permission within the namespace already exists.",
        },
    },
)
async def create_permission(permissions_post_request: PermissionPostRequest) -> PermissionPostResponse:
    # Only for Guardian superusers and app admins.
    # App admin must match the app they're trying to create a namespace for.
    pass


@router.get("/permissions/{app_name}/{namespace_name}/{permission}")
async def get_permission(app_name: str, namespace_name: str, permission: str) -> PermissionsGetResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/permissions/{app_name}/{namespace_name}")
async def get_all_permissions_by_namespace(
    app_name: str, namespace_name: str, offset: int = 0, limit: int = 1000
) -> PermissionsGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/permissions/{app_name}")
async def get_all_permissions_by_app_name(
    app_name: str, offset: int = 0, limit: int = 1000
) -> PermissionsGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/permissions")
async def get_all_permissions(offset: int = 0, limit: int = 1000) -> PermissionsGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


# D1
@router.put("/role-capability-mapping")
async def update_role_capability_mapping(role_capability_mapping: RoleCapabilityMapping):
    # Only a Guardian superuser can access this endpoint
    pass


@router.get("/role-capability-mapping")
async def get_role_capability_mapping() -> RoleCapabilityMapping:
    # Only a Guardian superuser can access this endpoint
    pass


@router.put("/role-capability-mapping/{app_name}/{namespace_name}")
async def update_role_capability_mapping_for_namespace(
    app_name: str, namespace_name: str, role_capability_mapping: RoleCapabilityMapping
):
    # Only for Guardian superusers and app admins.
    # App admin must match the app where they're updating the role-capabilty-mapping.
    pass


@router.get("/role-capability-mapping/{app_name}/{namespace_name}")
async def get_role_capability_mapping_for_namespace(
    app_name: str,
    namespace_name: str,
) -> RoleCapabilityMappingNamespaced:
    # Only for Guardian superusers and app admins.
    # App admin must match the app where they're getting the role-capabilty-mapping.
    pass


@router.delete("/role-capability-mapping/{app_name}/{namespace_name}")
async def delete_role_capability_mapping_for_namespace(
    app_name: str,
    namespace_name: str,
) -> RoleCapabilityMappingNamespaced:
    # Only for Guardian superusers and app admins.
    # App admin must match the app where they're deleting the role-capabilty-mapping.
    pass


# C6: Custom condition
@router.post("/conditions")
async def create_condition(condition_post_request: ConditionPostRequest) -> ConditionGetResponse:
    # Only for Guardian superusers and app admins.
    # App admin must match the app they're trying to create a condition for.
    pass


@router.patch("/conditions/{app_name}/{namespace_name}/{condition_name}")
async def update_condition(
    app_name: str,
    namespace_name: str,
    condition_name: str,
    condition_patch_request: ConditionPatchRequest,
) -> ConditionGetResponse:
    # Only for Guardian superusers and app admins.
    # App admin must match the app where they're trying to update a condition.
    pass


@router.get("/conditions/{app_name}/{namespace_name}/{condition_name}")
async def get_condition(app_name: str, namespace_name: str, condition_name: str) -> ConditionGetResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/conditions/{app_name}/{namespace_name}")
async def get_condition_by_namespace(
    app_name: str, namespace_name: str, offset: int = 0, limit: int = 1000
) -> ConditionGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/conditions/{app_name}")
async def get_condition_by_app_name(
    app_name: str, offset: int = 0, limit: int = 1000
) -> ConditionGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


@router.get("/conditions")
async def get_conditions(offset: int = 0, limit: int = 1000) -> ConditionGetAllResponse:
    # Any authenticated user/service can access this endpoint.
    pass


# C7: Custom Rego code endpoint
@router.post("/custom-endpoints")
async def create_custom_endpoint(
    custom_endpoint_request: CustomEndpointPostRequest,
) -> CustomEndpointResponse:
    # Only for Guardian superusers and app admins.
    # App admin must match the app they're trying to create a custom endpoint for.
    pass


@router.patch("/custom-endpoints/{app_name}/{namespace_name}/{endpoint_name}")
async def update_custom_endpoint(
    app_name: str,
    namespace_name: str,
    endpoint_name: str,
    custom_endpoint_request: CustomEndpointPatchRequest,
) -> CustomEndpointResponse:
    # Only for Guardian superusers and app admins.
    # App admin must match the app where they're trying to update a custom endpoint.
    pass
