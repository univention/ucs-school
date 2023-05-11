from dataclasses import dataclass
from typing import List, TypedDict

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi_dynamic_auth.auth_management import AuthManager, IdP
from fastapi_dynamic_auth.strategies import OAuth2Strategy, OAuth2Token

base_url: str = "https://school.test"

auth_manager = AuthManager()
auth_manager.tags["ucs"] = "UCS"
auth_manager.auth_strategies["oauth2"] = OAuth2Strategy
auth_manager.idps["ucs"] = IdP(
    strategy="oauth2",
    settings={
        "jwk_url": f"{base_url}/protocol/openid-connect/certs",
        "audience": "ucs_keycloak_audience",
        "issuer": base_url,
    },
)
auth_manager.tag_idp_mapping["ucs"].add("ucs")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_username(
    # just for getting the form in Swagger UI and adding the header to all requests
    token: str = Depends(oauth2_scheme),
    auth_entity: OAuth2Token = Depends(auth_manager.get_auth_dependency_for_tag("ucs", OAuth2Token)),
) -> str:
    return auth_entity.sub.split(":")[-1]


def get_token(username: str, password: str, client_id: str = "school-ui-users-dev") -> str:
    pass


class AuthzUserDict(TypedDict):
    name: str
    school: str
    schools: List[str]
    ucsschool_roles: List[str]


@dataclass(frozen=True)
class AuthzUser:
    name: str
    school: str
    schools: frozenset[str]
    ucsschool_roles: frozenset[str]

    def json(self) -> AuthzUserDict:
        return {
            "name": self.name,
            "school": self.school,
            "schools": list(self.schools),
            "ucsschool_roles": list(self.ucsschool_roles),
        }
