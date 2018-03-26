# -*- coding: utf-8 -*-
#
# Copyright 2018 Univention GmbH
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
# you and Univention.
#
# This program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import
from univention.listener import ListenerModuleHandler


class UcsschoolAdminObjectType(ListenerModuleHandler):
	class Configuration:
		name = 'ucsschool_admin_object_type'
		description = 'Add attribute and OC to UCS@school admin users and groups'
		# admin user must be teacher and/or staff
		ldap_filter = '(|(objectClass=ucsschoolTeacher)(objectClass=ucsschoolStaff))'
		attributes = ['objectClass']

	def create(self, dn, new):
		new_object_types = new.get('ucsschoolObjectType', [])
		if 'ucsschoolAdministrator' in new['objectClass'] and 'administrator_user' not in new_object_types:
			self.logger.info('Adding "administrator_user" to "ucsschoolObjectType" property of %r.', dn)
			self.lo.modify(
				dn,
				[('ucsschoolObjectType', new_object_types, new_object_types + ['administrator_user'])]
			)

	def modify(self, dn, old, new, old_dn):
		new_object_types = new.get('ucsschoolObjectType', [])
		if 'ucsschoolAdministrator' in new['objectClass'] and 'administrator_user' not in new_object_types:
			self.logger.info('Adding "administrator_user" to "ucsschoolObjectType" property of %r.', dn)
			self.lo.modify(
				dn,
				[('ucsschoolObjectType', new_object_types, new_object_types + ['administrator_user'])]
			)
		elif 'ucsschoolAdministrator' not in new['objectClass'] and 'administrator_user' in new_object_types:
			self.logger.info('Removing "administrator_user" from "ucsschoolObjectType" property of %r.', dn)
			object_types_without_admin = list(new_object_types)
			object_types_without_admin.remove('administrator_user')
			self.lo.modify(
				dn,
				[('ucsschoolObjectType', new_object_types, object_types_without_admin)]
			)
