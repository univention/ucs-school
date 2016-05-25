# -*- coding: utf-8 -*-
#
# Univention UCS@School
"""
Legacy mass import class.
"""
# Copyright 2016 Univention GmbH
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

from univention.admin.uexceptions import noObject
from ucsschool.importer.mass_import.user_import import UserImport


class LegacyUserImport(UserImport):
	def detect_users_to_delete(self):
		"""
		No need to compare input and LDAP. Action was written in the CSV file
		and is already stored in user.action.
		"""
		return [user for user in self.imported_users if user.action == "D"]

	def determine_add_modify_action(self, imported_user):
		"""
		If action == "M" but user does not exist, change to "A".
		"""
		if imported_user.action == "M":
			try:
				# just test if it exists in LDAP
				imported_user.get_by_import_id(self.connection, imported_user.source_uid, imported_user.record_uid)
			except noObject:
				imported_user.action = "A"
		return super(LegacyUserImport, self).determine_add_modify_action(imported_user)
