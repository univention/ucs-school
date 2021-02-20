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

from ucsschool.importer.utils.user_pyhook import UserPyHook
from ucsschool.lib.models.user import Staff


class UserStaffPyHook(UserPyHook):
    priority = {
        "pre_create": 1000,
        "post_create": None,
        "pre_modify": 1000,
        "post_modify": None,
        "pre_remove": None,
        "post_remove": None,
    }

    def pre_create(self, user):
        if isinstance(user, Staff):
            user.udm_properties["sambahome"] = super(Staff, user).get_samba_home_path(self.lo)
            user.udm_properties["profilepath"] = super(Staff, user).get_profile_path(self.lo)
            user.udm_properties["scriptpath"] = super(Staff, user).get_samba_netlogon_script_path()
            user.udm_properties["homedrive"] = super(Staff, user).get_samba_home_drive()

    pre_modify = pre_create  # this is for the case of a school change
