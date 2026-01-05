#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from uuid import uuid4


def create_group(self):
    school = self.test_data.random_school()
    name = f"testgroup-{uuid4()!s}"
    description = f"Randomly generated group for {school} created by locust, group name: {name}"
    with self.client.rename_request("/ucsschool/bff-groups/v1/workgroup"):
        url = f"{self.group_base_url}/workgroup"
        json = {
            "name": f"{school}-{name}",
            "school": school,
            "description": description,
            "users": self.test_data.random_users(school, k=10),
        }
        self.request("post", url, json=json, response_codes=[201])
