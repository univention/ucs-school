#!/usr/bin/python2.6
#
# UCS@school OU hook
#
# Copyright (C) 2014 Univention GmbH
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

OBJECTCLASS_SCHOOLOU = 'ucsschoolOrganizationalUnit'
OPTION_SCHOOLOU = 'UCSschool-School-OU'


class schoolOU(simpleHook):

	def hook_open(self, module):
		ud.debug(ud.ADMIN, ud.ALL, 'admin.hook.schoolOU: _open called')

		objectClass = module.oldattr.get('objectClass', [])

		# FIXME: handlers.contains.ou.object does not have options
		if not hasattr(module, 'options'):
			module.options = []

		if OBJECTCLASS_SCHOOLOU in objectClass and OPTION_SCHOOLOU not in module.options:
			module.options.append(OPTION_SCHOOLOU)

	def hook_ldap_modlist(self, module, ml=[]):
		"""Add or remove objectClass ucsschoolOrganizationalUnit when UCSschool-School-OU is enabled or disabled."""
		ud.debug(ud.ADMIN, ud.ALL, 'admin.hook.schoolOU.modlist called')

		# compute new accumulated objectClass
		old_ocs = module.oldattr.get('objectClass', [])
		ocs = set(old_ocs)

		is_school = OPTION_SCHOOLOU in module.options

		for modification in ml[:]:
			attr, remove_val, add_val = modification

			if attr == 'objectClass':
				if not isinstance(remove_val, list):
					remove_val = set([remove_val])
				ocs -= set(remove_val)

				if not isinstance(add_val, list):
					add_val = set([add_val])
					add_val.discard('')
				ocs |= set(add_val)

				ml.remove(modification)

			elif not is_school and attr in ('ucsschoolHomeShareFileServer', 'ucsschoolClassShareFileServer'):
				ml.remove(modification)

		if is_school:
			ocs.add(OBJECTCLASS_SCHOOLOU)
		else:
			ocs.discard(OBJECTCLASS_SCHOOLOU)
			for attr in ('ucsschoolHomeShareFileServer', 'ucsschoolClassShareFileServer'):
				ml.append((attr, module.oldattr.get(attr, ''), ''))

		ml.append(('objectClass', old_ocs, list(ocs)))

		return ml
