#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright 2022-2024 Univention GmbH
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

deleted_users = {}
max_tries = 100


def delete_user(self):
    tries = 0
    while True:
        tries += 1
        school = self.test_data.random_school()
        name = self.test_data.random_user(school)
        if name not in deleted_users.get(school, set()):
            deleted_users.setdefault(school, set()).add(name)
            break
        if tries >= max_tries:
            raise RuntimeError(f"Could not get unused user after {tries} tries.")
    with self.client.rename_request("/ucsschool/bff-users/v1/users/[name]"):
        url = f"{self.user_base_url}/users/{name}"
        self.request("delete", url, response_codes=[204])
