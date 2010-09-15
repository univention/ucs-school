#!/usr/bin/python2.4
#
# Univention Management Console Module
#  module: Proxy Settings Module
#
# Copyright 2007-2010 Univention GmbH
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

import univention.management.console as umc
import univention.management.console.categories as umcc
import univention.management.console.protocol as umcp
import univention.management.console.handlers as umch
import univention.management.console.dialog as umcd
import univention.management.console.tools as umct

import univention.debug as ud
import univention.config_registry
import univention.uldap

import notifier
import notifier.popen

import os, re
import urllib
import inspect
import fnmatch

import _schoolldap
import _revamp
import _types

_ = umc.Translation( 'univention.management.console.handlers.proxysettings' ).translate

DEFAULT_SETTINGS_FILTERTYPE = 'whitelist-blacklist-pass'

icon = 'proxysettings/module'
short_description = _( 'Proxy Filter Settings' )
long_description = _( 'Proxy Filter Settings' )
categories = [ 'all' ]

command_description = {
	'proxysettings/show/profiles': umch.command(
		short_description = _( 'Proxy Filter Profile' ),
		long_description = _( 'List proxy filter profiles' ),
		method = 'proxysettings_show_profiles',
		values = { 'filter' : _types.profile },
		startup = True,
		priority = 95,
	),
	'proxysettings/show/profileassignment': umch.command(
		short_description = _( 'Assign Profiles' ),
		long_description = _( 'Assign proxy filter profiles to groups' ),
		method = 'proxysettings_show_profileassignment',
		values = {
					'ou' : _types.ou,
					'grp': _types.group,
					},
		startup = True,
		priority = 94,
	),
	'proxysettings/set/profileassignment': umch.command(
		short_description = _( 'Assign Profile' ),
		long_description = _( 'Assign proxy filter profile to group' ),
		method = 'proxysettings_set_profileassignment',
		values = {
					'ou' : _types.ou,
					'grp': _types.group,
					'profile': _types.emptystring,
					},
		priority = 90,
	),
	'proxysettings/remove/profile': umch.command(
		short_description = _( 'Remove Proxy Filter Profile' ),
		long_description = _( 'Remove proxy filter profile' ),
		method = 'proxysettings_remove_profile',
		values = { 'profile' : _types.profile },
		priority = 90,
	),
	'proxysettings/create/sitefilter': umch.command(
		short_description = _( 'Profile [default]' ),
		long_description = _( 'List (un)blocked websites' ),
		method = 'proxysettings_create_sitefilter',
		values = {
					'profile' : _types.profile,
					'filtertype': _types.filtertype,
					'kind' : _types.kind,
					'color' : _types.color,
					'filter' : _types.filter },
		#startup = True,
		#priority = 85,
	),
	'proxysettings/show/sitefilters': umch.command(
		short_description = _( 'Profile [default]' ),
		long_description = _( 'List (un)blocked websites' ),
		method = 'proxysettings_show_sitefilters',
		values = {
					'profile' : _types.profile,
					'filtertype': _types.filtertype,
					'filtertypetext': _types.filtertype_text,
					'kind' : _types.kind,
					'color' : _types.color,
					'filter' : _types.filter },
		#startup = True,
		#priority = 85,
	),
	'proxysettings/set/filteritems': umch.command(
		short_description = _( 'Set URL Filter' ),
		long_description = _( 'Set URL filter' ),
		method = 'proxysettings_set_filteritems',
		values = {
					'profile' : _types.profile,
					'whitelistitems' : _types.filteritems,
					'blacklistitems' : _types.filteritems,
					},
		priority = 80,
	),
}

