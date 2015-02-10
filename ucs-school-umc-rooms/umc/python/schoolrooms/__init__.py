#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Manage room and their associated computers
#
# Copyright 2012-2015 Univention GmbH
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

import re

from univention.lib.i18n import Translation
from univention.management.console.modules import UMC_CommandError
from univention.management.console.log import MODULE

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule, LDAP_Filter, USER_READ, USER_WRITE

from ucsschool.lib.models import ComputerRoom
from ucsschool.lib.models.utils import add_module_logger_to_schoollib

_ = Translation( 'ucs-school-umc-rooms' ).translate

class Instance( SchoolBaseModule ):
	def init(self):
		super(Instance, self).init()
		add_module_logger_to_schoollib()

	@LDAP_Connection()
	def computers( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""
		requests.options = {}
		  'pattern' -- search pattern for name (default: '')
		  'school'
		"""
		MODULE.info( 'schoolrooms.query: options: %s' % str( request.options ) )
		pattern = request.options.get('pattern', '')
		ldapFilter = LDAP_Filter.forComputers(pattern)

		objs = udm_modules.lookup( 'computers/computer', None, ldap_user_read, scope = 'one', base = search_base.computers, filter = ldapFilter)
		result = [ {
			'label': i['name'],
			'id': i.dn
		} for i in objs ]
		result = sorted( result, cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'label' ] )

		MODULE.info( 'schoolrooms.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	@LDAP_Connection()
	def query( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""
		requests.options = {}
		  'name' -- search pattern for name or description (default: '')
		  'school'
		"""
		MODULE.info( 'schoolrooms.query: options: %s' % str( request.options ) )
		pattern = request.options.get('pattern', '')
		ldapFilter = LDAP_Filter.forGroups(pattern, search_base.school)

		objs = udm_modules.lookup( 'groups/group', None, ldap_user_read, scope = 'one', base = search_base.rooms, filter = ldapFilter)
		name_pattern = re.compile('^%s-' % (re.escape(search_base.school)), flags=re.I)
		result = [ {
			'name': name_pattern.sub('', i['name']),
			'description': i.oldinfo.get('description',''),
			'$dn$': i.dn
		} for i in objs ]
		result = sorted( result, cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'name' ] )

		MODULE.info( 'schoolrooms.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	@LDAP_Connection()
	def get(self, request, search_base=None, ldap_user_read=None, ldap_position=None):
		"""Returns the objects for the given IDs

		requests.options = [ <ID>, ... ]

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info('schoolrooms.get: options: %s' % str(request.options))

		# open the specified room
		room = ComputerRoom.from_dn(request.options[0], None, ldap_user_read)
		result = room.to_dict()
		result['computers'] = result.get('hosts')
		self.finished(request.id, [result])

	@LDAP_Connection(USER_READ, USER_WRITE)
	def add(self, request, search_base=None, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
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
	def put(self, request, search_base=None, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
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
	def remove(self, request, search_base=None, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
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
			self.finished(request.id, [{'success' : False, 'message' : str(e)}])

		self.finished(request.id, [{'success' : True}])

