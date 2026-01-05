# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Django settings file that gets its content from
/etc/ucsschool-import/settings.py
"""

import imp

info = imp.find_module("settings", ["/etc/ucsschool-import"])
res = imp.load_module("settings", *info)
globals().update({k: v for k, v in res.__dict__.items() if k == k.upper()})
