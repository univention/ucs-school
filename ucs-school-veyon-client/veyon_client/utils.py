# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2020-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import requests  # noqa: F401

from .models import VeyonError


def check_veyon_error(response):  # type: (requests.Response) -> None
    if response.status_code == 200:
        return
    data = response.json()
    error = data.get("error", {})
    error_code = error.get("code", -1)
    error_message = error.get("message", "")
    if error_code != 0:
        raise VeyonError(error_message, error_code)
