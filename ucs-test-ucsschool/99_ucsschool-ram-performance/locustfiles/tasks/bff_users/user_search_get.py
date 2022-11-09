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

# there are 10 different ways to search objects of a school
# 1. search a user
# 2. list all users
# 3. list all disabled users
# 4. list all users and enable
# 5. list all users of a class
# 6. list all users of a class and enable
# 7. list all disabled users of a class
# 8. list all users with a specific role
# 9. list all users with a specific role and enable
# 10. list all disabled users with a specific role
# 11. list all users with a specific role and a specific class
# 12. list all users with a specific role and a specific class and enable
# 13. list all disabled users with a specific role and a specific class


def search_user(self):
    if not hasattr(self, "search_type"):
        self.search_type = random.randint(0, 14)
    school = self.test_data.random_school()
    name = self.test_data.random_user(school)
    user = self.test_data.school_user(school, name)
    random_class = self.test_data.random_class(school).split("-")[1]
    random_role = random.choice(self.settings.ROLES)  # nosec
    search_scenario_parameters = [
        {
            "quickSearch": random.choice([user["name"], user["firstname"], user["lastname"]])[0] + "*"
        },  # search_type 1
        {},  # search_type 2
        {"disabled": "true"},  # search_type 3
        {"disabled": "false"},  # search_type 4
        {"group": random_class},  # search_type 5
        {"group": random_class, "disabled": "false"},  # search_type 6
        {"group": random_class, "disabled": "true"},  # search_type 7
        {"role": random_role},  # search_type 8
        {"role": random_role, "disabled": "false"},  # search_type 9
        {"role": random_role, "disabled": "true"},  # search_type 10
        {"role": random_role, "group": random_class},  # search_type 11
        {"role": random_role, "group": random_class, "disabled": "false"},  # search_type 12
        {"role": random_role, "group": random_class, "disabled": "true"},  # search_type 13
    ]
    with self.client.rename_request("/ucsschool/bff-users/v1/users/search/[school]"):
        url = f"https://{self.settings.BFF_USERS_HOST}/ucsschool/bff-users/v1/users/search/{school}"
        self.request(
            "get", url, params=search_scenario_parameters[self.search_type - 1], response_codes=[200]
        )
