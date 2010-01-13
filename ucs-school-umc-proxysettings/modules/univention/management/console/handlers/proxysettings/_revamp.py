#!/usr/bin/python2.4
#
# Univention Management Console Module
#  proxy settings module: revamp module command result for the specific user interface
#
# Copyright (C) 2007-2009 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import notifier.popen

import univention.management.console as umc
import univention.management.console.dialog as umcd
import univention.management.console.protocol as umcp

import univention.debug as ud
import _types

_ = umc.Translation( 'univention.management.console.handlers.proxysettings' ).translate

DEFAULT_SETTINGS_FILTERTYPE = 'whitelist-blacklist-pass'

OutString = {
	'profile' : _( 'Profile' ),
	'domain' : _( 'Domain' ),
	'url' : _( 'URL' )
	}

DescriptionProfiletype = {
	'whitelist-block': _( 'whitelist - block others' ),
	'blacklist-pass': _('blacklist - allow others'),
	'whitelist-blacklist-pass': _('whitelist then blacklist then allow'),
	}


import inspect
def debugmsg( component, level, msg ):
	info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
	printInfo=[]
	if len(info[0])>25:
		printInfo.append('...'+info[0][-25:])
	else:
		printInfo.append(info[0])
	printInfo.extend(info[1:3])
	ud.debug(component, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))


