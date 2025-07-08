#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import random

# there are 3 scenarios:
# 1. modify a few attributes, no changes to the group membership
# 2. modify a few attributes and change the school class membership
# 3. modify a few attributes and change the school membership


def modify_user(self):
    if not hasattr(self, "scenario"):
        self.scenario = 1
    school = self.test_data.random_school()
    school2 = self.test_data.random_school()
    while school == school2:
        school2 = self.test_data.random_school()
    name = self.test_data.random_user(school)
    json = {}
    if self.scenario >= 1:
        json["firstname"] = self.fake.first_name()
        json["lastname"] = self.fake.last_name()
    if self.scenario == 2:
        json["schoolClasses"] = {
            school: [
                self.test_data.random_class(school).split("-", 1)[1] for _ in range(random.randint(1, 3))
            ]
        }
    elif self.scenario == 3:
        json["schools"] = [school, school2]

    with self.client.rename_request("/ucsschool/bff-users/v1/users/[name]"):
        url = f"{self.user_base_url}/users/{name}"
        self.request("patch", url, json=json, response_codes=[204])
