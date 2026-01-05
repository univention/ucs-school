#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

deleted_groups = {}
max_tries = 100


def delete_group(self):
    tries = 0
    while True:
        tries += 1
        school = self.test_data.random_school()
        group_name = (
            self.test_data.random_workgroup(school)
            if self.group_type == "workgroup"
            else self.test_data.random_class(school)
        )
        if group_name not in deleted_groups.get(school, set()):
            deleted_groups.setdefault(school, set()).add(group_name)
            break
        if tries >= max_tries:
            raise RuntimeError(f"Could not get unused group after {tries} tries.")
    with self.client.rename_request(f"/ucsschool/bff-groups/v1/{self.group_type}/[group]"):
        url = f"{self.group_base_url}/{self.group_type}/{group_name}"
        self.request("delete", url, response_codes=[204])
