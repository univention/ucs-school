# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""WSGI"""

from __future__ import unicode_literals

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ucsschool.http_api.app.settings")

from django.core.wsgi import get_wsgi_application  # isort:skip  # noqa: E402

_application = get_wsgi_application()


def application(environ, start_response):
    script_name = environ.get("HTTP_X_SCRIPT_NAME", "")
    if script_name:
        environ["SCRIPT_NAME"] = script_name

    return _application(environ, start_response)
