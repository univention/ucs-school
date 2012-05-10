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
import univention.config_registry

from univention.lib.i18n import Translation
from univention.management.console.modules import UMC_OptionTypeError, Base
from univention.management.console.log import MODULE
from univention.management.console.protocol.definitions import *

import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display

import ucsschool.lib.internetrules as rules

from urlparse import urlparse

_ = Translation( 'ucs-school-umc-internetrules' ).translate

_filterTypes = dict(
	whitelist=rules.WHITELIST,
	blacklist=rules.BLACKLIST,
)
_filterTypesInv = dict([ (_i[1], _i[0]) for _i in _filterTypes.iteritems() ])

class Instance( SchoolBaseModule ):
	def __init__( self ):
		# initiate list of internal variables
		SchoolBaseModule.__init__(self)

	def init(self):
		SchoolBaseModule.init(self)

	def query( self, request ):
		"""Searches for internet filter rules
		requests.options = {}
		  'pattern' -- pattern to match within the rule name or the list of domains
		"""
		MODULE.info( 'internetrules.query: options: %s' % str( request.options ) )
		pattern = request.options.get('pattern', '').lower()

		def _matchDomain(domains):
			# helper function to match pattern within the list of domains
			matches = [ idom for idom in domains if pattern in idom.lower() ]
			return 0 < len(matches)

		# filter out all rules that match the given pattern
		result = [ dict(
			name=irule.name,
			type=_filterTypesInv[irule.type],
			domains=len(irule.domains),
			priority=irule.priority,
			wlan=irule.wlan,
		) for irule in rules.list() if pattern in irule.name.lower() or _matchDomain(irule.domains) ]

		MODULE.info( 'internetrules.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	def get( self, request ):
		"""Returns the specified rules
		requests.options = [ <ruleName>, ... ]
		"""
		MODULE.info( 'internetrules.get: options: %s' % str( request.options ) )
		names = request.options
		result = []
		if isinstance( names, ( list, tuple ) ):
			# fetch all rules with the given names
			names = set(names)
			result = [ dict(
				name=irule.name,
				type=_filterTypesInv[irule.type],
				domains=irule.domains,
				priority=irule.priority,
				wlan=irule.wlan,
			) for irule in rules.list() if irule.name in names ]
		else:
			MODULE.warn( 'internetrules.get: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		MODULE.info( 'internetrules.get: results: %s' % str( result ) )
		self.finished( request.id, result )

	def remove( self, request ):
		"""Removes the specified rules
		requests.options = [ { "object": <ruleName> }, ... ]
		"""
		MODULE.info( 'internetrules.remove: options: %s' % str( request.options ) )
		names = request.options
		result = []
		if isinstance( names, ( list, tuple ) ):
			# fetch all rules with the given names
			for ientry in names:
				iname = ientry.get('object')
				success = False
				if iname:
					success = rules.remove(iname)
				result.append(dict(name = iname, success = success))
		else:
			MODULE.warn( 'internetrules.get: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		MODULE.info( 'internetrules.remove: results: %s' % str( result ) )
		self.finished( request.id, result )

	@staticmethod
	def _parseRule(iprops, forceAllProperties=False):
		# validate types
		for ikey, itype in (('name', basestring), ('type', basestring), ('priority', (int, basestring)), ('wlan', bool), ('domains', list)):
			if not ikey in iprops:
				if forceAllProperties:
					# raise exception as the key is not present
					raise ValueError(_('The key "%s" has not been specified: %s') % (ikey, iprops))
				continue
			if not isinstance(iprops[ikey], itype):
				typeStr = ''
				if isinstance(itype, tuple):
					typeStr = ', '.join([ i.__name__ for i in itype])
				else:
					typeStr = itype.__name__
				raise ValueError(_('The key "%s" needs to be of type: %s') % (ikey, typeStr))

		# validate name
		if 'name' in iprops and not univention.config_registry.validateKey(iprops['name']):
			raise ValueError(_('Invalid rule name "%s". The name needs to be a string, the following special characters are not allowed: %s') % (iprops.get('name'), '!, ", §, $, %, &, (, ), [, ], {, }, =, ?, `, +, #, \', ",", ;, <, >, \\'))

		# validate type
		if 'type' in iprops and iprops['type'] not in _filterTypes:
			raise ValueError(_('Filter type is unknown: %s') % iprops['type'])

		# validate domains
		if 'domains' in iprops:
			parsedDomains = []
			for idomain in iprops['domains']:
				def _validValueChar():
					# helper function to check for invalid characters
					for ichar in idomain:
						if ichar in univention.config_registry.invalid_value_chars:
							return False
					return True

				if not isinstance(idomain, basestring) or not _validValueChar():
					raise ValueError(_('Invalid domain '))

				# parse domain
				domain = idomain
				if '://' not in domain:
					# make sure that we have a scheme defined for parsing
					MODULE.info('Adding a leading scheme for parsing of domain: %s' % idomain)
					domain = 'http://%s' % domain
				domain = urlparse(domain).hostname
				MODULE.info('Parsed domain: %s -> %s' % (idomain, domain))
				if not domain:
					raise ValueError(_('The specified domain "%s" is not valid. Please specify a valid domain name, such as "wikipedia.org", "facebook.com"') % idomain)

				# add domain to list of parsed domains
				parsedDomains.append(domain)

			# save parsed domains in the dict
			iprops['domains'] = parsedDomains

		return iprops

	def add( self, request ):
		"""Add the specified new rules:
		requests.options = [ {
			'object': {
				'name': <str>,
				'type': 'whitelist' | 'blacklist',
				'priority': <int> | <str>,
				'wlan': <bool>,
				'domains': [<str>, ...],
			}
		}, ... ]
		"""
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		# try to create all specified projects
		result = []
		for ientry in request.options:
			try:
				iprops = ientry.get('object', {})

				# make sure that the rule does not already exist
				irule = rules.load(iprops.get('name',''))
				if irule:
					raise ValueError(_('A rule with the same name does already exist: %s') % iprops.get('name',''))


				# parse the properties
				parsedProps = self._parseRule(iprops, True)

				# create a new rule from the user input
				newRule = rules.Rule(
					name=parsedProps['name'],
					type=_filterTypes[parsedProps['type']],
					priority=parsedProps['priority'],
					wlan=parsedProps['wlan'],
					domains=parsedProps['domains'],
				)

				# try to save filter rule
				newRule.save()
				MODULE.info('Created new rule: %s' % newRule)

				# everything ok
				result.append(dict(
					name = iprops['name'],
					success = True
				))
			except (ValueError, KeyError) as e:
				# data not valid... create error info
				MODULE.info('data for internet filter rule "%s" is not valid: %s' % (iprops.get('name'), e))
				result.append(dict(
					name = iprops.get('name'),
					success = False,
					details = str(e)
				))

		# return the results
		self.finished(request.id, result)

	def put( self, request ):
		"""Modify an existing rules:
		requests.options = [ {
			'object': {
				'name': <str>, 						# optional
				'type': 'whitelist' | 'blacklist', 	# optional
				'priority': <int>, 					# optional
				'wlan': <bool>,						# optional
				'domains': [<str>, ...],  			# optional
			},
			'options': {
				'name': <str>  # the original name of the object
			}
		}, ... ]
		"""
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		# try to create all specified projects
		result = []
		for ientry in request.options:
			try:
				# get properties and options from entry
				iprops = ientry.get('object', {})
				iname = None
				ioptions = ientry.get('options')
				if ioptions:
					iname = ioptions.get('name')
				if not iname:
					raise ValueError(_('No "name" attribute has been specified in the options.'))

				# make sure that the rule already exists
				irule = rules.load(iname)
				if not irule:
					raise ValueError(_('The rule does not exist and cannot be modified: %s') % iprops.get('name',''))

				# parse the properties
				parsedProps = self._parseRule(iprops)

				if iprops.get('name', iname) != iname:
					# name has been changed -> remove old rule and create a new one
					rules.remove(iname)
					irule.name = iprops['name']

				if 'type' in iprops:
					# set rule type
					irule.type = _filterTypes[iprops['type']]

				if 'priority' in iprops:
					# set priority
					irule.priority = iprops['priority']

				if 'wlan' in iprops:
					# set wlan
					irule.wlan = iprops['wlan']

				if 'domains' in iprops:
					# set domains
					irule.domains = iprops['domains']

				# try to save filter rule
				irule.save()
				MODULE.info('Saved rule: %s' % irule)

				# everything ok
				result.append(dict(
					name = iname,
					success = True
				))
			except ValueError as e:
				# data not valid... create error info
				MODULE.info('data for internet filter rule "%s" is not valid: %s' % (iprops.get('name'), e))
				result.append(dict(
					name = iprops.get('name'),
					success = False,
					details = str(e)
				))

		# return the results
		self.finished(request.id, result)

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
		ldapFilter = LDAP_Filter.forGroups(request.options.get('pattern', ''), search_base.school)
		groupresult = udm_modules.lookup( 'groups/group', None, ldap_user_read, scope = 'sub', base = base, filter = ldapFilter)

		# try to load all group rules
		allRules = rules.getGroupRuleName([ i['name'] for i in groupresult ])

		# prepare final list of dicts
		result = [ {
			'name': i['name'].replace('%s-' % search_base.school, '', 1),
			'$dn$': i.dn,
			'rule': allRules.get(i['name'], 'default') or _('-- default settings --')
		} for i in groupresult ]
		result.sort( cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'name' ] )

		MODULE.info( 'internetrules.groups_query: result: %s' % str( result ) )
		self.finished( request.id, result )

	@LDAP_Connection()
	def groups_assign( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Assigns default rules to groups:
		request.options = [ { 'group': <groupDN>, 'rule': <ruleName> }, ... ]
		"""
		MODULE.info( 'internetrules.groups_assign: options: %s' % str( request.options ) )

		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of dicts, but got: %s' % str(ids) )

		# try to load all group rules
		newRules = {}
		rmRules = []
		for ientry in request.options:
			# make sure we got a dict
			if not isinstance(ientry, dict):
				raise UMC_OptionTypeError( 'Expected list of dicts, but got: %s' % str(ids) )

			# make sure the group exists
			igrp = udm_objects.get( udm_modules.get( 'groups/group' ), None, ldap_user_read, ldap_position, ientry.get('group') )
			if not igrp:
				raise UMC_OptionTypeError( 'unknown group object' )
			igrp.open()

			# check the rule name
			irule = ientry.get('rule')
			if irule == '$default$':
				# remove the rule
				rmRules.append(igrp['name'])
			else:
				# make sure the rule name is valid
				self._parseRule(dict(name=irule))

				# add new rule
				newRules[igrp['name']] = irule

		# assign default filter rules to groups
		rules.setGroupRuleName(newRules)
		rules.unsetGroupRuleName(rmRules)

		MODULE.info( 'internetrules.groups_assign: finished' )
		self.finished( request.id, True )


