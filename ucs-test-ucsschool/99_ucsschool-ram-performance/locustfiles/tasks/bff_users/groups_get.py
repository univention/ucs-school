#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import random


def get_groups(self):
    group_kind = getattr(self, "group_kind", random.choice(["school_class", "workgroup"]))
    school = self.test_data.random_school()
    with self.client.rename_request(f"/ucsschool/bff-users/v1/{group_kind}"):
        url = f"{self.user_base_url}/{group_kind}"
        params = {"school": school}
        self.request("get", url, response_codes=[200], params=params)
