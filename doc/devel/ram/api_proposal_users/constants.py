from typing import Any, Dict, Union

from models import DetailException, ValidationException

# default responses for endpoints that require authentication (`get_username` fixture)
responses_authc: Dict[int, Dict[str, Any]] = {
    # every endpoint that requires authentication (get_username fixture)
    401: {
        "model": DetailException,
        "description": "If the request does not provide authentication.",
    },
    # every endpoint that requires authentication (get_username fixture)
    403: {
        "model": Union[DetailException, None],
        "description": (
            "If Keycloak does not grant a token to the logged in user (empty response"
            " body). Or if the logged in user does not exist."
        ),
    },
}

other_common_responses: Dict[int, Dict[str, Any]] = {
    # whenever get_access_or_raise is used
    404: {
        "model": DetailException,
        "description": "If the actor has no access at all to the target.",
    },
    # when custom validation errors might be raised (apart from the default FastAPI ones)
    422: {
        "model": Union[ValidationException, DetailException],
        "description": "Validation error.",
    },
    409: {
        "model": DetailException,
        "description": "If the object already exists (forwarded from Kelvin).",
    },
}
