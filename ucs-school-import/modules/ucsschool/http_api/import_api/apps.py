#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2017-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""App registry"""

from __future__ import unicode_literals

from django.apps import AppConfig


class HttpApiConfig(AppConfig):
    name = "ucsschool.http_api.import_api"
    verbose_name = "UCS@school import API"
