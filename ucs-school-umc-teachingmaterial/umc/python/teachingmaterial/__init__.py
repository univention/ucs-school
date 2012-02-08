#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   
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

import uuid

_ = Translation( 'ucs-school-umc-teachingmaterial' ).translate

class Instance( SchoolBaseModule ):
	# list of dummy entries
	entries = map(lambda x: { 
		'id': str(uuid.uuid4()), 
		'name': x[0], 
		'description': x[1],
		'owner': x[2],
		'nusers': x[3],
		'files': x[4],
		'nfiles': len(x[4]),
		'distributed': x[5]
	}, [
		['Informatik-AG', 'Testprojekt der Informatik AG bei', 'Hans Schneemann', 23, ['test.png'], True],
		['Klassenarbeit 11d', 'Klassenarbeit für die Klasse 11d', 'Daniel Krause', 12, ['formular.doc', 'anschreiben.doc'], False],
		['Vokabeltest', 'Französisch Vokabeltest (Fr. Schneemann)', 'Silvia Schneemann', 18, ['vokabeln.xls'], False],
		['Projektarbeit', 'Projektarbeit Leistungskurs Schwimmen', 'Franz Lehmann', 4, ['film.avi', 'aufsatz_vorlage.doc'], True]
	])

	def __init__( self ):
		SchoolBaseModule.__init__(self)

	def init(self):
		SchoolBaseModule.init(self)

	@LDAP_Connection()
	def users( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		# parse group parameter
		group = request.options.get('group')
		if not group or group == 'None':
			group = None

		# get list of all users matching the given pattern
		result = [ {
			'id': i.dn,
			'label': Display.user(i)
		} for i in self._users( ldap_connection, search_base, group = group, user_type = 'pupil', pattern = request.options.get('pattern') ) ]
		self.finished( request.id, result )

	def query( self, request ):
		"""Searches for entries in a dummy list

		requests.options = {}
		  'pattern' -- search pattern for name (default: '')

		###return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info( 'teachingmaterial.query: options: %s' % str( request.options ) )
		pattern = request.options.get('pattern', '').lower()
		result = [ i for i in Instance.entries if i['name'].lower().find(pattern) >= 0 or i['description'].lower().find(pattern) >= 0 ]
		MODULE.info( 'teachingmaterial.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	def get( self, request ):
		"""Returns the objects for the given IDs

		requests.options = [ <ID>, ... ]

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info( 'teachingmaterial.get: options: %s' % str( request.options ) )
		ids = request.options
		result = []
		if isinstance( ids, ( list, tuple ) ):
			ids = set(ids)
			result = filter(lambda x: x['id'] in ids, Instance.entries)
		else:
			MODULE.warn( 'teachingmaterial.get: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )
		MODULE.info( 'teachingmaterial.get: results: %s' % str( result ) )
		self.finished( request.id, result )

