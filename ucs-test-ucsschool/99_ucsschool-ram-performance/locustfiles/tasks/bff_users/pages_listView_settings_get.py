#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only


def get_pages_listView_settings(self):
    with self.client.rename_request("/ucsschool/bff-users/v1/pageconf/listView"):
        url = f"{self.user_base_url}/pageconf/listView"
        self.request("get", url, response_codes=[200])
