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
import pytest
import requests

# import ucsschool.kelvin.constants
from ucsschool.kelvin.opa import OPAClient

# pytestmark = pytest.mark.skipif(
#     not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
#     reason="Must run inside Docker container started by appcenter.",
# )

pytestmark = pytest.mark.skipif(True, reason="OPA disabled for now")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ("classes", "roles", "schools"))
@pytest.mark.parametrize("role", ("student", "teacher", "staff", "school_admin"))
async def test_unhandled_routes_non_kelvin_admin(
    route: str, role: str, generate_auth_header, url_fragment
):
    """
    This test is just to ensure that routes that are not yet handled by OPA are
    inaccessible by non kelvin admins. It is just checked for the GET method
    """
    headers = await generate_auth_header(
        "dummy", False, schools=["DEMOSCHOOL"], roles=[f"{role}:school:DEMOSCHOOL"]
    )
    params = dict()
    if route == "classes":
        params["school"] = "DEMOSCHOOL"
    response = requests.get(f"{url_fragment}/{route}", headers=headers, params=params)
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ("classes", "roles", "schools"))
async def test_unhandled_routes_kelvin_admin(route: str, generate_auth_header, url_fragment):
    headers = await generate_auth_header("dummy", True, schools=[], roles=[])
    params = dict()
    if route == "classes":
        params["school"] = "DEMOSCHOOL"
    response = requests.get(f"{url_fragment}/{route}", headers=headers, params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ("student", "teacher", "staff", "school_admin"))
@pytest.mark.parametrize(
    "json,expected",
    (
        ({"password": "nfi4ztr8wuisdef"}, 200),
        ({"password": "fh8734h", "firstname": "other"}, 404),
    ),
)
async def test_reset_own_password(
    role, json, expected, url_fragment, generate_auth_header, create_random_users
):
    user = (await create_random_users({role: 1}, disabled=False))[0]
    headers = await generate_auth_header(
        user.name, False, schools=["DEMOSCHOOL"], roles=[f"{role}:school:DEMOSCHOOL"]
    )
    response = requests.patch(
        f"{url_fragment}/users/{user.name}",
        headers=headers,
        json=json,
    )
    assert response.status_code == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role,expected",
    (
        ("teacher", {"student"}),
        ("student", set()),
        ("staff", {"teacher", "student"}),
        ("school_admin", {"teacher", "student", "school_admin", "staff"}),
    ),
)
@pytest.mark.parametrize("school", ("DEMOSCHOOL", "OTHERSCHOOL"))
async def test_policy_list(
    role: str,
    expected: set,
    school: str,
    generate_jwt,
):
    token = await generate_jwt("actor", False, ["DEMOSCHOOL"], [f"{role}:school:DEMOSCHOOL"])
    request = dict(
        method="GET",
        path=["users"],
        data=[
            dict(
                username="student",
                schools=[school],
                roles=[f"student:school:{school}"],
            ),
            dict(
                username="teacher",
                schools=[school],
                roles=[f"teacher:school:{school}"],
            ),
            dict(
                username="staff",
                schools=[school],
                roles=[f"staff:school:{school}"],
            ),
            dict(
                username="school_admin",
                schools=[school],
                roles=[f"school_admin:school:{school}"],
            ),
        ],
    )
    target = {}
    assert set(
        await OPAClient.instance().check_policy("allowed_users_list", token, request, target)
    ) == (expected if school == "DEMOSCHOOL" else set())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "actor_role,target_role,expected",
    (
        ("student", "student", False),
        ("student", "teacher", False),
        ("student", "staff", False),
        ("student", "school_admin", False),
        ("teacher", "student", True),
        ("teacher", "teacher", False),
        ("teacher", "staff", False),
        ("teacher", "school_admin", False),
        ("staff", "student", False),
        ("staff", "teacher", False),
        ("staff", "staff", False),
        ("staff", "school_admin", False),
        ("school_admin", "student", True),
        ("school_admin", "teacher", True),
        ("school_admin", "staff", False),
        ("school_admin", "school_admin", False),
    ),
)
@pytest.mark.parametrize("school", ("DEMOSCHOOL", "OTHERSCHOOL"))
async def test_policy_password_reset_as_role(
    actor_role: str, target_role: str, expected: bool, school: str, generate_jwt
):
    token = await generate_jwt("actor", False, ["DEMOSCHOOL"], [f"{actor_role}:school:DEMOSCHOOL"])
    request = dict(method="PATCH", path=["users", "target"], data={"password": "new_password"})
    target = dict(
        username="target",
        schools=["DEMOSCHOOL"],
        roles=[f"{target_role}:school:DEMOSCHOOL"],
    )
    assert await OPAClient.instance().check_policy_true("users", token, request, target) == expected
