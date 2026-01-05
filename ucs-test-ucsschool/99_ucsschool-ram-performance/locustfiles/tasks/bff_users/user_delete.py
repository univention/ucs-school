#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

deleted_users = {}
max_tries = 100


def delete_user(self):
    tries = 0
    while True:
        tries += 1
        school = self.test_data.random_school()
        name = self.test_data.random_user(school)
        if name not in deleted_users.get(school, set()):
            deleted_users.setdefault(school, set()).add(name)
            break
        if tries >= max_tries:
            raise RuntimeError(f"Could not get unused user after {tries} tries.")
    with self.client.rename_request("/ucsschool/bff-users/v1/users/[name]"):
        url = f"{self.user_base_url}/users/{name}"
        self.request("delete", url, response_codes=[204])
