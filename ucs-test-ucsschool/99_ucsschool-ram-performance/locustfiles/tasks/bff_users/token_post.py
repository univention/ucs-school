#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only


def token_post(self):
    school = self.test_data.random_school()
    name = self.test_data.random_user(school)
    with self.client.rename_request("/ucsschool/bff-users/v1/token"):
        url = f"{self.user_base_url}/token"
        headers = {"content-type": "application/x-www-form-urlencoded", "accept": "application/json"}
        data = {"username": name, "password": self.password}
        self.request("post", url, data=data, headers=headers, response_codes=[200])