class Web( object ):
	def _create_search_form(self, cmdname, opts = {}, headline = _( 'Search' ) ):
		debugmsg( ud.ADMIN, ud.INFO, '_create_search_form: headline=%s opts=%s' % (headline, opts) )
		lst = umcd.List()

		my_filter = opts.get('filter','*')
		text = umcd.make( self[ cmdname ][ 'filter' ], default = my_filter, attributes = { 'width' : '250' } )
		form = umcd.SearchForm( cmdname, [ [ ( text, my_filter ) ] ], opts )
		lst.add_row( [ form ] )

		return umcd.Frame( [ lst ], headline )


	def _web_proxysettings_create_sitefilter( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_create_sitefilter: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_create_sitefilter: dialog: %s' % str( res.dialog ) )

		searchresult, success = res.dialog

		opt_profile = object.options.get('profile', 'default')
		opt_filtertype = object.options.get('filtertype', DEFAULT_SETTINGS_FILTERTYPE)
		opt_kind = object.options.get('kind', 'domain')
		opt_color = object.options.get('color', 'blacklisted')
		opt_searchfilter = object.options.get('filter', '*')

		if not success:
			lst = umcd.List()
			header = _('Profile name "%s" is reserved, please choose a different one') % opt_profile
			lst.add_row( [] )
			btn = umcd.CloseButton()
			lst.add_row( [ btn ] )
			res.dialog = [ umcd.Frame( [ lst ], header ) ]
			self.revamped( object.id(), res )
		else:
			self._web_proxysettings_show_sitefilters( object, res )


	def _web_proxysettings_show_sitefilters( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_show_sitefilters: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_show_sitefilters: dialog: %s' % str( res.dialog ) )

		searchresult, success = res.dialog

		opt_profile = object.options.get('profile', 'default')
		opt_filtertype = object.options.get('filtertype', DEFAULT_SETTINGS_FILTERTYPE)
		opt_kind = object.options.get('kind', 'domain')
		opt_color = object.options.get('color', 'blacklisted')
		opt_searchfilter = object.options.get('filter', '*')

		framelst = []

		if opt_kind == 'url':
			width = '500'
			name = 'URL'
		else:
			width = '300'
			name = 'domain'

		#
		# display "Profile name" section
		#
		idlist = []
		lst = umcd.List()

		# make profilename editable if not supplied - otherwise readonly
		input_profile = umcd.make_readonly( self[ 'proxysettings/show/sitefilters' ][ 'profile' ], default = opt_profile )
		idlist.append( input_profile.id() )
		input_filtertype = umcd.make_readonly( self[ 'proxysettings/show/sitefilters' ][ 'filtertypetext' ],
											   default = DescriptionProfiletype[ opt_filtertype ],
											   attributes = { 'width' : '300' })
		idlist.append( input_filtertype.id() )

		lst.add_row( [ input_profile, input_filtertype ] )
		framelst.append( umcd.Frame( [ lst ], _('Edit Proxy Filter Profile') ) )

		#
		# display dynamic whitelist
		#
		if opt_filtertype in [ 'whitelist-block', 'whitelist-blacklist-pass' ]:
			lst = umcd.List()
			default = []
			if searchresult['whitelisted']:
				for id, url, kind in searchresult['whitelisted']:
					default.append( { 'id': id, 'urldomain' : url, 'kind' : kind } )
			kind = umcd.Selection( ( 'kind', _types.kind ), default = 'domain' )
			kind[ 'width' ] = '300'
			urldomain = umcd.TextInput( ( 'urldomain', _types.url_domain ) )
			urldomain[ 'width' ] = '300'
			itemlist = umcd.DynamicList( self[ 'proxysettings/set/filteritems' ][ 'whitelistitems' ],
										 [ _( 'Type' ), _( 'URL / Domain' ) ], [ kind, urldomain ],
										 default = default )
			itemlist[ 'colspan' ] = '2'
			idlist.append(itemlist.id())
			lst.add_row( [ itemlist ] )
			framelst.append( umcd.Frame( [ lst ], _('Whitelist') ) )

		#
		# display dynamic blacklist
		#
		if opt_filtertype in [ 'blacklist-pass', 'whitelist-blacklist-pass' ]:
			lst = umcd.List()
			default = []
			if searchresult['blacklisted']:
				for id, url, kind in searchresult['blacklisted']:
					default.append( { 'id': id, 'urldomain' : url, 'kind' : kind } )
			kind = umcd.Selection( ( 'kind', _types.kind ), default = 'domain' )
			kind[ 'width' ] = '300'
			urldomain = umcd.TextInput( ( 'urldomain', _types.url_domain ) )
			urldomain[ 'width' ] = '300'
			itemlist = umcd.DynamicList( self[ 'proxysettings/set/filteritems' ][ 'blacklistitems' ],
										 [ _( 'Type' ), _( 'URL / Domain' ) ], [ kind, urldomain ],
										 default = default )
			itemlist[ 'colspan' ] = '2'
			idlist.append(itemlist.id())
			lst.add_row( [ itemlist ] )
			framelst.append( umcd.Frame( [ lst ], _('Blacklist') ) )

		#
		# add save and close buttons
		#
		lst = umcd.List()
		req = umcp.Command( args = [ 'proxysettings/set/filteritems' ] )
		cancel = umcd.CancelButton()
		setbtn = umcd.SetButton( umcd.Action( req, idlist ), attributes = { 'class': 'submit', 'defaultbutton': '1' } )
		lst.add_row( [ umcd.HTML('<div style="padding-right: 325px">&nbsp;</div>'), cancel, setbtn ] )
		framelst.append( umcd.Frame( [ lst ] ) )

		res.dialog = framelst

		self.revamped( object.id(), res )


	def _web_proxysettings_show_profileassignment( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_show_profileassignment: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_show_profileassignment: dialog: %s' % str( res.dialog ) )

		( availableOU, available_groups, available_profiles, current_profile ) = res.dialog

		currentOU = object.options.get('ou', availableOU[0] )
		group = object.options.get('grp', available_groups[0] )
		if not group in available_groups:
			group = available_groups[0]

		idlist = []
		lst = umcd.List()

		# FIXME TODO HACK HARDCODED for SFB:
		# if 438 is in availableOU then disable selection of OU
		if len(availableOU) > 1 and not '438' in availableOU:
			defaultchoice = 0
			ouchoices = []
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['proxysettings/show/profileassignment'],
																			opts = { 'ou' : ou,
																					 'grp': group
																					 },
																			incomplete = True ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False )
			ouselect['width'] = '300'
			lst.add_row( [ ouselect ] )
			idlist.append( ouselect.id() )

		grpchoices = []
		defaultchoice = 0
		for grp in available_groups:
			if grp == group:
				defaultchoice = len(grpchoices)
			grpchoices.append( { 'description' : grp,
								 'actions': [ umcd.Action( umcp.Command( args = ['proxysettings/show/profileassignment'],
																		 opts = { 'ou' : currentOU,
																				  'grp': grp,
																				  },
																			incomplete = True ) ) ] } )

		grpselect = umcd.ChoiceButton( _('Please select group:'), grpchoices, default = defaultchoice, close_dialog = False )
		grpselect['width'] = '300'
		lst.add_row( [ grpselect ] )
		idlist.append( grpselect.id() )

		choices = []
		choices.append( [ '::DEFAULT::', _('--- default ---') ] )
		for p in available_profiles:
			# Hint: p == (2, 'myprofile', 'whitelist-blacklist-pass', ['308-1B']) 
			choices.append( [ p[1], p[1] ] )
		debugmsg( ud.ADMIN, ud.INFO, 'CHOICES: %s' % str(choices) )
		mysyntax = _types.ProfileSelection( _('Please set new profile here:' ), choices = choices )
		profileselect = umcd.Selection( ('profile', mysyntax), default = current_profile, attributes = { 'width': '300' } )
		lst.add_row( [ profileselect ] )
		idlist.append( profileselect.id() )

		#
		# add save and close buttons
		#
		reqSet = umcp.Command( args = [ 'proxysettings/set/profileassignment' ], opts = { 'profile': [], 'grp': group, 'ou': currentOU } )
		reqShow = umcp.Command( args = [ 'proxysettings/show/profileassignment' ], opts = { 'profile': [], 'grp': group, 'ou': currentOU } )

		actions = ( umcd.Action( reqSet, idlist ), umcd.Action( reqShow, idlist ) )
		lst.add_row( [ umcd.SetButton( actions = actions, attributes = { 'class': 'submit', 'defaultbutton': '1' } ) ] )

		res.dialog = umcd.Frame( [ lst ], _('Assign Proxy Filter Profile To Group') )

		self.revamped( object.id(), res )



	def _web_proxysettings_show_profiles( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_show_profiles: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_show_profiles: dialog: %s' % str( res.dialog ) )

		( searchresult ) = res.dialog

		opt_searchfilter = object.options.get('filter', '*')

		framelst = []

		#
		# display "ADD" section
		#

		if self.permitted('proxysettings/set/filteritems', {} ):
			headline = _( 'Create New Proxy Filter Profile')

			inputitems = []
			lst = umcd.List()

			input_profile = umcd.make( self[ 'proxysettings/create/sitefilter' ]['profile'], attributes = { 'width' : '250' }  )
			inputitems.append( input_profile.id() )
			input_filtertype = umcd.make( self[ 'proxysettings/create/sitefilter' ]['filtertype'], attributes = { 'width' : '250' }  )
			inputitems.append( input_filtertype.id() )

			req = umcp.Command( args = [ 'proxysettings/create/sitefilter' ] )
			req.set_flag( 'web:startup', True )
			req.set_flag( 'web:startup_reload', True )
			req.set_flag( 'web:startup_dialog', True )
			req.set_flag( 'web:startup_format', _('Profile [%(profile)s]') )

			item_addbtn = umcd.Button( _('Add'), 'actions/ok', umcd.Action( req, inputitems ), attributes = { 'helptext': str(_('Profile name:')), 'width': '250' } )
			lst.add_row( [ input_profile, input_filtertype, item_addbtn ] )
			framelst.append( umcd.Frame( [ lst ], headline ) )

		#
		# display "SEARCH" section
		#

		framelst.append( self._create_search_form( 'proxysettings/show/profiles', opts = {'filter': opt_searchfilter}, headline = _('Search For Existing Profiles') ) )

		#
		# display search results
		#

		tablelst = umcd.List()
		headline = '%s ( %s=%s )' % ( _('Searchresults'), _('searchkey'), opt_searchfilter)
		if searchresult:
			item_id_list = []

			icon = 'proxysettings/profile'
			grpicon = 'proxysettings/group'
			nogrpicon = 'proxysettings/nogroup'
			img = umcd.Image( icon )

			tablelst.set_header( [ _( 'Profilename' ), _('Profile Type'), _('Associated Groups') ] )
			for itemid, profile, profiletype, groups in searchresult:

				req = umcp.Command( args = [ 'proxysettings/show/sitefilters' ], opts =  { 'profile': profile, 'filtertype': profiletype } )
				req.set_flag( 'web:startup', True )
				req.set_flag( 'web:startup_reload', True )
				req.set_flag( 'web:startup_dialog', True )
				req.set_flag( 'web:startup_format', _('Profile [%(profile)s]') )
				btn = umcd.Button( profile, icon, umcd.Action( req ) )
				row = [ btn ]

				if profile != 'default':
					#
					# display "profile type"
					#
					row.append( umcd.Text( DescriptionProfiletype[ profiletype ] ) )

					#
					# display "associated user groups"
					#
					if groups:
						row.append( ( umcd.Image( grpicon ), umcd.Text(', '.join(groups)) ) )
					else:
						row.append( umcd.Image( nogrpicon ) )

					#
					# display "Select for removal" checkbox
					#
					if self.permitted('proxysettings/remove/profile', { 'profile': profile } ):
						chkoptions = { 'itemid': itemid, 'profile': profile }
						chk = umcd.Checkbox( static_options = chkoptions )
						item_id_list.append( chk.id() )
						row.append( chk )

				tablelst.add_row( row )

			choices = []
			if self.permitted('proxysettings/remove/profile', {} ):
				req = umcp.Command( opts = {'profile': [], 'itemid': [], 'confirmed' : False} )
				req.set_flag( 'web:startup', True )
				req.set_flag( 'web:startup_reload', True )
				req.set_flag( 'web:startup_dialog', True )
				req.set_flag( 'web:startup_format', _('Remove Proxy Filter Profiles') )
				choices.append( ( 'proxysettings/remove/profile', _( 'remove' ) ) )
				actions = [ umcd.Action( req, item_id_list, True ) ]
			select = umcd.SelectionButton( _( 'Select the Operation' ), choices, actions )
			tablelst.add_row( [ umcd.Fill( 3 ), select ] )
		else:
			tablelst.add_row( [ _( 'No profiles could be found.' ) ] )

		if not object.incomplete:
			framelst.append( umcd.Frame( [ tablelst ], headline ) )

		res.dialog = framelst

		self.revamped( object.id(), res )

	def _web_proxysettings_remove_profile(self, object, res):
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_remove_profile: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_proxysettings_remove_profile: dialog: %s' % str( res.dialog ) )

		success, messages, groups_using_profile = res.dialog
		profilelist = object.options.get( 'profile', [] )
		confirmed = object.options.get('confirmed', False)

		icon = 'proxysettings/profile'
		grpicon = 'proxysettings/group'
		nogrpicon = 'proxysettings/nogroup'

		if not confirmed and not profilelist:
			lst = umcd.List()
			res.dialog = [ umcd.Frame( [ lst ], _('No profile has been selected') ) ]
			self.revamped( object.id(), res )
			return

		tablelst = umcd.List()
		if not confirmed:
			header =  _('Please confirm removal of following profiles:')
			icon = 'proxysettings/profile'
			tablelst.set_header( [ _( 'Profile' ), _('Associated User Groups') ] )
			for profile in profilelist:
				row = [ ( umcd.Image( icon ), umcd.Text( profile ) ) ]
				if groups_using_profile[profile]:
					row.append( (umcd.Image( grpicon ), umcd.Text( ', '.join(groups_using_profile[profile] ) ) ) )
				else:
					row.append( umcd.Image( nogrpicon ) )
				tablelst.add_row( row )

			opts = { 'profile': profilelist, 'confirmed': True }
			req = umcp.Command( args = [ 'proxysettings/remove/profile' ], opts = opts )
			actions = ( umcd.Action( req ) )
			item_btn_ok = umcd.Button( _('Remove'), 'actions/ok', actions = actions, close_dialog = False )
			item_btn_cancel = umcd.CancelButton()
			tablelst.add_row( [ item_btn_cancel, item_btn_ok ] )
		else:
			if success:
				header = _('Deleted profile successfully.')
			else:
				header = _('Error while deleting following profiles:')
				tablelst.add_row( [] )
				tablelst.add_row( [ _('Please ask local administrator for further details.') ] )
			for msg in messages:
				tablelst.add_row( [ msg ] )

			btn = umcd.ErrorButton()
			tablelst.add_row( [ btn ] )

		res.dialog = [ umcd.Frame( [ tablelst ], header ) ]

		self.revamped( object.id(), res )
