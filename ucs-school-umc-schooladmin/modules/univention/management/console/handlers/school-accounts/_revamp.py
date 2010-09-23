#!/usr/bin/python2.4
#
# Univention Management Console
#  school accounts module: revamp module command result for the specific user interface
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

import notifier.popen

import univention.management.console as umc
import univention.management.console.dialog as umcd
import univention.management.console.protocol as umcp
import univention.debug as ud

import _types

_ = umc.Translation( 'univention.management.console.handlers.school-accounts' ).translate

class Web( object ):

	def _generate_userlist_header( self, checkbox = False ):
		header = [ _( 'User' ), _( 'Password expiry' ) ]
		if checkbox:
			header.append( checkbox )
		return header

	def _generate_userlist_element( self, usermodule, checkbox = False ):
		user = umcd.Text( '%s %s (%s)' % ( usermodule['firstname'], usermodule['lastname'], usermodule['username'] ) )
		if not usermodule['passwordexpiry']:
			expiry = umcd.HTML( '<i>%s</i>' % _( 'none' ) )
		else:
			expiry = umcd.Text( str( usermodule['passwordexpiry'] ) )
		element = [ umcd.Cell( user, attributes = { 'type' : 'umc_list_element umc_nowrap' } ), umcd.Cell( expiry, attributes = { 'align' : 'center' } ) ]
		if checkbox:
			element.append( checkbox )
		return element

	def _generate_userlist_table( self, accountlist, additional_static_options = {} ):
		tablelst = umcd.List()
		btnCheck = umcd.ToggleCheckboxes()
		tablelst.set_header( self._generate_userlist_header( checkbox = btnCheck ) )
		boxes = []

		for usermodule in accountlist: # got univention.admin.modules here
			myoptions = additional_static_options.copy()
			myoptions[ 'userdns' ] = usermodule.dn
			chk = umcd.Checkbox( static_options = myoptions )
			boxes.append( chk.id() )
			tablelst.add_row( self._generate_userlist_element( usermodule, checkbox = chk ) )

		btnCheck.checkboxes( boxes )
		return (tablelst, boxes)

	def _generate_userlist_select( self, boxes, choices, req_opts = {} ):
		myopts = req_opts.copy()
		myopts['userdns'] = []
		req = umcp.Command( opts = myopts )
		req.set_flag( 'web:startup', True )
