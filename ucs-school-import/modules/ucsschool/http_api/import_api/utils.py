#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2018-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Diverse helper functions."""

import grp
import pwd


def get_wsgi_user_group():
    """
    Get the username and group name of the WSGI process in which the HTTP-API
    runs.

    :return: tuple with username and group name
    :rtype: tuple(str, str)
    """
    return "uas-import", "uas-import"


def get_wsgi_uid_gid():
    """
    Get the UID and GID of the WSGI process in which the HTTP-API runs.

    :return: tuple with UID and GID
    :rtype: tuple(int, int)
    """
    user_name, group_name = get_wsgi_user_group()
    return pwd.getpwnam(user_name).pw_uid, grp.getgrnam(group_name).gr_gid
