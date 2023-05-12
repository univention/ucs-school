from typing import Any, Literal, Optional, Type, TypeVar

import humps
from pydantic import BaseModel, Field

BaseModelBoundType = TypeVar("BaseModelBoundType", bound=BaseModel)


def create_example_instance(model_cls: Type[BaseModelBoundType]) -> BaseModelBoundType:
    """Create an example instance from the example attribute fields, works only for non-nested models"""
    schema = model_cls.schema()
    example_data: dict[str, Any] = {}

    # Look into properties, otherwise fall back to the definitions
    for prop, details in schema["properties"].items():
        example_value = details.get("example")
        if example_value is None and details.get("$ref") is not None:
            type_name = details["$ref"].split("/")[-1]
            example_value = schema["definitions"][type_name].get("example")
        elif details.get("type") == "array":
            # type_name = details["items"]["$ref"].split("/")[-1]
            # example_value = [schema["definitions"][type_name].get("example")]
            pass
        if example_value is None:
            raise ValueError(f"Example value for field {prop} is not provided.")
        example_data[prop] = example_value

    return model_cls(**example_data)


class GuardianBaseModel(BaseModel):
    class Config:
        alias_generator = humps.camelize
        allow_population_by_field_name = True


class PaginationMetaData(GuardianBaseModel):
    offset: int
    limit: int
    total_count: int


class GuardianPaginatedResponse(GuardianBaseModel):
    pagination: PaginationMetaData


class GuardianResponseObjectMixin(BaseModel):
    resource_url: str = Field(
        example="https://fqdn/resource_url", description="URL to the Guardian Object"
    )


class NamespaceName(BaseModel):
    """Name of a namespace"""

    __root__: str = Field(example="kelvin-rest-api", regex=r"[a-z][a-z0-9\-]*", min_length=1)


class AppName(BaseModel):
    """Name of an application"""

    __root__: str = Field(example="ucsschool-kelvin-rest-api", regex=r"[a-z][a-z0-9\-]*", min_length=1)


class AppDisplayname(BaseModel):
    """User-friendly display name"""

    __root__: str = Field(example="UCS@school", min_length=1)


class RegoCode(BaseModel):
    """Base64 encoded rego code"""

    __root__: bytes = Field(
        example=b"Y2FwX2NvbmRpdGlvbigidGFyZ2V0SGFzUm9sZSIsIGNvbmRpdGlvbl9kYXRhKSBpZiB7Cgljb25kaXRpb25fZ"
        b"GF0YS5wYXJhbWV0ZXJzLnJvbGUgaW4ge2Uucm9sZSB8CgkJZSA6PSBjb25kaXRpb25fZGF0YS50YXJnZXRfb2x"
        b"kLnJvbGVzW19dCgl9Cn0K"
    )


class NamespaceDisplayname(BaseModel):
    """User-friendly display name"""

    __root__: str = Field(example="UCS@school Kelvin REST API", min_length=1)


class NamespaceMinimal(GuardianBaseModel):
    """A minimal namespace object for requests (e.g. role-capability-mapping)"""

    app_name: AppName
    namespace_name: NamespaceName


class Namespace(NamespaceMinimal):
    """A distinct namespace related to a specific application"""

    namespace_displayname: Optional[NamespaceDisplayname] = Field(default=None)


class NamespaceResponseObject(Namespace, GuardianResponseObjectMixin):
    pass


class ConditionName(GuardianBaseModel):
    __root__: str = Field(
        example="kelvin_kelvin_condition1",
        description="The name of a condition. This name is used as a function name"
        " and has therefore naming requirements (see regex in schema).",
        regex=r"[a-zA-Z][a-zA-Z0-9_]*",
        min_length=8,
    )


class ConditionDisplayName(GuardianBaseModel):
    __root__: str = Field(example="Kelvin Condition 1")


class PermissionName(BaseModel):
    __root__: str = Field(example="reset_password")


class RoleName(BaseModel):
    __root__: str = Field(example="kelvin_admin")


class RoleIdentifier(BaseModel):
    """
    role composite string

    The 'role composite string' identifies a specific Role globally by including
    appName and namespaceName.
    """

    __root__: str = Field(
        example="appName:namespaceName:roleName",
        regex=r"[a-z][a-z0-9\-]:[a-z][a-z0-9\-]:[a-z][a-z0-9\-]",
    )


class RoleDisplayName(BaseModel):
    __root__: str = Field(example="Kelvin Administrator")


