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

import random


def get_groups(self):
    group_kind = getattr(self, "group_kind", random.choice(["school_class", "workgroup"]))
    school = self.test_data.random_school()
    with self.client.rename_request(f"/ucsschool/bff-users/v1/{group_kind}"):
        url = f"{self.user_base_url}/{group_kind}"
        params = {"school": school}
        self.request("get", url, response_codes=[200], params=params)
