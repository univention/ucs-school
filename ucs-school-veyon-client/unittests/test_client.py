#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -s -l -v
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2020-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import calendar
import threading
import time
import uuid
from datetime import datetime

import pytest
import requests
from requests import ConnectionError, Response
from veyon_client.client import VeyonClient
from veyon_client.models import (
    AuthenticationMethod,
    VeyonConnectionError,
    VeyonError,
    VeyonSession,
    VeyonUser,
)


def monkey_get(*args, **kwargs):
    response = Response()
    url_parts = args[1].split("/")
    domain = url_parts[0]
    method = url_parts[1]
    if domain in ["unreachable"]:
        raise ConnectionError()
    elif domain in ["user_info"]:
        response.status_code = 200
        response._content = b'{ "login":"LOGIN", "fullName":"FULLNAME", "session":"SESSION" }'
    elif domain in ["get_feature"]:
        response.status_code = 200
        feature = url_parts[2]
        if feature == "REBOOT":
            response._content = b'{"active":false}'
        elif feature == "SCREEN_LOCK":
            response._content = b'{"active":true}'
    elif domain == "encoding_error":
        response.status_code = 500
        response._content = b'{"error":{"code":10,"message":"Framebuffer encoding error"}}'
    elif method in ["framebuffer"]:
        params = kwargs.get("params")
        if params["format"] == "gif":
            response.status_code = 400
            response._content = b'{"error":{"code":9,"message":"Unsupported image format"}}'
        else:
            response.status_code = 200
            response._content = "{}-{}-{}".format(
                params["format"], params["compression"], params["quality"]
            ).encode("UTF-8")
    else:
        raise RuntimeError("Unexpected url for monkeypatch get: {}".format(args[1]))
    return response


def monkey_post(*args, **kwargs):
    response = Response()
    url_parts = args[1].split("/")
    domain = url_parts[0]
    method = url_parts[1]
    if domain in ["wrong_credentials"]:
        response.status_code = 400
        response._content = b'{"error":{"code":4,"message":"Invalid credentials"}}'
    elif domain in ["invalid_feature"]:
        response.status_code = 400
        response._content = b'{"error":{"code":3,"message":"Invalid feature"}}'
    elif domain in ["wrong_method"]:
        response.status_code = 400
        response._content = b'{"error":{"code":5,"message":"Authentication method not available"}}'
    elif (
        domain
        in [
            "create_session",
            "framebuffer",
            "encoding_error",
            "invalid_feature",
            "get_feature",
            "user_info",
            "idle_timeout",
            "remove_session",
        ]
        and method == "authentication"
    ):
        response.status_code = 200
        response._content = b'{"connection-uid":"42", "validUntil": 0}'
    elif domain in ["random_uid"] and method == "authentication":
        response.status_code = 200
        response._content = b'{"connection-uid":"%s", "validUntil": %s}' % (
            str(uuid.uuid4()).encode(),
            str(time.time() + 600).encode(),
        )  # nosec
    else:
        raise RuntimeError("Unexpected url for monkeypatch post: {}".format(args[0]))
    return response


def monkey_delete(*args, **kwargs):
    return None


