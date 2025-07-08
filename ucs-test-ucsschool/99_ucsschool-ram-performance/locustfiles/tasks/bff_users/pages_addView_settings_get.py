#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only


def get_pages_addView_settings(self):
    with self.client.rename_request("/ucsschool/bff-users/v1/pageconf/addView"):
        url = f"{self.user_base_url}/pageconf/addView"
        self.request("get", url, response_codes=[200])
