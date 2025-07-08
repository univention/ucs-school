#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2016-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class for all Python based hooks."""


class PyHook(object):
    """
    Base class for all Python based hooks.

    Do not use this class directly, use one of its subclasses like UserPyHook.
    """

    # If multiple hook classes are found, hook functions with higher
    # priorities run before those with lower priorities. None disables
    # a function.
    priority = {}

    def __init__(self, *arg, **kwargs):
        pass