def test_connection_error_on_unreachable_url(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    client = VeyonClient("unreachable", {})
    assert not client.ping()


def test_connection_test(monkeypatch):
    with pytest.raises(VeyonConnectionError):
        client = VeyonClient("http://unreachableurl", {})
        client.test_connection()


def test_authentication_method_not_available(monkeypatch):
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    client = VeyonClient("wrong_method", {}, auth_method=AuthenticationMethod.AUTH_KEYS)
    with pytest.raises(VeyonError) as exc:
        client._create_session("localhost")
    assert exc.value.code == 5


def test_wrong_credentials(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    client = VeyonClient("wrong_credentials", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    with pytest.raises(VeyonError) as exc:
        client._create_session("localhost")
    assert exc.value.code == 4


def test_create_session(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    client = VeyonClient("create_session", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    assert client._create_session("localhost") == VeyonSession("42", 0)


def test_reuse_session():
    client = VeyonClient("reuse_session", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    time = datetime.now()
    client._session_cache["localhost"] = VeyonSession(
        "99", calendar.timegm(time.replace(time.year + 1).timetuple())
    )
    client._reset_idle_time("localhost")
    assert client._get_connection_uid() == "99"


def test_second_host(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    client = VeyonClient("create_session", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    time = datetime.now()
    client._session_cache["localhost"] = VeyonSession(
        "99", calendar.timegm(time.replace(time.year + 1).timetuple())
    )
    assert client._create_session("other_host") == VeyonSession("42", 0)


@pytest.mark.parametrize("screenshot_format,compression,quality", [("png", 6, 80), ("jpeg", 1, 20)])
def test_framebuffer(monkeypatch, screenshot_format, compression, quality):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("framebuffer", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    assert client.get_screenshot(
        screenshot_format=screenshot_format, quality=quality, compression=compression
    ) == "{}-{}-{}".format(screenshot_format, compression, quality).encode("UTF-8")


def test_wrong_image_format(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("framebuffer", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    with pytest.raises(VeyonError) as exc:
        client.get_screenshot(screenshot_format="gif")
    assert exc.value.code == 9


def test_encoding_error(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("encoding_error", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    with pytest.raises(VeyonError) as exc:
        client.get_screenshot()
    assert exc.value.code == 10


def test_invalid_feature(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("invalid_feature", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    with pytest.raises(VeyonError) as exc:
        client.set_feature("NON_EXISTENT_FEATURE")
    assert exc.value.code == 3


def test_invalid_feature_status(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("invalid_feature", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    with pytest.raises(VeyonError) as exc:
        client.get_feature_status("NON_EXISTENT_FEATURE")
    assert exc.value.code == 3


@pytest.mark.parametrize("feature,expected", [("REBOOT", False), ("SCREEN_LOCK", True)])
def test_get_feature_status(monkeypatch, feature, expected):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("get_feature", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    assert client.get_feature_status(feature) == expected


def test_get_user_info(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("user_info", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    assert client.get_user_info() == VeyonUser("LOGIN", "FULLNAME", "SESSION")


def test_idle_timeout(monkeypatch):
    monkeypatch.setattr(requests.Session, "get", monkey_get)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("idle_timeout", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    time = datetime.now()
    client._session_cache["localhost"] = VeyonSession(
        "99", calendar.timegm(time.replace(time.year + 1).timetuple())
    )
    client._last_used["localhost"] = 0.0
    assert client._get_connection_uid() == "42"


def test_remove_session(monkeypatch):
    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    client = VeyonClient("remove_session", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    time = datetime.now()
    client._session_cache["localhost"] = VeyonSession(
        "99", calendar.timegm(time.replace(time.year + 1).timetuple())
    )
    client._last_used["localhost"] = 0.0
    client.remove_session("localhost")
    assert client._session_cache == {}
    assert client._last_used == {}


def test_invalid_cached_session():
    client = VeyonClient("invalid_cached_session", {}, auth_method=AuthenticationMethod.AUTH_LOGON)
    client._session_cache["localhost"] = None
    with pytest.raises(VeyonError) as exc:
        client._get_connection_uid(renew_session=False)
    assert exc.value.code == 2


def test_client_thread_safety(monkeypatch):
    n = 1000
    results = [None] * n

    def _call_get_connection_uid(j):
        results[j] = client._get_connection_uid("localhost")

    monkeypatch.setattr(requests.Session, "delete", monkey_delete)
    monkeypatch.setattr(requests.Session, "post", monkey_post)
    client = VeyonClient(
        "random_uid",
        {},
        auth_method=AuthenticationMethod.AUTH_LOGON,
    )
    threads = []
    for i in range(n):
        x = threading.Thread(target=_call_get_connection_uid, args=(i,))
        threads.append(x)
        x.start()
    for thread in threads:
        thread.join()
    # all uids must be equal and not equal None
    assert results[0] and results.count(results[0]) == len(results)
