from typing import Union

from ldap.dn import escape_dn_chars, explode_dn  # TODO: use ldap3
from pydantic import HttpUrl
from starlette.datastructures import URL
from starlette.requests import Request

from ucsschool.lib.models.base import NoObject
from ucsschool.lib.models.utils import env_or_ucr
from udm_rest_client import UDM

from .ldap_access import udm_kwargs


def name_from_dn(dn):
    return explode_dn(dn, 1)[0]


def url_to_name(request: Request, obj_type: str, url: Union[str, HttpUrl]) -> str:
    if not url:
        return url
    if isinstance(url, HttpUrl):
        url = str(url)
    if url.startswith("https"):
        raise RuntimeError(f"Missed unscheme_and_unquote() for URL {url!r}.")
    no_object_exception = NoObject(
        f"Could not find object of type {obj_type!r} with URL {url!r}."
    )
    if obj_type == "school":
        name = URL(url).path.rstrip("/").split("/")[-1]
        calc_url = request.url_for("get", school_name=name)
        if url != calc_url:
            raise no_object_exception
    elif obj_type == "user":
        name = URL(url).path.rstrip("/").split("/")[-1]
        calc_url = request.url_for("get", username=name)
        if url != calc_url:
            raise no_object_exception
    elif obj_type == "role":
        name = URL(url).path.rstrip("/").split("/")[-1]
        calc_url = request.url_for("get", role_name=name)
        if url != calc_url:
            raise no_object_exception
    else:
        raise no_object_exception
    return name


async def url_to_dn(request: Request, obj_type: str, url: str) -> str:
    """
    Guess object ID (e.g. school name or username) from last part of URL, then
    optionally get object from UDM HTTP API to retrieve DN.
    """
    name = url_to_name(request, obj_type, url)
    if obj_type == "school":
        return f"ou={name},{env_or_ucr('ldap/base')}"
    elif obj_type == "user":
        async with UDM(**await udm_kwargs()) as udm:
            filter_s = f"(&(objectClass=ucsschoolType)(uid={escape_dn_chars(name)}))"
            async for obj in udm.get("users/user").search(
                filter_s, base=env_or_ucr("ldap/base")
            ):
                return obj.dn
            else:
                raise NoObject(
                    f"Could not find object of type {obj_type!r} with URL {url!r}."
                )
    raise NotImplementedError(f"Don't know how to create DN for obj_type {obj_type!r}.")
