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
from ucsschool.importer.models.import_user import ImportStaff, ImportUser
from ucsschool.importer.utils.user_pyhook import UserPyHook
from ucsschool.lib.models import Staff


class UserStaffPyHook(UserPyHook):
    priority = {
        "pre_create": 0,
        "post_create": 1,
        "pre_modify": 0,
        "post_modify": 0,
        "pre_remove": 0,
        "post_remove": 0,
    }

    async def pre_create(self, user: ImportUser) -> None:
        pass

    async def post_create(self, user: ImportUser) -> None:
        if isinstance(user, ImportStaff):
            udm_obj = await user.get_udm_object(self.udm)
            samba_home = await super(Staff, user).get_samba_home_path(self.udm)
            if samba_home:
                udm_obj.props.sambahome = samba_home
            profile_path = await super(Staff, user).get_profile_path(self.udm)
            if profile_path:
                udm_obj.props.profilepath = profile_path
            home_drive = super(Staff, user).get_samba_home_drive()
            if home_drive:
                udm_obj.props.homedrive = home_drive
            script_path = super(Staff, user).get_samba_netlogon_script_path()
            if script_path:
                udm_obj.props.scriptpath = script_path
            await user.modify(self.udm)

    async def pre_modify(self, user: ImportUser) -> None:
        pass

    async def post_modify(self, user: ImportUser) -> None:
        pass

    async def pre_remove(self, user: ImportUser) -> None:
        pass

    async def post_remove(self, user: ImportUser) -> None:
        pass