class ContextName(GuardianBaseModel):
    __root__: str = Field(example="school_a")


class ContextDisplayName(GuardianBaseModel):
    __root__: str = Field(default=None, example="School A")


class ContextIdentifier(BaseModel):
    """
    context composite string

    The 'context composite string' identifies a specific Context globally by
    including appName and namespaceName.
    """

    __root__: str = Field(
        example="appName:namespaceName:contextName",
        regex=r"[a-z][a-z0-9\-]:[a-z][a-z0-9\-]:[a-z][a-z0-9\-]",
    )


class NamespacesPostRequest(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    namespace_displayname: Optional[NamespaceDisplayname] = Field(None)


class NamespacePostResponse(GuardianBaseModel):
    namespace: NamespaceResponseObject


class NamespacesGetResponse(GuardianBaseModel):
    namespace: NamespaceResponseObject


class NamespacesGetAllResponse(GuardianPaginatedResponse):
    namespaces: list[NamespaceResponseObject]


class NamespacesPatchRequest(BaseModel):
    namespace_displayname: Optional[NamespaceDisplayname]


class NamespacePatchResponse(GuardianBaseModel):
    namespace: NamespaceResponseObject


class RoleMinimal(GuardianBaseModel):
    """Minimal role object for use with requests (e.g., role-capability-mapping)"""

    app_name: AppName
    namespace_name: NamespaceName
    role_name: RoleName


class Role(RoleMinimal):
    role_displayname: Optional[RoleDisplayName] = Field(default=None)


class RoleResponseObject(Role, GuardianResponseObjectMixin):
    role_identifier: RoleIdentifier


class App(GuardianBaseModel):
    """A specific application that will interact with the Guardian"""

    app_name: AppName
    app_displayname: Optional[AppDisplayname] = Field(default=None)
    app_admin: Optional[Role]


class AppResponseObject(App, GuardianResponseObjectMixin):
    pass


class RolesPostRequest(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    role_name: RoleName
    role_displayname: Optional[RoleDisplayName] = Field(default=None)


class RolesPatchRequest(GuardianBaseModel):
    role_displayname: Optional[RoleDisplayName] = Field(default=None)


class RolesResponse(GuardianBaseModel):
    role: RoleResponseObject


class RolesGetResponse(GuardianBaseModel):
    role: RoleResponseObject


class RolesGetAllResponse(GuardianPaginatedResponse):
    roles: list[RoleResponseObject]


class ContextPostRequest(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    context_name: ContextName
    context_displayname: Optional[ContextDisplayName]


class ContextPatchRequest(GuardianBaseModel):
    context_displayname: Optional[ContextDisplayName] = Field(default=None, example="School A")


class Context(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    context_name: ContextName
    context_displayname: ContextDisplayName


class ContextResponseObject(Context, GuardianResponseObjectMixin):
    context_identifier: ContextIdentifier


class ContextPostResponse(GuardianBaseModel):
    context: ContextResponseObject


class ContextResponse(GuardianBaseModel):
    context: ContextResponseObject


class ContextGetAllResponse(GuardianPaginatedResponse):
    contexts: list[ContextResponseObject]


class Permission(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    permission_name: PermissionName


class PermissionResponseObject(Permission, GuardianResponseObjectMixin):
    pass


class PermissionPostRequest(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    permission_name: PermissionName


class PermissionPostResponse(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    permission_name: PermissionName


class PermissionsGetResponse(GuardianBaseModel):
    permission: PermissionResponseObject


class PermissionsGetAllResponse(GuardianPaginatedResponse):
    permissions: list[PermissionResponseObject]


class ParameterName(BaseModel):
    """Name of an application"""

    __root__: str = Field(example="roleName", regex=r"[a-z][a-z0-9_]*", min_length=1)

    def __hash__(self):  # make hashable BaseModel subclass
        return hash((type(self),) + tuple(self.__dict__.values()))


class ConditionMinimal(GuardianBaseModel):
    """A condition as it is used in the role-capability-mapping"""

    condition_name: ConditionName
    parameters: dict[ParameterName, str] = Field(example={"parameter1": "value1"})


class ConditionBase(GuardianBaseModel):
    """A condition without the Rego code, which we don't want to expose"""

    app_name: AppName
    namespace_name: NamespaceName
    condition_name: ConditionName
    condition_displayname: ConditionDisplayName
    documentation_string: Optional[str] = Field(
        default=None, example="This is the documentation string for this condition."
    )
    parameter_names: list[ParameterName]


class Condition(ConditionBase):
    """How conditions are actually stored"""

    rego_code: RegoCode


class ConditionResponseObject(ConditionBase, GuardianResponseObjectMixin):
    pass


class Capability(GuardianBaseModel):
    role: Role = Field(example=create_example_instance(Role))
    conditions: list[ConditionMinimal] = Field(example=[create_example_instance(ConditionMinimal)])
    relation: Literal["AND", "OR"] = Field(example="AND")
    permissions: list[Permission] = Field(example=[create_example_instance(Permission)])


class RoleCapabilityMapping(GuardianBaseModel):
    mappings: list[Capability] = Field(example=[create_example_instance(Capability)])


class RoleCapabilityMappingNamespaced(RoleCapabilityMapping):
    namespace: Namespace


class ConditionPostRequest(GuardianBaseModel):
    condition_displayname: ConditionDisplayName
    rego_code: RegoCode
    parameter_names: list[ParameterName]
    documentation_string: Optional[str] = Field(
        default=None, description="Optional documentation string for the custom condition."
    )


class ConditionPatchRequest(GuardianBaseModel):
    condition_displayname: Optional[ConditionDisplayName]
    rego_code: Optional[RegoCode]
    parameter_names: Optional[list[ParameterName]]
    documentation_string: Optional[str] = Field(
        default=None, description="Optional documentation string for the custom condition."
    )


class ConditionGetResponse(GuardianBaseModel):
    condition: ConditionResponseObject


class ConditionGetAllResponse(GuardianPaginatedResponse):
    conditions: list[ConditionResponseObject]


class CustomEndpointName(BaseModel):
    """Name of a namespace"""

    __root__: str = Field(example="my-custom-endpoint", regex=r"[a-z][a-z0-9\-]*", min_length=1)


class CustomEndpointMinimal(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    endpoint_name: CustomEndpointName


class CustomEndpoint(CustomEndpointMinimal):
    rego_code: RegoCode


class CustomEndpointPostRequest(GuardianBaseModel):
    custom_endpoint: CustomEndpointMinimal


class CustomEndpointPatchRequest(GuardianBaseModel):
    rego_code: RegoCode


class CustomEndpointResponse(GuardianBaseModel):
    custom_endpoint: CustomEndpointMinimal


class GenericError(BaseModel):
    detail: str


class ObjectIdentifier(BaseModel):
    """Identifies an object in an authz check"""

    __root__: str = Field(example="6f8be20a-d463-454d-8ccf-bf6227437473", min_length=1)


class Target(GuardianBaseModel):
    """A target has a current state and an updated state and field which identify the object"""

    id: ObjectIdentifier
    current_state: Optional[dict[str, Any]]
    updated_state: Optional[dict[str, Any]]


class Actor(GuardianBaseModel):
    """Representation of an actor. An actor must contain a roles attribute."""

    id: ObjectIdentifier
    attributes: dict[str, Any]


class AuthzPermissionsCheckPostRequest(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    actor: Actor
    targets: Optional[list[Target]]
    permissions_to_check: list[Permission]
    contexts: Optional[list[Context]]
    extra_request_data: dict[str, Any]


class PermissionCheckResult(GuardianBaseModel):
    target_id: str
    actor_has_permissions: bool


class AuthzPermissionsCheckPostResponse(GuardianBaseModel):
    app_name: AppName
    namespace_name: NamespaceName
    permission_check_results: list[PermissionCheckResult]
    actor_has_all_permissions: bool


class PermissionResult(GuardianBaseModel):
    """
    Represents the answer to the question:
    What permissions are available for 'actor' with respect to 'target'
    """

    target_id: ObjectIdentifier
    permissions: list[Permission]


class AuthzPermissionsPostRequest(GuardianBaseModel):
    namespaces: Optional[list[NamespaceMinimal]] = Field(default=None)
    actor: Actor
    targets: Optional[list[Target]]
    contexts: Optional[list[Context]]


class AuthzPermissionsPostResponse(GuardianBaseModel):
    actor_id: ObjectIdentifier
    general_permissions: list[Permission]
    target_permissions: list[PermissionResult]


class AppsPostRequest(GuardianBaseModel):
    app_name: AppName
    app_displayname: AppDisplayname


class AppsPatchRequest(GuardianBaseModel):
    app_displayname: AppDisplayname


class AppResponse(GuardianBaseModel):
    app: AppResponseObject


class AppsGetAllResponse(GuardianPaginatedResponse):
    apps: list[AppResponseObject]
