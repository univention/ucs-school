#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only


def get_user(self):
    school = self.test_data.random_school()
    name = self.test_data.random_user(school)
    with self.client.rename_request("/ucsschool/bff-users/v1/users/[name]"):
        url = f"{self.user_base_url}/users/{name}"
        self.request("get", url, response_codes=[200])
