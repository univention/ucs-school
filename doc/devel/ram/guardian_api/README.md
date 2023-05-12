# Guardian HTTP API proposal

This API was created in the context of the Guardian ([see concept](https://git.knut.univention.de/univention/ucsschool/-/blob/jkoeniger/concept-ram-proposal/doc/devel/ram/concept_proposal.md)) and Issue [ucsschool#1006](https://git.knut.univention.de/univention/ucsschool/-/issues/1006).
The definition is done by creating a minimal application with python and the packages fastAPI and pydantic.
From that minimal application, the openapi JSON files can be generated.

## Structure

The Guardian HTTP API is split in two parts: The authorization API ([authz.py](authz.py)) and the management API ([data.py](data.py)).
Pydantic models used within the endpoint specifications for both APIs are defined in [models.py](models.py).

## Installing requirements and running the minimal app

The minimum python version needed to run the application is `3.9`, as `typing.Annotated` is used.

```console
pip install -r guardian_api/requirements
uvicorn guardian_api.guardian_http_api:app
```

## Generate/Update openapi JSON files

```console
python -m guardian_api.guardian_http_api management > guardian_api/openapi_management.json
python -m guardian_api.guardian_http_api authz > guardian_api/openapi_authz.json
```

## Generate python client

One possibility to generate the python client is the following:
First Install the [openapi-generator](https://openapi-generator.tech/docs/installation)
Then run these commands to generate the python client and its documentation:

```console
openapi-generator-cli generate -i guardian_api/openapi_authz.json -g python-nextgen -o guardian_authorization_client/ --library asyncio --additional-properties=packageName=guardian_authorization_client,generateSourceCodeOnly=true
openapi-generator-cli generate -i guardian_api/openapi_management.json -g python-nextgen -o guardian_management_client/ --library asyncio --additional-properties=packageName=guardian_management_client,generateSourceCodeOnly=true
```
