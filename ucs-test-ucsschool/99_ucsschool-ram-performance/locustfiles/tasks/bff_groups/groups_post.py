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

from uuid import uuid4


def create_group(self):
    school = self.test_data.random_school()
    name = f"testgroup-{str(uuid4())}"
    description = f"Randomly generated group for {school} created by locust, group name: {name}"
    with self.client.rename_request(f"/ucsschool/bff-groups/v1/groups/{self.group_type}/"):
        url = f"https://{self.settings.BFF_USERS_HOST}/ucsschool/bff-groups/v1/groups/{self.group_type}/"
        json = {
            "name": name,
            "school": school,
            "description": description,
            "users": self.test_data.random_users(school, k=10),
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self.request("post", url, json=json, headers=headers, response_codes=[201])
