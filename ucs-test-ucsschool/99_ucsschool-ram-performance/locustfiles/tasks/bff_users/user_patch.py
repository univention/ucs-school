#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright 2022 Univention GmbH
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
