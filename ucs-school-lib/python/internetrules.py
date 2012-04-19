#!/usr/bin/python2.6
# -*- coding: iso-8859-15 -*-
#
# Univention Management Console
#  module: Internet Rules Module
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
from univention.management.console.log import MODULE
import univention.config_registry

import re

# regular expression to match UCR variables for filter properties
_regFilterNames = re.compile(r'^proxy/filter/setting(?P<userPrefix>-user)?/(?P<name>[^/]*)/(?P<property>[^/]*)(/(?P<listType>[^/]*)/(?P<index>[^/]*))?$')

WHITELIST, BLACKLIST, GREYLIST = range(3)
_filterTypes = {
	'blacklist-pass': BLACKLIST,
	'whitelist-block': WHITELIST,
	'whitelist-blacklist-pass': GREYLIST,
}
_filterTypesInv = dict([ (_i[1], _i[0]) for _i in _filterTypes.iteritems() ])
_listTypes = {
	'blacklisted': BLACKLIST,
	'whitelisted': WHITELIST,
}
_listTypesInv = dict([ (_i[1], _i[0]) for _i in _listTypes.iteritems() ])

class Rule(object):

	def __init__(self, name, type=WHITELIST, priority=5, wlan=False, domains=[], userRule=False):
		self.name = name
		self.type = type
		self.priority = priority
		self.wlan = wlan
		self.domains = domains
		# proxy/filter/setting/* or proxy/filter/setting-user/* ?
		self.userRule = userRule

	def __str__(self):
		return '<rule:%s type:%s priority:%s>' % (self.name, self.type, self.priority)

	def __repr__(self):
		return self.__str__()

	def _getIndexedDomains(self, type):
		return [ i for i in sorted(self._domains) if i[0] >= 0 and i[2] == type ]

	def _getAppendedDomains(self, type):
		return [ i for i in self._domains if i[0] < 0 and i[2] == type ]

	def _getDomains(self, type):
		return [ i for i in self._getIndexedDomains(type) + self._getAppendedDomains(type) ]

	@property
	def domains(self):
		'''Return list of all domains, the order respects the indeces.
		Show only the entries that match the current filter type.'''
		return [ i[1] for i in self._getDomains(self.type) ]

	@domains.setter
	def domains(self, domains):
		'''domains can be a list of strings or a list of index-string-type tuples.'''
		self._domains = []
		for i in domains:
			if isinstance(i, str):
				self._domains.append((-1, i, self.type))
			else:
				self._domains.append(i)

	def addDomain(self, domain, idx=-1, listType=None):
		'''add a new domain with an optional fixed index and list type'''
		if listType not in _listTypesInv:
			listType = self.type
		self._domains.append((idx, domain, listType))

	def save(self):
		'''Save the current rule as UCR variables. If the rule already exists,
		only the changed properties will be saved. In case the rules are similar,
		no changes will be done.'''
		# load original rule
		orgRule = load(self.name)
		if orgRule:
			# for comparing domains, make sure that we look at
			orgRule.type = self.type

		# prepare for saving filter properties
		vars = []
		rmVars = []
		prefix = 'proxy/filter/setting/%s' % self.name
		if self.userRule:
			# this is a user rule which has a different prefix
			prefix = 'proxy/filter/setting-user/%s' % self.name
		if not orgRule or orgRule.type != self.type:
			vars.append('%s/filtertype=%s' % (prefix, _listTypesInv[self.type]))
		if not orgRule or orgRule.priority != self.priority:
			vars.append('%s/priority=%s' % (prefix, self.priority))
		if not orgRule or orgRule.wlan != self.wlan:
			wlan = 'true'
			if not self.wlan:
				wlan = 'false'
			vars.append('%s/wlan=%s' % (prefix, wlan))

		# iterate over all blacklist and whitelist entries
		for itype in _listTypes.values():
			# saving domains is a bit more tricky as we need to take care of the indeces
			# ... get the original list of domains with indeces and sorted
			orgDomains = []
			if orgRule:
				orgDomains = orgRule._getIndexedDomains(itype) + orgRule._getAppendedDomains(itype)

			# prepare list of current domains with indeces
			domains = [ i[1] for i in self._getDomains(itype) ]
			domains = [ (i + 1, domains[i], itype) for i in range(len(domains)) ]

			# find the entries that need to be changed/added
			domainPrefix = '%s/domain/%s' % (prefix, _listTypesInv[itype])
			iorg = 0
			inew = 0
			while inew < len(domains):
				if iorg >= len(orgDomains) or orgDomains[iorg] != domains[inew]:
					vars.append('%s/%s=%s' % (domainPrefix, domains[inew][0], domains[inew][1]))

				# increment iterators
				if iorg < len(orgDomains) and orgDomains[iorg][0] <= domains[inew][0] and orgDomains[iorg][0] >= 0:
					iorg += 1
				inew += 1

			# collect entries that need to be removed
			while iorg < len(orgDomains):
				rmVars.append('%s/%s' % (domainPrefix, orgDomains[iorg][0]))
				iorg += 1

		# write changes
		if vars:
			univention.config_registry.handler_set(vars)
		if rmVars:
			univention.config_registry.handler_unset(rmVars)

