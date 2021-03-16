from typing import Any, Dict

import requests

from ucsschool.importer.models.import_user import ImportUser

from .constants import OPA_URL


def check_policy(
    policy: str, token: str, request: Dict[str, Any], target: Dict[str, Any]
) -> Any:
    response = requests.post(
        f"{OPA_URL}{policy}",
        json={
            "input": {
                "token": token,
                "request": request,
                "target": target,
            },
        },
    )
    if response.status_code != 200:
        return False
    return response.json().get("result", False)


def check_policy_true(
    policy: str, token: str, request: Dict[str, Any], target: Dict[str, Any]
) -> bool:
    response_data = check_policy(policy, token, request, target)
    return response_data is True


def import_user_to_opa(user: ImportUser) -> Dict[str, Any]:
    user_dict = user.to_dict()
    return {
        "username": user_dict.get("name", ""),
        "schools": user_dict.get("schools", []),
        "roles": user_dict.get("ucsschool_roles", []),
    }
