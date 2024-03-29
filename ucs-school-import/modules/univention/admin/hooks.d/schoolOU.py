#!/usr/bin/python3
#
# UCS@school OU hook
#
# Copyright (C) 2014-2024 Univention GmbH
#
# https://www.univention.de/
#
# All rights reserved.
#
# source code of this program is made available
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
# /usr/share/common-licenses/AGPL-3. If not, see <http://www.gnu.org/licenses/>.

import univention.debug as ud
from univention.admin.hook import simpleHook

OBJECTCLASS_SCHOOLOU = b"ucsschoolOrganizationalUnit"
OPTION_SCHOOLOU = "UCSschool-School-OU"
ATTRIBUTE_LIST = ("ucsschoolHomeShareFileServer", "ucsschoolClassShareFileServer", "displayName")


class schoolOU(simpleHook):
    def hook_ldap_modlist(self, module, ml=None):
        """
        Add or remove objectClass ucsschoolOrganizationalUnit when UCSschool-School-OU is enabled or
        disabled.
        """
        ud.debug(ud.ADMIN, ud.ALL, "admin.hook.schoolOU.modlist called")

        if ml is None:
            ml = []

        # compute new accumulated objectClass
        old_ocs = module.oldattr.get("objectClass", [])
        ocs = set(old_ocs)

        is_school = OPTION_SCHOOLOU in module.options

        for modification in ml[:]:
            attr, remove_val, add_val = modification

            if attr == "objectClass":
                if not isinstance(remove_val, list):
                    remove_val = {remove_val}
                ocs -= set(remove_val)

                if not isinstance(add_val, list):
                    add_val = {add_val}
                    add_val.discard(b"")
                ocs |= set(add_val)

                ml.remove(modification)

            elif not is_school and attr in ATTRIBUTE_LIST:
                ml.remove(modification)

        if is_school:
            ocs.add(OBJECTCLASS_SCHOOLOU)
        else:
            ocs.discard(OBJECTCLASS_SCHOOLOU)
            for attr in ATTRIBUTE_LIST:
                ml.append((attr, module.oldattr.get(attr, []), None))

        ml.append(("objectClass", old_ocs, list(ocs)))
        return ml
