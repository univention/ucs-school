#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: selective-udm
#
# Copyright 2012-2021 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

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
    with self.client.rename_request("/ucsschool/bff-groups/v1/groups/search/[school]"):
        url = f"https://{self.settings.BFF_USERS_HOST}/ucsschool/bff-groups/v1/groups/search/{school}"
        # encode arguments in url
        params = {"quickSearch": group_name_regex}
        self.request("get", url, params=params, response_codes=[200])
