# -*- coding: utf-8 -*-

# Copyright 2020-2024 Univention GmbH
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

import time
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import TYPE_CHECKING, Dict, Optional  # noqa: F401

import requests

from .models import (
    AuthenticationMethod,
    ScreenshotFormat,
    VeyonConnectionError,
    VeyonError,
    VeyonSession,
    VeyonUser,
)
from .utils import check_veyon_error

if TYPE_CHECKING:
    from .models import Dimension, Feature  # noqa: F401


class VeyonClient:
    def __init__(
        self,
        url,
        credentials,
        auth_method=AuthenticationMethod.AUTH_KEYS,
        default_host="localhost",
        idle_timeout=60,
    ):  # type: (str, Dict[str, str], Optional[AuthenticationMethod], str, int) -> None
        """
        Creates a client that communicates with the Veyon API to control features and fetch
        screenshots.

        :param url: The url this client should connect to
        :param credentials: The credentials used to authenticate against the Veyon API
        :param auth_method: The method to use for authentication against the Veyon API
        :param default_host: The default host to connect to if no specific host is provided
        :param idle_timeout: The maximum time a connection can be idle without being invalidated by the
            server. Has to be a value > 0. If the given value is < 1, the value is set to 1.
        """
        self._url = url
        self._credentials = credentials
        self._auth_method = auth_method
        self._default_host = default_host
        self._idle_timeout = max(idle_timeout - 1, 1)
        self._ping_timeout = 5.0
        self._session_cache = {}  # type: Dict[str, VeyonSession]
        self._last_used = {}  # type: Dict[str, float]
        self._session_locks = defaultdict(Lock)  # type: defaultdict[str, Lock]
        self._locks_lock = Lock()  # type: Lock
        """This lock is needed to ensure thread safe operation of the defaultdict for the individual
        session locks"""

    def _get_headers(self, host=None):  # type: (Optional[str]) -> Dict[str, str]
        return {"Connection-Uid": self._get_connection_uid(host)}

    def _reset_idle_time(self, host):
        self._last_used[host] = time.time()

    def _create_session(self, host):  # type: (str) -> VeyonSession
        auth_route = "{}/authentication/{}".format(self._url, host)
        result = requests.post(
            auth_route, json={"method": str(self._auth_method), "credentials": self._credentials}
        )
        check_veyon_error(result)
        session_data = result.json()
        return VeyonSession(str(session_data["connection-uid"]), session_data["validUntil"])

    def _get_connection_uid(self, host=None, renew_session=True):
        # type:(Optional[str], Optional[bool]) -> str
        """
        Fetches the connection uid for a given host from the cache or generates a new one if none is
        present or valid.

        :param str host: The host to fetch the connection uid for
        :param bool renew_session: If set to False an exception is thrown if no valid session exists in
            the session cache
        :return: The connection uid
        :rtype: str
        :raises VeyonError: If renew_session=False and the cached connection does not exist or is invalid
        """
        host = host if host else self._default_host
        with self._locks_lock:
            host_lock = self._session_locks[host]
        with host_lock:
            session = self._session_cache.get(host, None)  # type: VeyonSession
            if (
                session
                and datetime.fromtimestamp(session.valid_until) > datetime.now()
                and time.time() - self._last_used.get(host, 0.0) < self._idle_timeout
            ):
                self._reset_idle_time(host)
                return session.connection_uid
            else:
                if not renew_session:
                    raise VeyonError("The currently cached connection is invalid", 2)
                self.remove_session(host)
                session = self._create_session(host)
                self._session_cache[host] = session
                self._reset_idle_time(host)
                return session.connection_uid

    def remove_session(self, host):  # type: (str) -> None
        """
        This function tries to close the currently cached connection to the host and then purges it
        from the cache. This function is not thread safe and thus needs to be used in an already thread
        safe context.

        :param str host: The host to remove the session for
        """
        try:
            session = self._session_cache.get(host, None)
            session_uid = session.connection_uid if session else ""
            requests.delete(
                "{}/authentication".format(self._url),
                headers={"Connection-Uid": session_uid},
            )
        except requests.RequestException:
            raise VeyonConnectionError
        except VeyonError:
            pass  # We do not care if the connection was already invalid or does not exist anymore
        if host in self._session_cache:
            del self._session_cache[host]
        if host in self._last_used:
            del self._last_used[host]

    def test_connection(self):
        """
        Check if the veyon WebAPI Server is reachable

        :raises VeyonConnectionError: if the there is no response.
        """
        try:
            requests.head("{}/feature".format(self._url), timeout=self._ping_timeout)
        except requests.RequestException:
            raise VeyonConnectionError("No response from WebAPI Server ({}).".format(self._url))
        return True

    def get_screenshot(
        self,
        host=None,
        screenshot_format=ScreenshotFormat.PNG,
        compression=5,
        quality=75,
        dimension=None,
    ):  # type: (Optional[str], Optional[ScreenshotFormat], Optional[int], Optional[int], Optional[Dimension]) -> bytes  # noqa: E501
        """
        Fetches a screenshot for the specified host from the Veyon API

        :param host: The host to fetch the screenshot for. If not specified the default host is used.
        :param screenshot_format: The file format the screenshot should be returned as
        :param compression: The compression level of the screenshot. Only used if the format is png
        :param quality: The quality of the screenshot. Only used if format is jpeg
        :param dimension: Optional specification of the screenshots dimensions as (width, height). If
            neither is specified (dimension=None) the original dimensions are used. If either is
            specified the other
            one is calculated in a way to keep the aspect ratio.
        :return: The screenshot as bytes
        :rtype: bytes
        :raises VeyonError: Can throw a VeyonError(10) if no framebuffer is available yet.
        """
        params = {"format": screenshot_format, "compression": compression, "quality": quality}
        if dimension and dimension.width:
            params["width"] = dimension.width
        if dimension and dimension.height:
            params["height"] = dimension.height
        try:
            result = requests.get(
                "{}/framebuffer".format(self._url), params=params, headers=self._get_headers(host)
            )
        except requests.RequestException as exc:
            raise VeyonConnectionError(exc)
        check_veyon_error(result)
        return result.content

    def ping(self, host=None):  # type: (Optional[str]) -> bool
        host = host if host else self._default_host
        try:
            result = requests.get(
                "{}/authentication/{}".format(self._url, host), timeout=self._ping_timeout
            )
            return result.status_code == 200
        except requests.RequestException as exc:
            raise VeyonConnectionError(exc)

    def set_feature(self, feature, host=None, active=True, arguments=None):
        # type: (Feature, Optional[str], Optional[bool], Optional[Dict[str, str]]) -> None
        """
        De-/Activates a Veyon feature on the given host

        :param host: The host to set the feature for. If not specified the default host is used.
        :param feature: The feature to set
        :param active: True if the feature should be activated or triggered, False to deactivate a
            feature
        :param arguments: A dictionary containing additional arguments for the feature
        """
        data = {"active": active}
        if arguments:
            data["arguments"] = arguments
        try:
            result = requests.put(
                "{}/feature/{}".format(self._url, feature),
                json=data,
                headers=self._get_headers(host),
            )
        except requests.RequestException as exc:
            raise VeyonConnectionError(exc)
        check_veyon_error(result)

    def get_feature_status(self, feature, host=None):  # type: (Feature, Optional[str]) -> bool
        """
        Fetches the status of a given feature on a given host.

        :param host: The host to fetch the feature status for. If not specified the default host is used.
        :param feature: The feature to fetch the status for

        :returns: True if the feature is activated, False if the feature is deactivated or has no
            status, like "REBOOT"
        :rtype: bool
        """
        try:
            result = requests.get(
                "{}/feature/{}".format(self._url, feature), headers=self._get_headers(host)
            )
        except requests.RequestException as exc:
            raise VeyonConnectionError(exc)
        check_veyon_error(result)
        return result.json()["active"]

    def get_user_info(self, host=None):  # type: (Optional[str]) -> VeyonUser
        """
        Fetches the information about a logged in user on a given host

        :param host: The host to fetch the user info for. If not specified the default host is used.

        :returns: The info about the logged in user. If no user is logged in the session field of the
            result will be -1
        :rtype: VeyonUser
        """
        try:
            result = requests.get("{}/user".format(self._url), headers=self._get_headers(host))
        except requests.RequestException as exc:
            raise VeyonConnectionError(exc)
        check_veyon_error(result)
        return VeyonUser(**result.json())
