#!/usr/bin/python2.7
#
# UCS@school Admin Group Hook
#
# Copyright (C) 2016 Univention GmbH
#
# http://www.univention.de/
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

from univention.admin.hook import simpleHook
import univention.debug as ud


class schoolAdminGroup(simpleHook):

	def hook_open(self, module):
		ud.debug(ud.ADMIN, ud.ALL, 'admin.hook.schoolAdminGroup: _open called')

		objectClass = module.oldattr.get('objectClass', [])
		name = 'ucsschoolAdministratorGroup'
		if name in objectClass and name not in module.options:
			module.options.append(name)
