#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Manage reservations for computer rooms
#
# Copyright 2012 Univention GmbH
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

from univention.management.console.config import ucr

from univention.lib.i18n import Translation
from univention.management.console.modules import UMC_OptionTypeError, Base
from univention.management.console.log import MODULE
from univention.management.console.protocol.definitions import *

import univention.admin.modules as udm_modules

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display

_ = Translation( 'ucs-school-umc-roomreservation' ).translate
import uuid

class Instance( SchoolBaseModule ):
	# list of dummy entries
	entries = map(lambda x: { 'id': str(uuid.uuid4()), 'name': x[0], 'color': x[1] }, [
		['Zackary Cavaco', 'Blue'],
		['Shon Hodermarsky', 'Green'],
		['Jude Nachtrieb', 'Green'],
		['Najarian', 'Blue'],
		['Oswaldo Lefeld', 'Blue'],
		['Vannessa Kopatz', 'Orange'],
		['Marcellus Hoga', 'Orange'],
		['Violette Connerty', 'Orange'],
		['Lucina Jeanquart', 'Blue'],
		['Mose Maslonka', 'Green'],
		['Emmie Dezayas', 'Green'],
		['Douglass Glaubke', 'Green'],
		['Deeann Delilli', 'Blue'],
		['Janett Cooch', 'Orange'],
		['Ike Collozo', 'Orange'],
		['Tamala Pecatoste', 'Orange'],
		['Shakira Cottillion', 'Blue'],
		['Colopy', 'Blue'],
		['Vivan Noggles', 'Green'],
		['Shawnda Hamalak', 'Blue'],
	])

	def __init__( self ):
		# initiate list of internal variables
		SchoolBaseModule.__init__(self)

	def init(self):
		SchoolBaseModule.init(self)

	def colors( self, request ):
		"""Returns a list of all existing colors."""
		MODULE.info( 'roomreservation.colors: options: %s' % str( request.options ) )
		allColors = set(map(lambda x: x['color'], Instance.entries))
		allColors = map(lambda x: { 'id': x, 'label': x }, allColors)
		allColors.append({ 'id': 'None', 'label': _('All colors') })
		MODULE.info( 'roomreservation.colors: result: %s' % str( allColors ) )
		self.finished(request.id, allColors)

	def query( self, request ):
		"""Searches for entries in a dummy list

		requests.options = {}
		  'name' -- search pattern for name (default: '')
		  'color' -- color to match, 'None' for all colors (default: 'None')

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info( 'roomreservation.query: options: %s' % str( request.options ) )
		color = request.options.get('color', 'None')
		pattern = request.options.get('name', '')
		result = filter(lambda x: (color == 'None' or color == x['color']) and x['name'].find(pattern) >= 0, Instance.entries)
		MODULE.info( 'roomreservation.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	def get( self, request ):
		"""Returns the objects for the given IDs

		requests.options = [ <ID>, ... ]

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info( 'roomreservation.get: options: %s' % str( request.options ) )
		ids = request.options
		result = []
		if isinstance( ids, ( list, tuple ) ):
			ids = set(ids)
			result = filter(lambda x: x['id'] in ids, Instance.entries)
		else:
			MODULE.warn( 'roomreservation.get: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )
		MODULE.info( 'roomreservation.get: results: %s' % str( result ) )
		self.finished( request.id, result )

