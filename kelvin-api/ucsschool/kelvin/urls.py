# Copyright 2020 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

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