def findUCRVariables(filterName=None, userRule=False):
	'''Returns a dict of all UCR variables or all variables matching the
	specified rule name.'''
	# refresh internal UCR cache
	ucr.load()

	# iterate over all UCR variables
	vars = {}
	for k, v in ucr.items():
		imatch = _regFilterNames.match(k)
		if imatch:
			# we found a filter variable
			iname = imatch.group('name')
			if not iname or (filterName and filterName != iname):
				# empty name or name does not match the specified filter
				continue

			# see whether this is a user specific rule or a general rule
			if userRule != bool(imatch.group('userPrefix')):
				continue

			# bingo, we got a match :)
			vars[k] = v

	# return all matched variables
	return vars

def remove(name, userRule=False):
	'''Removes the UCR variables corresponding to the specified rule.'''
	if not name:
		return False
	rmVars = findUCRVariables(name, userRule).keys()
	if rmVars:
		univention.config_registry.handler_unset(rmVars)
		return True
	return False

def load(name, userRule=False):
	'''Wrapper for list(name).'''
	return list(name, userRule)

def list(filterName=None, userRule=False):
	'''Returns a list of all existing rules. If name is given, returns only the
	rule matching the specified name or None. userRule specifies whether all
	common rules (=False) or only user-specific rules (=True) are listed.
	If filterName is specified, only rule matching this name is returned as
	single object (not as list!).'''

	# iterate over all UCR variables
	rules = {}
	for k, v in findUCRVariables(filterName, userRule).iteritems():
		imatch = _regFilterNames.match(k)
		if not imatch:
			# should not happen
			continue

		# get filter name
		iname = imatch.group('name')

		# get the rule from our cache
		irule = rules.get(iname, Rule(iname))

		# update the rule with the given property
		# NOTE: URL black-/whitelists are not supported anymore, only domain lists
		iproperty = imatch.group('property')
		if iproperty == 'filtertype':
			if v not in _filterTypes:
				irule.type = WHITELIST
				MODULE.error('Unknown filtertype "%s" for rule "%s", using whitelist as default.' % (v, irule))
			else:
				irule.type = _filterTypes[v]
		elif iproperty == 'priority':
			try:
				irule.priority = int(v)
			except ValueError as e:
				irule.priority = 5
				MODULE.error('Could not parse priority "%s" for rule "%s", using default value "5".' % (v, irule))
		elif iproperty == 'wlan':
			irule.wlan = ucr.is_true(k)
		elif iproperty == 'domain':
			# get the index
			idx = -1
			try:
				idx = int(imatch.group('index'))
			except ValueError as e:
				pass

			# get list type (blacklisted or whitelisted)
			listType = _listTypes.get(imatch.group('listType'))

			# add domain to list of domains
			irule.addDomain(v, idx, listType)

		# save the rule back to our cache
		rules[iname] = irule

	if filterName:
		# handle case for filtered search
		if not len(rules):
			# no match
			return None
		# return single element
		return rules.items()[0][1]

	return rules.values()


