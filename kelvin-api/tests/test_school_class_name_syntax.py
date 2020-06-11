# Copyright 2020 Univention GmbH
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

from typing import List
import random
import string
import pytest
import requests
from pydantic import ValidationError

from udm_rest_client import UDM
from ucsschool.lib.models.utils import ucr
from udm_rest_client.exceptions import CreateError
from ucsschool.kelvin.routers.school_class import SchoolClass

lower_case_chars = f"{string.ascii_lowercase}"
digits = "".join(str(i) for i in range(10))


def random_names(name_lengths: list, chars: str) -> List:
    names = []
    for n in name_lengths:
        names.append(''.join(random.choice(chars) for _ in range(n)))
    return names


@pytest.mark.parametrize("name", random_names(random.choices(range(1, 33), k=100),
                                              f"{lower_case_chars}{digits}"))
@pytest.mark.asyncio
async def test_schoolclass_module(name):
    try:
        SchoolClass(name=name, school='DEMOSCHOOL')
    except ValidationError as e:
        raise e


@pytest.mark.asyncio
async def test_check_class_name(auth_header, url_fragment, udm_kwargs):
    school_name = "DEMOSCHOOL"
    attrs = {
        "school": school_name,
    }
    names = []
    names.append('1a')
    names.append('1-a')
    name_lengths = random.sample(range(1, 33), 3) + [1]*3
    names.extend(random_names(name_lengths, lower_case_chars))
    names.extend(random_names(name_lengths, digits))
    class_names = names
    names = [f"DEMOSCHOOL-{name}" for name in names]

    async with UDM(**udm_kwargs) as udm:
        group_mod = udm.get('groups/group')
        for name in names:
            obj = await group_mod.new()
            obj.props.name = name
            obj.props.ucsschoolRole = [f'school_class:school:{school_name}']
            obj.props.school = [school_name]
            obj.position = f"cn=klassen,cn=schueler,cn=groups,ou={school_name},{ucr.get('ldap/base')}"
            try:
                await obj.save()
            except CreateError:
                # obj already exists, that's ok.
                pass
        response = requests.get(
            f"{url_fragment}/classes/",
            headers={"Content-Type": "application/json", **auth_header},
            params=attrs,
        )
        json_resp = response.json()
        assert response.status_code == 200
        # make sure all classes were created.
        expected = set(class_names)
        received = set([r['name'] for r in json_resp if r['name'] in class_names])
        assert expected == received



