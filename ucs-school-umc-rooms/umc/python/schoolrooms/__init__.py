#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Manage room and their associated computers
#
# Copyright 2012-2016 Univention GmbH
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

from univention.lib.i18n import Translation
from univention.management.console.modules import UMC_CommandError
from univention.management.console.modules.sanitizers import StringSanitizer
from univention.management.console.modules.decorators import sanitize
from univention.management.console.log import MODULE

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule, LDAP_Filter, USER_READ, USER_WRITE
from ucsschool.lib.models import ComputerRoom, SchoolComputer
from ucsschool.lib.models.utils import add_module_logger_to_schoollib

_ = Translation('ucs-school-umc-rooms').translate


class Instance(SchoolBaseModule):

	def init(self):
		super(Instance, self).init()
		add_module_logger_to_schoollib()

	@sanitize(school=StringSanitizer(required=True), pattern=StringSanitizer(default=''))
	@LDAP_Connection()
	def computers(self, request, ldap_user_read=None, ldap_position=None):
		pattern = LDAP_Filter.forComputers(request.options.get('pattern', ''))

		result = [{
			'label': x.name,
			'id': x.dn
		} for x in SchoolComputer.get_all(ldap_user_read, request.options['school'], pattern)]
		result = sorted(result, cmp=lambda x, y: cmp(x.lower(), y.lower()), key=lambda x: x['label'])  # TODO: still necessary?

		self.finished(request.id, result)

	@sanitize(school=StringSanitizer(required=True), pattern=StringSanitizer(default=''))
	@LDAP_Connection()
	def query(self, request, ldap_user_read=None, ldap_position=None):
		school = request.options['school']
		pattern = LDAP_Filter.forGroups(request.options.get('pattern', ''), school)

		result = [{
			'name': x.get_relative_name(),
			'description': x.description or '',
			'$dn$': x.dn,
		} for x in ComputerRoom.get_all(ldap_user_read, school, pattern)]
		result = sorted(result, cmp=lambda x, y: cmp(x.lower(), y.lower()), key=lambda x: x['name'])  # TODO: still necessary?

		self.finished(request.id, result)

	@LDAP_Connection()
	def get(self, request, ldap_user_read=None, ldap_position=None):
		MODULE.info('schoolrooms.get: options: %s' % str(request.options))

		# open the specified room
		room = ComputerRoom.from_dn(request.options[0], None, ldap_user_read)
		result = room.to_dict()
		result['computers'] = result.get('hosts')
		self.finished(request.id, [result])

	@LDAP_Connection(USER_READ, USER_WRITE)
	def add(self, request, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		"""Adds a new room

		requests.options = [ { $dn$ : ..., }, ... ]

		return: True|<error message>
		"""
		if not request.options:
			raise UMC_CommandError('Invalid arguments')

		group_props = request.options[0].get('object', {})
		group_props['hosts'] = group_props.get('computers')
		room = ComputerRoom(**group_props)
		if room.get_relative_name() == room.name:
			room.name = '%(school)s-%(name)s' % group_props
			room.set_dn(room.dn)
		success = room.create(ldap_user_write)
		self.finished(request.id, [success])

	@LDAP_Connection(USER_READ, USER_WRITE)
	def put(self, request, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		"""Modify an existing room

		requests.options = [ { object : ..., options : ... }, ... ]

		return: True|<error message>
		"""
		if not request.options:
			raise UMC_CommandError('Invalid arguments')

		group_props = request.options[0].get('object', {})
		group_props['hosts'] = group_props.get('computers')

		room = ComputerRoom(**group_props)
		if room.get_relative_name() == room.name:
			room.name = '%(school)s-%(name)s' % group_props
		room.set_dn(group_props['$dn$'])
		room.modify(ldap_user_write)

		self.finished(request.id, [True])

	@LDAP_Connection(USER_READ, USER_WRITE)
	def remove(self, request, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		"""Deletes a room

		requests.options = [ <LDAP DN>, ... ]

		return: True|<error message>
		"""
		MODULE.info('schoolrooms.remove: object: %s' % str(request.options))
		if not request.options:
			raise UMC_CommandError('Invalid arguments')

		room_dn = request.options[0].get('object', {})
		room_obj = udm_modules.get('groups/group').object(None, ldap_user_write, ldap_position, room_dn[0])

		try:
			room_obj.remove()
		except udm_exceptions.base as e:
			self.finished(request.id, [{'success': False, 'message': str(e)}])

		self.finished(request.id, [{'success': True}])
