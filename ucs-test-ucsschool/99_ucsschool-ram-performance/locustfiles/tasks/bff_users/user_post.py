#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import random


def create_user(self):
    name = self.fake.unique.pystr(max_chars=15)

    school = self.test_data.random_school()
    school_class = self.test_data.random_class(school)
    json = {
        "name": name,
        "firstname": self.fake.first_name(),
        "lastname": self.fake.last_name(),
        "school": school,
        "schoolClasses": [school_class.split("-", 1)[1]],
        "role": random.choice(self.settings.ROLES),  # nosec
        "password": self.fake.password(length=20),
    }
    with self.client.rename_request("/ucsschool/bff-users/v1/users/"):
        url = f"{self.user_base_url}/users/"
        res = self.request("post", url, json=json, response_codes=[201])
        if res.status_code < 400:
            self.test_cleaner.delete_later_user(name)