# 		req.set_flag( 'web:startup_reload', True )
		req.set_flag( 'web:startup_format', _( 'reset passwords' ) )
		actions = ( umcd.Action( req, boxes, True ) )
		select = umcd.SelectionButton( _( 'Select the Operation' ), choices, actions )
		return [ umcd.Fill( 2 ), select ]

	def _web_schoolaccounts_class_show ( self, object, res ):
		availableOU, grouplist, accountlist, selectedgroup, messages = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )

		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolaccounts_class_show: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolaccounts_class_show: dialog: %s' % str( res.dialog ) )

		headline = _( "Administrate pupils" )

		lst = umcd.List()

		if len(availableOU) > 1:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['schoolaccounts/class/show'],
																			opts = { 'ou' : ou } ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select department:'), ouchoices, default = defaultchoice )
			ouselect['width'] = '300'
			lst.add_row( [ ouselect ] )

		groupchoices = []
		defaultchoice = 0
		for group in grouplist:
			if group == selectedgroup:
				defaultchoice = len(groupchoices)
			groupchoices.append( { 'description' : group,
					       'actions': [ umcd.Action( umcp.Command( args = ['schoolaccounts/class/show'],
										       opts = { 'selectedgroup' : group, 'ou': currentOU } ) ) ] } )

		groupselect = umcd.ChoiceButton( _('show class'), groupchoices, default = defaultchoice )
		groupselect['width'] = '300'
		lst.add_row( [ groupselect ] )

		# stop if no group is selected
		if not selectedgroup or selectedgroup == _( 'No group selected' ):
			res.dialog = umcd.Frame( [ lst ], headline )
			self.revamped( object.id(), res )
			return

		# create user table
		tablelst, boxes = self._generate_userlist_table( accountlist,
								 additional_static_options = { 'selectedgroup' : selectedgroup, 'ou': currentOU } )
								 # don't change the selected group

		# create selectbox
		tablelst.add_row( self._generate_userlist_select( boxes,
								  [ ( 'schoolaccounts/user/passwd', _( 'reset password' ) ) ],
								  req_opts = {'selectedgroup' : selectedgroup, 'ou': currentOU }) )
		lst.add_row( [ tablelst ] )

		# add messages if any
		if messages:
			for message in messages:
				lst.add_row( [ message ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )


	def __accounts_search_form( self, opts, filter = '*', key = 'uid' ):
		select = umcd.make( self[ 'schoolaccounts/pupil/search' ][ 'key' ], default = key, attributes = { 'width' : '200' } )
		text = umcd.make( self[ 'schoolaccounts/pupil/search' ][ 'filter' ], default = filter, attributes = { 'width' : '250' } )
		form = umcd.SearchForm( 'schoolaccounts/pupil/search', [ [ ( select, 'uid' ), ( text, '*' ) ] ], opts )
		return form


	def _web_schoolaccounts_pupil_search ( self, object, res ):
		availableOU, accountlist, messages = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )
		searchkey = object.options.get( 'key', 'uid' )
		searchfilter = object.options.get( 'filter', '*' )

		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolaccounts_pupil_search: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolaccounts_pupil_search: dialog: %s' % str( res.dialog ) )

		headline = _( "Search pupils" )

		lst = umcd.List()

		if len(availableOU) > 1:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['schoolaccounts/pupil/search'],
																			opts = { 'ou' : ou,
																					 'key': searchkey,
																					 'filter': searchfilter }, incomplete = True ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select department:'), ouchoices, default = defaultchoice )
			ouselect['width'] = '300'
			lst.add_row( [ ouselect ] )


		lst.add_row( [ self.__accounts_search_form( { 'ou' : currentOU }, searchfilter, searchkey ) ] )

		# stop if no group is selected
		if object.incomplete:
			res.dialog = umcd.Frame( [ lst ], headline )
			self.revamped( object.id(), res )
			return

		# create user table
		tablelst, boxes = self._generate_userlist_table( accountlist,
								 additional_static_options = { 'key' : searchkey, 'filter': searchfilter, 'ou': currentOU } )
								 # don't change the selected group

		# create selectbox
		tablelst.add_row( self._generate_userlist_select( boxes,
								  [ ( 'schoolaccounts/user/passwd', _( 'reset password' ) ) ],
								  req_opts = {'ou': currentOU }) )
		lst.add_row( [ tablelst ] )

		# add messages if any
		if messages:
			for message in messages:
				lst.add_row( [ message ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )

	def _web_schoolaccounts_teacher_show ( self, object, res ):
		availableOU, accountlist, messages = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolaccounts_class_show: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolaccounts_class_show: dialog: %s' % str( res.dialog ) )

		headline = _( "Administrate teachers" )

		lst = umcd.List()

		if len(availableOU) > 1:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['schoolaccounts/teacher/show'],
																			opts = { 'ou' : ou } ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select department:'), ouchoices, default = defaultchoice )
			ouselect['width'] = '300'
			lst.add_row( [ ouselect ] )

		# create user table
		tablelst, boxes = self._generate_userlist_table( accountlist )

		# create selectbox
		tablelst.add_row( self._generate_userlist_select( boxes,
							     [ ( 'schoolaccounts/user/passwd', _( 'reset password' ) ) ] ) )

		lst.add_row( [ tablelst ] )

		# add messages if any
		if messages:
			for message in messages:
				lst.add_row( [ message ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )

	def _web_schoolaccounts_user_passwd ( self, object, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolaccounts_pupil_passwd: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolaccounts_pupil_passwd: dialog: %s' % str( res.dialog ) )
		availableOU, userlist, success, messages = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )

		headline = _( "reset passwords for users" )

		lst = umcd.List()

		if len(userlist) > 0:
			tablelst = umcd.List()
			tablelst.set_header( self._generate_userlist_header( checkbox = False) )

			for usermodule in userlist: # got univention.admin.modules here
				tablelst.add_row( self._generate_userlist_element( usermodule, checkbox = False ) )

			lst.add_row( [ tablelst ] )

		if not success:
			password = umcd.make( self['schoolaccounts/user/passwd']['newPassword'] )
			pwdChangeNextLogin = umcd.make( self['schoolaccounts/user/passwd']['pwdChangeNextLogin'], default = '1' )

			req = umcp.Command( args = [ 'schoolaccounts/user/passwd' ],
					    opts = { 'reallyChangePasswords' : True,
								 'userdns' : object.options[ 'userdns' ],
								 'ou': currentOU } )
			setbut = umcd.SetButton( umcd.Action( req, [ password.id(), pwdChangeNextLogin.id() ] ), attributes = {'class': 'submit', 'defaultbutton': '1'} )
			buttonlst = umcd.List()
			buttonlst.add_row( [ pwdChangeNextLogin ] )
			buttonlst.add_row( [ password, setbut ] )
			lst.add_row( [ buttonlst ] )

		if messages:
			for message in messages:
				lst.add_row( [ message ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )

