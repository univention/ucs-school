#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import random


def search_groups(self):
    if not hasattr(self, "search_type"):
        self.search_type = random.choice(["school_class", "workgroup"])
    school = self.test_data.random_school()
    group = (
        self.test_data.random_class(school)
        if self.search_type == "school_class"
        else self.test_data.random_workgroup(school)
    )
    group_name = group.split("-")[1]
    group_name_regex = group_name[0] + "*"
    with self.client.rename_request("/ucsschool/bff-groups/v1/groups"):
        url = f"{self.group_base_url}/groups"
        # encode arguments in url
        params = {"quickSearch": group_name_regex, "school": school}
        self.request("get", url, params=params, response_codes=[200])
