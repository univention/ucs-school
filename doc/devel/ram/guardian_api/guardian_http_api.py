"""
See
https://git.knut.univention.de/univention/ucsschool/-/blob/jkoeniger/concept-ram-proposal/doc/devel/ram/concept_proposal.md
for the requirement identifiers.
"""
import json

from fastapi import FastAPI
from fastapi.routing import APIRoute

from .authz import router as authorization_router
from .data import router as data_router

app = FastAPI(
    title="Guardian REST API",
    description="The Guardian REST API provides endpoints for the use"
    " and management of the Guardian software component.\n"
    "See [management api](http://127.0.0.1:8000/v1/management/docs)"
    " and [authorization api](http://127.0.0.1:8000/v1/authorization/docs)",
    version="0.0.1",
)

app_v1 = FastAPI()
app.mount("/v1", app_v1)

app_data = FastAPI(title="Guardian Management REST API")
app_authorization = FastAPI(title="Guardian Authorization REST API")

app_v1.mount("/management", app_data)
app_v1.mount("/authorization", app_authorization)

app_data.include_router(data_router)
# Roles management is no longer part of the REST API
# app_data.include_router(roles_router)
app_authorization.include_router(authorization_router)


def use_route_names_as_operation_ids(app_to_modify: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    for route in app_to_modify.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


use_route_names_as_operation_ids(app_authorization)
use_route_names_as_operation_ids(app_data)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("endpoint", choices=["management", "authz"])

    args = parser.parse_args()

    if args.endpoint == "management":
        print(json.dumps(app_data.openapi(), indent=4))
    elif args.endpoint == "authz":
        print(json.dumps(app_authorization.openapi(), indent=4))
    else:
        print(f"{args.endpoint} is no valid endpoint.")
