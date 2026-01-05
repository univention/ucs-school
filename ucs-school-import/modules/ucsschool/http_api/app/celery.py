# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Django settings for the UCS@school import HTTP API."""

from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ucsschool.http_api.app.settings")

app = Celery("import_http_api")
app.config_from_object("django.conf:settings")
app.autodiscover_tasks(packages=["ucsschool.http_api.import_api"])
