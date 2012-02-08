#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Administration of groups
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

_ = Translation( 'ucs-school-umc-groups' ).translate


class Instance( SchoolBaseModule ):
	def __init__( self ):
		# initiate list of internal variables
		SchoolBaseModule.__init__(self)

	def init(self):
		SchoolBaseModule.init(self)

	@LDAP_Connection()
	def users( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		# parse group parameter
		group = request.options.get('group')
		user_type = None
		if not group or group == 'None':
			group = None
		elif group.lower() == '$teachers$':
			group = None
			user_type = 'teacher'
		elif group.lower() == '$pupils$':
			group = None
			user_type = 'pupil'

		result = [ {
			'id': i.dn,
			'label': Display.user(i)
		} for i in self._users( ldap_user_read, search_base, group = group, user_type = user_type, pattern = request.options.get('pattern') ) ]
		self.finished( request.id, result )

	@LDAP_Connection()
	def query( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Searches for entries:

		requests.options = {}
		  'pattern' -- search pattern (default: '')
		  'school' -- particular school name as internal base for the search parameters
		  		  (default: automatically chosen search base in LDAP_Connection)

		return: [ { '$dn$' : <LDAP DN>, 'name': '...', 'description': '...' }, ... ]
		"""
		MODULE.info( 'schoolgroups.query: options: %s' % str( request.options ) )
		
		# get the correct base for the search
		base = search_base.classes
		if request.flavor == 'workgroup':
			# only show workgroups
			base = search_base.workgroups

		# LDAP search for groups
		ldapFilter = LDAP_Filter.forGroups(request.options.get('pattern', ''))
		MODULE.info('### filter:%s' % ldapFilter)
		groupresult = udm_modules.lookup( 'groups/group', None, ldap_user_read, scope = 'one', base = base, filter = ldapFilter)
		grouplist = [ { 
			'name': i['name'],
			'description': i.oldinfo.get('description',''),
			'$dn$': i.dn
		} for i in groupresult ]
		result = sorted( grouplist, cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'name' ] )

		MODULE.info( 'schoolgroups.query: result: %s' % str( result ) )
		self.finished( request.id, result )

	def get( self, request ):
		"""Returns the objects for the given IDs

		requests.options = [ <DN>, ... ]

		return: [ { '$dn$' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info( 'schoolgroups.get: options: %s' % str( request.options ) )
		ids = request.options
		result = []
		if isinstance( ids, ( list, tuple ) ):
			ids = set(ids)
			result = [ ]
		else:
			MODULE.warn( 'schoolgroups.get: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )
		MODULE.info( 'schoolgroups.get: results: %s' % str( result ) )
		self.finished( request.id, result )

