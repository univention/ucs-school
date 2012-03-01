#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Defines and manages internet rules
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

_ = Translation( 'ucs-school-umc-internetrules' ).translate

class Instance( SchoolBaseModule ):
	# list of dummy entries
	entries = map(lambda x: { 'id': x[0], 'name': x[0], 'type': x[1], 'groups': x[2], 'domains': x[3] }, [
		[ 'Wikipedia', 'whitelist', '10d, Redations AG', [ 'wikipedia.org' ] ],
		[ 'Kein facebook', 'blacklist', 'Informatik AK', [ 'facebook.com', 'facebook.de' ] ],
		[ 'Youtube', 'whitelist', 'Filme AG', [ 'youtube.com', 'vimeo.com' ] ],
		[ 'default', 'blacklist', '', [ 'facebook.com', 'youtube.com' ] ]
	])

	def __init__( self ):
		# initiate list of internal variables
		SchoolBaseModule.__init__(self)

	def init(self):
		SchoolBaseModule.init(self)

	def query( self, request ):
		"""Searches for entries in a dummy list

		requests.options = {}
		  'name' -- search pattern for name (default: '')
		  'color' -- color to match, 'None' for all colors (default: 'None')

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info( 'internetrules.query: options: %s' % str( request.options ) )
		pattern = request.options.get('name', '')
		result = filter(lambda x: x['name'].find(pattern) >= 0, Instance.entries)
		MODULE.info( 'internetrules.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	def get( self, request ):
		"""Returns the objects for the given IDs

		requests.options = [ <ID>, ... ]

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info( 'internetrules.get: options: %s' % str( request.options ) )
		ids = request.options
		result = []
		if isinstance( ids, ( list, tuple ) ):
			ids = set(ids)
			result = filter(lambda x: x['id'] in ids, Instance.entries)
		else:
			MODULE.warn( 'internetrules.get: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )
		MODULE.info( 'internetrules.get: results: %s' % str( result ) )
		self.finished( request.id, result )

	@LDAP_Connection()
	def groups_query( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Searches for entries:

		requests.options = {}
		  'pattern' -- search pattern (default: '')
		  'school' -- particular school name as internal base for the search parameters
		  		  (default: automatically chosen search base in LDAP_Connection)

		return: [ { '$dn$' : <LDAP DN>, 'name': '...', 'description': '...' }, ... ]
		"""
		MODULE.info( 'internetrules.groups_query: options: %s' % str( request.options ) )

		# LDAP search for groups
		base = search_base.classes
		ldapFilter = LDAP_Filter.forGroups(request.options.get('pattern', ''))
		groupresult = udm_modules.lookup( 'groups/group', None, ldap_user_read, scope = 'sub', base = base, filter = ldapFilter)
		grouplist = [ { 
			'name': i['name'],
			'$dn$': i.dn,
			'rule': 'default'
		} for i in groupresult ]
		result = sorted( grouplist, cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'name' ] )

		MODULE.info( 'internetrules.groups_query: result: %s' % str( result ) )
		self.finished( request.id, result )

