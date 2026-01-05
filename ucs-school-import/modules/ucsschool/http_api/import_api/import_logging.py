#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Logging configuration for the HTTP API"""

from __future__ import absolute_import, unicode_literals

import logging

from django.conf import settings

FILE_HANDLER_NAME = "http_api.log"

logger = logging.getLogger(__name__)

if FILE_HANDLER_NAME not in [h.name for h in logger.handlers]:
    _file_handler = logging.FileHandler(settings.UCSSCHOOL_IMPORT["logging"]["api_logfile"])
    _file_handler.set_name(FILE_HANDLER_NAME)
    _file_handler.setFormatter(
        logging.Formatter(
            fmt=settings.UCSSCHOOL_IMPORT["logging"]["api_format"],
            datefmt=settings.UCSSCHOOL_IMPORT["logging"]["api_datefmt"],
        )
    )
    _file_handler.setLevel(level=settings.UCSSCHOOL_IMPORT["logging"]["api_level"])
    logger.addHandler(_file_handler)
    logger.setLevel(max(logger.level, _file_handler.level))
