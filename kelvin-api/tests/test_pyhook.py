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

import datetime
import inspect
import random
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Type, Union

import pytest
import requests
from faker import Faker

import ucsschool.kelvin.constants
import univention.admin.uldap_docker
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.importer.utils.format_pyhook import FormatPyHook
from ucsschool.importer.utils.user_pyhook import UserPyHook
from ucsschool.kelvin.routers.user import UserModel
from ucsschool.lib.models.user import Staff, Student, Teacher, TeachersAndStaff, User
from udm_rest_client import UDM

pytestmark = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)

UserType = Type[Union[Staff, Student, Teacher, TeachersAndStaff, User]]
Role = NamedTuple("Role", [("name", str), ("klass", UserType)])
USER_ROLES: List[Role] = [
    Role("staff", Staff),
    Role("student", Student),
    Role("teacher", Teacher),
    Role("teacher_and_staff", TeachersAndStaff),
]  # User.role_sting -> User
random.shuffle(USER_ROLES)
fake = Faker()


class FormatFirstnamePyHook(FormatPyHook):
    priority = {
        "patch_fields_student": 10,
        "patch_fields_teacher_and_staff": 10,
    }
    properties = ("firstname",)

    def crazy_camel(self, property_name: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        import random

        fields["lastname"] = "".join(
            [
                getattr(char, random.choice(("upper", "lower")))()
                for char in fields["lastname"]
            ]
        )
        return fields

    patch_fields_student = crazy_camel
    patch_fields_teacher_and_staff = crazy_camel


class UserBirthdayPyHook(UserPyHook):
    priority = {
        "pre_create": 10,
        "post_create": 10,
        "pre_modify": 10,
        "post_modify": 10,
        "pre_remove": 10,
        "post_remove": 10,
    }

    def __init__(
        self,
        lo: univention.admin.uldap_docker.access = None,
        dry_run: bool = None,
        udm: UDM = None,
        *args,
        **kwargs,
    ) -> None:
        from ucsschool.lib.models.utils import env_or_ucr
        from ucsschool.importer.utils.user_pyhook import KelvinUserHook

        assert isinstance(self, KelvinUserHook)
        super(UserBirthdayPyHook, self).__init__(
            lo=lo, dry_run=dry_run, udm=udm, *args, **kwargs
        )
        self.logger.info("   -> THIS IS A KelvinUserHook")
        self.base_dn = env_or_ucr("ldap/base")

    async def test_lo(self):
        assert isinstance(self.lo, univention.admin.uldap_docker.access), type(self.lo)
        admin = self.lo.get(f"uid=Administrator,cn=users,{self.base_dn}")
        samba_sid = admin["sambaSID"][0]
        if isinstance(samba_sid, bytes):
            samba_sid: str = samba_sid.decode("utf-8")
        assert samba_sid.endswith("-500")

    async def test_udm(self):
        assert isinstance(self.udm, UDM), type(self.udm)
        assert self.udm.session._session
        assert not self.udm.session._session.closed
        base_dn: str = await self.udm.session.base_dn
        assert base_dn == self.base_dn

    async def pre_create(self, user: ImportUser) -> None:
        await self.test_lo()
        await self.test_udm()

    async def post_create(self, user: ImportUser) -> None:
        import datetime

        await self.test_lo()
        await self.test_udm()
        self.logger.info("   -> HAPPY BIRTHDAY")

        user.birthday = datetime.date.today().isoformat()
        await user.modify(self.udm)

    async def pre_modify(self, user: ImportUser) -> None:
        await self.test_lo()
        await self.test_udm()

        user.firstname = user.lastname
        self.logger.info("   -> NEW GIVEN NAME")

    async def post_modify(self, user: ImportUser) -> None:
        await self.test_lo()
        await self.test_udm()
        self.logger.info("   -> HOWDY NEW NAMER")

    async def pre_remove(self, user: ImportUser) -> None:
        await self.test_lo()
        await self.test_udm()
        self.logger.info("   -> GOODBYE")

    async def post_remove(self, user: ImportUser) -> None:
        await self.test_lo()
        await self.test_udm()
        from pathlib import Path

        Path("/tmp", user.name).touch()
        self.logger.info("   -> RIP")


@pytest.fixture(scope="module")
def create_pyhook(restart_kelvin_api_server_module):
    cache_path = ucsschool.kelvin.constants.KELVIN_IMPORTUSER_HOOKS_PATH / "__pycache__"
    module_names = []

    def _func(name, text):
        module_names.append(name)
        hook_path = ucsschool.kelvin.constants.KELVIN_IMPORTUSER_HOOKS_PATH / f"{name}.py"
        with open(hook_path, "w") as fp:
            fp.write(text)
        restart_kelvin_api_server_module()

    yield _func

    for name in module_names:
        hook_path = ucsschool.kelvin.constants.KELVIN_IMPORTUSER_HOOKS_PATH / f"{name}.py"
        try:
            hook_path.unlink()
        except FileNotFoundError:
            pass
        for cache_file in cache_path.glob(f"{name}.*"):
            cache_file.unlink()
    restart_kelvin_api_server_module()


@pytest.fixture(scope="module")
def create_format_pyhook(create_pyhook):
    text = f"""from typing import Any, Dict
from ucsschool.importer.utils.format_pyhook import FormatPyHook

{inspect.getsource(FormatFirstnamePyHook)}
"""
    create_pyhook("formattesthook", text)


@pytest.fixture(scope="module")
def create_user_pyhook(create_pyhook):
    text = f"""from udm_rest_client import UDM
import univention.admin.uldap_docker
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.importer.utils.user_pyhook import UserPyHook

{inspect.getsource(UserBirthdayPyHook)}
"""
    create_pyhook("usertesthook", text)


def role_id(value: Role) -> str:
    return value.name


def bday_id(bday: datetime.date) -> str:
    return bday.isoformat()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_format_pyhook(
    auth_header,
    url_fragment,
    udm_kwargs,
    create_random_user_data,
    schedule_delete_user,
    create_format_pyhook,
    role: Role,
):
    hook_path = (
        ucsschool.kelvin.constants.KELVIN_IMPORTUSER_HOOKS_PATH / "formattesthook.py"
    )
    with open(hook_path, "r") as fp:
        print(f"****** {hook_path!s} ******")
        print(fp.read())
        print("***********************************************")
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    r_user = await create_random_user_data(
        roles=[f"{url_fragment}/roles/{role_}" for role_ in roles]
    )
    r_user.firstname = ""
    data = r_user.json()
    print(f"POST data={data!r}")
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
    assert len(lib_users) == 0
    schedule_delete_user(r_user.name)
    response = requests.post(
        f"{url_fragment}/users/",
        headers={"Content-Type": "application/json", **auth_header},
        data=data,
    )
    assert response.status_code == 201, f"{response.__dict__!r}"
    response_json = response.json()
    api_user = UserModel(**response_json)
    if role.name in ("staff", "teacher"):
        assert api_user.firstname == api_user.lastname
    else:
        assert api_user.firstname != api_user.lastname
        assert api_user.firstname.lower() == api_user.lastname.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", USER_ROLES, ids=role_id)
async def test_user_pyhook(
    auth_header,
    url_fragment,
    udm_kwargs,
    create_random_user_data,
    schedule_delete_user,
    create_user_pyhook,
    role: Role,
):
    hook_path = (
        ucsschool.kelvin.constants.KELVIN_IMPORTUSER_HOOKS_PATH / "usertesthook.py"
    )
    with open(hook_path, "r") as fp:
        print(f"****** {hook_path!s} ******")
        print(fp.read())
        print("***********************************************")
    if role.name == "teacher_and_staff":
        roles = ["staff", "teacher"]
    else:
        roles = [role.name]
    r_user = await create_random_user_data(
        roles=[f"{url_fragment}/roles/{role_}" for role_ in roles]
    )
    data = r_user.json()
    print(f"POST data={data!r}")
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
    assert len(lib_users) == 0
    schedule_delete_user(r_user.name)
    response = requests.post(
        f"{url_fragment}/users/",
        headers={"Content-Type": "application/json", **auth_header},
        data=data,
    )
    assert response.status_code == 201, f"{response.__dict__!r}"
    response_json = response.json()
    api_user = UserModel(**response_json)
    assert api_user.birthday == datetime.date.today()

    response = requests.patch(
        f"{url_fragment}/users/{r_user.name}",
        headers=auth_header,
        json={"birthday": "2013-12-11"},
    )
    assert response.status_code == 200, response.reason
    api_user = UserModel(**response.json())
    assert api_user.firstname == api_user.lastname

    response = requests.delete(
        f"{url_fragment}/users/{r_user.name}", headers=auth_header,
    )
    assert response.status_code == 204, response.reason
    async with UDM(**udm_kwargs) as udm:
        lib_users = await User.get_all(udm, "DEMOSCHOOL", f"username={r_user.name}")
    assert len(lib_users) == 0

    assert Path("/tmp", r_user.name).exists()
    Path("/tmp", r_user.name).unlink()
