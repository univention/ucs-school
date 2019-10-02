from .constants import LOG_FILE_PATH
from fastapi import HTTPException
from ldap.dn import escape_dn_chars, explode_dn  # TODO: use ldap3
from pydantic import UrlStr
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.status import HTTP_404_NOT_FOUND
from typing import Any, Dict, List, Union
from ucsschool.lib.models.base import NoObject
from ucsschool.lib.models.utils import get_file_handler, get_stream_handler, ucr
from univention.admin.client import Object, UDM
from univention.admin.uexceptions import noObject

import logging
import re
import univention.admin.modules as udm_modules


def enable_ucsschool_lib_debugging():
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("univention").setLevel(logging.DEBUG)
    logger = logging.getLogger("ucsschool")
    logger.setLevel(logging.DEBUG)
    if "ucsschool" not in [h.name for h in logger.handlers]:
        handler = get_stream_handler(logging.DEBUG)
        handler.set_name("ucsschool")
        logger.addHandler(handler)


enable_ucsschool_lib_debugging()
_logger = logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """
    Create logger with name `name` and attach file and stream handlers.
    Call from your module like this `get_logger(__name__)`.

    :param str name: name of logger
    :return: logger instance with handlers attached
    :rtype: logging.Logger
    """
    logger = logging.getLogger(name)
    if "kelvin-api" not in [h.name for h in logger.handlers]:
        logger.setLevel(logging.DEBUG)
        handler = get_stream_handler(logging.DEBUG)
        handler.set_name("kelvin-api")
        logger.addHandler(handler)
        handler = get_file_handler(logging.DEBUG, LOG_FILE_PATH)
        handler.set_name("kelvin-api")
        logger.addHandler(handler)
    return logger


def get_lo_udm():
    _lo_kwargs = dict(
        uri=udm_modules.ConnectionData.uri(),
        username=udm_modules.ConnectionData.ldap_machine_account_username(),
        password=udm_modules.ConnectionData.machine_password(),
    )
    # print(repr(_lo_kwargs))
    return UDM.http(**_lo_kwargs)


def name_from_dn(dn):
    return explode_dn(dn, 1)[0]


def url_to_name(request: Request, obj_type: str, url: str) -> str:
    if not url:
        return url
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
    else:
        raise no_object_exception
    return name


def url_to_dn(request: Request, obj_type: str, url: str) -> str:
    """
    Guess object ID (e.g. school name or username) from last past of URL, then
    optionally get object from UDM HTTP API to retrieve DN.
    """
    no_object_exception = NoObject(
        f"Could not find object of type {obj_type!r} with URL {url!r}."
    )
    name = url_to_name(request, obj_type, url)
    if obj_type == "school":
        return f"ou={name},{ucr['ldap/base']}"
    elif obj_type == "user":
        udm_objs = udm_lookup(
            "users/user",
            get_lo_udm(),
            f"(&(objectClass=ucsschoolType)(uid={escape_dn_chars(name)}))",
            base=ucr["ldap/base"],
        )
        if len(udm_objs) == 1:
            return udm_objs[0].dn
        else:
            raise no_object_exception
    raise NotImplemented(f"Don't know how to create DN for obj_type {obj_type!r}.")


def udm_lookup(
    module_name: str,
    lo_udm: UDM,
    filter_str="",
    base="",
    superordinate: str = None,
    scope="sub",
) -> List[Object]:

    try:
        res = list(
            udm_modules.lookup(
                module_name=module_name,
                co=None,
                lo_udm=lo_udm,
                filter=filter_str,
                base=base,
                scope=scope,
                superordinate=superordinate,
            )
        )
        return res
    except noObject:
        return []