class handler( umch.simpleHandler, _revamp.Web  ):

	# __ReservedProfileNames = [ 'domain', 'url', 'hostgroup' ]

	def __init__( self ):
		global command_description
		umch.simpleHandler.__init__( self, command_description )
		_revamp.Web.__init__( self )
		self.ldap = _schoolldap.SchoolLDAPConnection()
		self._debug( ud.INFO, 'availableOU=%s' % self.ldap.availableOU )

	def _escapeUrlList( self, urllist ):
		for i in range(len(urllist)):
			urllist[i] = self._escapeUrl(urllist[i])

	def _escapeUrl( self, url ):
		return urllib.quote(url,':%/?=&')

	def _debug(self, level, msg):
		info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
		printInfo = []
		if len(info[0])>25:
			printInfo.append('...'+info[0][-25:])
		else:
			printInfo.append(info[0])
		printInfo.extend(info[1:3])
		ud.debug(univention.debug.ADMIN, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))


	def _getGroupsFromLDAP( self ):
		self._debug( ud.INFO, 'basedn_groups=%s' % self.ldap.searchbaseExtGroups )
		result = []
		try:
			groups = self.ldap.lo.search( filter = 'objectClass=univentionGroup', base = self.ldap.searchbaseExtGroups,
											scope = 'sub', attr = [ 'cn' ] )
		except Exception, e:
			self._debug( ud.ERROR, 'getting rooms failed: %s' % str(e) )
			import traceback, sys
			lines = traceback.format_exc().replace('%','#')
			self._debug( ud.ERROR, 'TRACEBACK\n%s' % lines )
			groups = []

		for grpdn, grpattrs in groups:
			if grpattrs.get('cn'):
				result.append( grpattrs['cn'][0] )
		result.sort()
		return result

	def _searchFilterItems( self, opt_profile, opt_kind, opt_color, opt_searchfilter ):
		if not opt_kind in [ 'domain', 'url' ]:
			return []
		if not opt_color in [ 'blacklisted', 'whitelisted' ]:
			return []
		if opt_profile == 'default':
			profilekeybase = 'proxy/filter'
		else:
			profilekeybase = 'proxy/filter/setting/%s' % opt_profile


		searchresult = []

		if opt_profile and opt_kind and opt_color and opt_searchfilter:
			umc.registry.load()
			namelst = umc.registry.keys()
			namelst = [item for item in namelst if item.startswith('%s/%s/%s/' % (profilekeybase, opt_kind, opt_color))]
			self._debug( ud.INFO, 'namelst=%s' % '\n'.join(namelst) )

			for name in namelst:
				# cut off prefix
				nameid = name[ len('%s/%s/%s/' % (profilekeybase, opt_kind, opt_color)) : ]
				searchresult.append( ( nameid, umc.registry[ name ] ) )  # append tuple ( ID, URL )

			searchresult.sort(lambda x, y: cmp(x[1], y[1]))  # sort by url/domain

			self._debug( ud.INFO, 'searchresult=%s' % searchresult )

			if searchresult:
				searchresult = [item for item in searchresult if fnmatch.fnmatch(item[1], opt_searchfilter)]
				self._debug( ud.INFO, 'searchresult_filtered=%s' % searchresult )
		return searchresult


	def _getFilterredListOfProfiles( self, opt_searchfilter = '*' , containsDefault = True ):

		searchresult = []

		if opt_searchfilter:
			umc.registry.load()
			namelst = umc.registry.keys()
			regex = re.compile('^proxy/filter/setting/([^/]+)/.*$')
			profilelist = []
			for item in namelst:
				match = regex.match(item)
				if match:
					name = match.group(1)
					#if name not in self.__ReservedProfileNames and not name in profilelist:
					if not name in profilelist:
						profilelist.append(name)
			profilelist.sort()
			self._debug( ud.INFO, 'profilelist=%s' % '\n'.join(profilelist) )

			if profilelist:
				profilelist = [item for item in profilelist if fnmatch.fnmatch(item, opt_searchfilter)]
				self._debug( ud.INFO, 'profilelist_filtered=%s' % profilelist )

			profileid = 0
			if containsDefault:
				searchresult.append( ( profileid, 'default', DEFAULT_SETTINGS_FILTERTYPE, [] ) )
			groupdefaultlist = [item for item in namelst if item.startswith('proxy/filter/groupdefault/' )]
			for profile in profilelist:	# append searchresults
				profileid = profileid+1
				groups = []
				profiletype = umc.registry.get( 'proxy/filter/setting/%s/filtertype' % profile, DEFAULT_SETTINGS_FILTERTYPE )
				for groupdefault in groupdefaultlist:	# with associated groups
					if profile == umc.registry[ groupdefault ]:
						group = groupdefault[ len('proxy/filter/groupdefault/' ) : ]
						groups.append(group)
				searchresult.append( ( profileid, profile, profiletype, groups ) )

		return searchresult



	def proxysettings_show_profileassignment( self, object ):
		self._debug( ud.INFO, 'proxysettings_show_profileassignment: options=%s' % str(object.options) )

		# get current ou - default is first OU
		opt_ou = object.options.get('ou', self.ldap.availableOU[0] )
		# switch to current ou
		self.ldap.switch_ou( opt_ou )
		# get groups
		available_groups = self._getGroupsFromLDAP()
		# get current group - default ist first group
		opt_group = object.options.get('grp', available_groups[0] )
		if not opt_group in available_groups:
			opt_group = available_groups[0]
		# get profiles
		available_profiles = self._getFilterredListOfProfiles( '*', containsDefault = False )

		# get current profile
		umc.registry.load()
		current_profile = umc.registry.get( 'proxy/filter/groupdefault/%s' % opt_group )
		if not current_profile:
			current_profile = '::DEFAULT::'

		self.finished( object.id(), ( self.ldap.availableOU, available_groups, available_profiles, current_profile ) )


	def proxysettings_set_profileassignment( self, object ):
		self._debug( ud.INFO, 'proxysettings_set_profiles: options=%s' % str(object.options) )
		opt_group = object.options.get('grp')
		opt_profile = object.options.get('profile')

		if type(opt_profile) == type( [] ):
			opt_profile = opt_profile[0]

		if opt_group and opt_profile:
			if opt_profile == '::DEFAULT::':
				key = 'proxy/filter/groupdefault/%s' % opt_group
				self._debug( ud.INFO, 'UNSET %s' % key )
				univention.config_registry.handler_unset( [ key.encode() ] )
			else:
				keyval = 'proxy/filter/groupdefault/%s=%s' % (opt_group, opt_profile)
				self._debug( ud.INFO, 'SET %s' % keyval )
				univention.config_registry.handler_set( [ keyval.encode() ] )
		else:
			self._debug( ud.ERROR, 'values invalid' )

		self.finished( object.id(), ( ) )


	def proxysettings_show_profiles( self, object ):
		self._debug( ud.INFO, 'proxysettings_show_profiles: options=%s' % str(object.options) )
		searchresult = []

		opt_searchfilter = object.options.get('filter' , '' )

		self._debug( ud.INFO, 'opt_searchfilter=%s' % opt_searchfilter )

		searchresult = self._getFilterredListOfProfiles( opt_searchfilter )

		self.finished( object.id(), ( searchresult ) )


	def proxysettings_create_sitefilter( self, object ):
		self._debug( ud.INFO, 'proxysettings_create_sitefilter: options=%s' % str(object.options) )
		opt_profile = object.options.get('profile', '' )
		opt_filtertype = object.options.get('filtertype', DEFAULT_SETTINGS_FILTERTYPE)

		umc.registry.load()
		key = 'proxy/filter/setting/%s/filtertype=%s' % (opt_profile, opt_filtertype)
		univention.config_registry.handler_set( [ key.encode() ] )
		self._debug( ud.INFO, 'created %s' % key )

		self.proxysettings_show_sitefilters( object, success = True )

	def proxysettings_show_sitefilters( self, object, success = True ):
		searchresult = []
		opt_profile = object.options.get('profile', '' )	# empty: create new and get name on new tab
		opt_kind = object.options.get('kind', 'domain' )
		opt_color = object.options.get('color', 'blacklisted' )
		opt_searchfilter = object.options.get('filter', '' )

		self._debug( ud.INFO, 'opt_profile=%s' % opt_profile )
		self._debug( ud.INFO, 'opt_color=%s' % opt_color )
		self._debug( ud.INFO, 'opt_kind=%s' % opt_kind )
		self._debug( ud.INFO, 'opt_searchfilter=%s' % opt_searchfilter )

		#if opt_profile in self.__ReservedProfileNames:
		#	self.finished( object.id(), ( searchresult, False ) )
		#	return

		searchresult = { 'blacklisted': [], 'whitelisted': [] }
		for color in [ 'whitelisted', 'blacklisted' ]:
			for kind in [ 'domain', 'url' ]:
				sr = self._searchFilterItems( opt_profile, kind, color, '*' )
				for item in sr:
					searchresult[ color ].append( (item[0], item[1], kind) )
			searchresult[ color ].sort(lambda x, y: cmp(x[1], y[1]))  # sort by url/domain

		self.finished( object.id(), ( searchresult, success ) )


	def proxysettings_set_filteritems( self, object ):
		self._debug( ud.INFO, 'proxysettings_set_filteritems: options=%s' % str(object.options) )
