# Copyright 2020-2021 Univention GmbH
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
import string
from typing import List

import pytest
import requests
from faker import Faker

import ucsschool.kelvin.constants
from ucsschool.kelvin.routers.school_class import SchoolClass
from ucsschool.lib.models.utils import ucr
from ucsschool.lib.roles import create_ucsschool_role_string, role_school_class
from udm_rest_client import UDM

must_run_in_container = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)
fake = Faker()


def random_names(name_lengths: List[int], chars: str) -> List[str]:
    names = []
    for n in name_lengths:
        names.append("".join(random.choice(chars) for _ in range(n)))
    return names


@pytest.mark.parametrize(
    "name",
    random_names(random.choices(range(1, 33), k=100), f"{string.ascii_lowercase}{string.digits}"),
)
@must_run_in_container
@pytest.mark.asyncio
async def test_schoolclass_module(name: str, udm_kwargs):
    school = fake.user_name()
    async with UDM(**udm_kwargs) as udm:
        await SchoolClass(name=f"{school}-{name}", school=school).validate(udm)


@must_run_in_container
@pytest.mark.asyncio
async def test_check_class_name(
    auth_header, create_ou_using_python, retry_http_502, url_fragment, udm_kwargs
):
    school_name = await create_ou_using_python()
    names = {"1a", "1-a"}
    name_lengths = random.sample(range(1, 33), 3) + [1] * 3
    names.update(set(random_names(name_lengths, string.ascii_lowercase)))
    names.update(set(random_names(name_lengths, string.digits)))

    async with UDM(**udm_kwargs) as udm:
        group_mod = udm.get("groups/group")
        for name in names:
            obj = await group_mod.new()
            obj.props.name = f"{school_name}-{name}"
            obj.props.ucsschoolRole = [create_ucsschool_role_string(role_school_class, school_name)]
            obj.props.school = [school_name]
            obj.position = f"cn=klassen,cn=schueler,cn=groups,ou={school_name},{ucr.get('ldap/base')}"
            await obj.save()

    response = retry_http_502(
        requests.get,
        f"{url_fragment}/classes/",
        headers={"Content-Type": "application/json", **auth_header},
        params={"school": school_name},
    )
    json_resp = response.json()
    assert response.status_code == 200, response.reason
    # make sure all classes were created.
    received = set(r["name"] for r in json_resp if r["name"] in names)
    assert names == received