# proxysettings_set_filteritems: options={
# 	'profile': 'myprofile',
# 	'blacklistitems': [  {'kind': u'domain', 'urldomain': u'www.porno.de'},
# 						 {'kind': u'url', 'urldomain': u'www.bambusnase.de'} ],
# 	'filtertypetext': u'whitelist then blacklist then allow',
# 	'whitelistitems': [  {'kind': u'domain', 'urldomain': u'www.alleswirdgut.de'},
# 						 {'kind': u'url', 'urldomain': u'http://www.allessupi.de/toll.html'} ]
# 	}
		opt_profile = object.options.get( 'profile' )
		ucr_setting_part = '/setting/%s' % opt_profile
		if opt_profile == 'default':
			ucr_setting_part = ''

		umc.registry.load()

		items_add = []         # [  [ UCRPREFIX, value ], ... ]
		items_remove = []      # [ UCRKEYS, ... ]
		for color in ['whitelist', 'blacklist']:
			for kind in [ 'domain', 'url' ]:
				# get new items
				newitems = []
				for item in object.options.get('%sitems' % color, []):
					item_kind = item.get('kind')
					item_val = item.get('urldomain')
					if item_kind == kind and item_val:
						newitems.append( item_val )

				# get old items
				olditems = {}
				oldkeys = umc.registry.keys()
				for key in oldkeys:
					if key.startswith('proxy/filter%s/%s/%sed/' % (ucr_setting_part, kind, color)):
						olditems[ umc.registry[ key ] ] = key

				# is in newitems but not in olditems
				for item in newitems:
					if not item in olditems.keys():
						items_add.append( [ 'proxy/filter%s/%s/%sed' % (ucr_setting_part, kind, color), item ] )

				# is in olditems but not in newitems
				for item in olditems.keys():
					if not item in newitems:
						items_remove.append( olditems[item] )

		# remove items
		items_remove = [ item.encode() for item in items_remove ]
		univention.config_registry.handler_unset( items_remove )
		self._debug( ud.INFO, 'REMOVING UCR: %s' % items_remove )

		# add new items
		umc.registry.load()
		items_add_ucrlist = []
		next_i = 1
		for item in items_add:
			free_i = next_i
			while '%s/%d' % (item[0], free_i) in umc.registry.keys():
				free_i += 1
			keyval = '%s/%d=%s' % (item[0], free_i, item[1])
			items_add_ucrlist.append( keyval.encode() )
			next_i = free_i + 1
		self._debug( ud.INFO, 'ADDING UCR: %s' % items_add_ucrlist )
		univention.config_registry.handler_set( items_add_ucrlist )

		self.finished( object.id(), [] )


	def proxysettings_remove_profile( self, object ):
		self._debug( ud.INFO, 'proxysettings_remove_profile=%s' % object.options )

		#itemidlist = object.options.get( 'itemid', [] )
		profilelist = object.options.get( 'profile', [] )
		confirmed = object.options.get( 'confirmed', False )

		ud.debug( ud.ADMIN, ud.INFO, 'confirmed=%s  profilelist=%s' % (confirmed, profilelist))

		if not isinstance( profilelist, list ):
			profilelist = [ profilelist ]

		#for name in self.__ReservedProfileNames + ['default']:
		#	if name in profilelist:
		#		profilelist.remove(name)

		message = []
		groups_using_profile = {}

		if confirmed:
			umc.registry.load()
			namelst = umc.registry.keys()
			for profile in profilelist:
				# get all profile UCR keys
				rmlist = [item for item in namelst if item.startswith('proxy/filter/setting/%s/' % profile )]
				self._debug( ud.INFO, 'rmlist=%s' % '\n'.join(rmlist) )

				# get all groupdefault UCR keys that refer to given profilename
				rmlist_grpdefault = [item for item in namelst if item.startswith('proxy/filter/groupdefault/') and umc.registry[item] == profile ]
				rmlist.extend( rmlist_grpdefault )
				self._debug( ud.INFO, 'rmlist2=%s' % '\n'.join(rmlist) )

				for key in rmlist:
					univention.config_registry.handler_unset( [ key.encode() ] )
					self._debug( ud.INFO, 'removed %s' % key )
		else:
			umc.registry.load()
			namelst = umc.registry.keys()
			groupdefaultlist = [item for item in namelst if item.startswith('proxy/filter/groupdefault/' )]
			for profile in profilelist:
				groups_using_profile[profile] = []
				for groupdefault in groupdefaultlist:
					if profile == umc.registry[ groupdefault ]:
						group = groupdefault[ len('proxy/filter/groupdefault/' ) : ]
						groups_using_profile[profile].append(group)

		profilelist = sorted( profilelist )

		self.finished( object.id(), (len(message)==0, message, groups_using_profile) )
