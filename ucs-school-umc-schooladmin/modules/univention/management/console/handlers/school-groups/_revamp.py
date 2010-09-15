#!/usr/bin/python2.4
#
# Univention Management Console
#  school groups module: revamp module command result for the specific user interface
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
import univention.management.console.dialog as umcd
import univention.management.console.protocol as umcp
import univention.debug as ud


_ = umc.Translation( 'univention.management.console.handlers.school-groups' ).translate

class Web( object ):
	def __groups_search_form( self, opts, filter = '*', key = 'name', umccommand = 'schoolgroups/groups/list' ):
		select = umcd.make( self[ umccommand ][ 'key' ], default = key, attributes = { 'width' : '200' } )
		text = umcd.make( self[ umccommand ][ 'filter' ], default = filter, attributes = { 'width' : '250' } )
		form = umcd.SearchForm( umccommand, [ [ ( select, 'name' ), ( text, '*' ) ] ], opts )
		return form

	def _web_schoolgroups_groups_list( self, object, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_list: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_list: dialog: %s' % str( res.dialog ) )

		availableOU, departmentNumber, filter, key, groups = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_list: availableOU: %s' % availableOU )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_list: currentOU: %s' % currentOU )

		lstheader = umcd.List()

		# FIXME TODO HACK HARDCODED for SFB:
		# if 438 is in availableOU then disable selection of OU
		if len(availableOU) > 1 and not '438' in availableOU:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['schoolgroups/groups/list'],
																			opts = { 'ou' : ou,
																					 'hidesearchresult': True,
																					 'filter': filter,
																					 'key': key } ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False )
			ouselect['width'] = '300'
			lstheader.add_row( [ ouselect ] )

		req = umcp.Command( args = [ 'schoolgroups/group/add' ],
							opts =  { 'groupdn': None, 'group': None, 'newgrp': True, 'ou': currentOU } )
		req.set_flag( 'web:startup', True )
		req.set_flag( 'web:startup_reload', True )
		req.set_flag( 'web:startup_dialog', True )
		req.set_flag( 'web:startup_format', _('Create new group') )
		item_createbtn = umcd.Button( _('Create new group'), 'school-groups/group', umcd.Action( req ), attributes = { 'width' : '250' } )
		if self.permitted('schoolgroups/group/add', {} ):
			lstheader.add_row( [ item_createbtn ] )

		if object.incomplete or object.options.get( 'hidesearchresult', False ):
			opts = { 'ou': currentOU }
			res.dialog = [ lstheader, umcd.Frame( [ self.__groups_search_form( opts ) ], _('Search') ) ]
			self.revamped( object.id(), res )
			return

		lst = umcd.List()
		item_id_list = []
		if groups:
			lst.set_header( [ _( 'Group' ), _( 'Description' ) ] )
			for group in groups:
				req = umcp.Command( args = [ 'schoolgroups/group/edit' ],
									opts =  { 'group' : group['name'],
											  'groupdn' :group['dn'],
											  'ou': currentOU,
											  } )
				req.set_flag( 'web:startup', True )
				req.set_flag( 'web:startup_reload', True )
				req.set_flag( 'web:startup_dialog', True )
				req.set_flag( 'web:startup_format', _('Edit group "%(group)s"') )

				row = [ umcd.Button( group['name'], 'school-groups/group', umcd.Action( req ) ), group['description'] ]

				if self.permitted('schoolgroups/groups/remove', {} ):
					static_options = { 'group': group['name'], 'groupdn' : group['dn'], 'ou': currentOU }
					chk_button = umcd.Checkbox( static_options = static_options )
					item_id_list.append( chk_button.id() )
					row.append(	chk_button )

				lst.add_row( row )

			if self.permitted('schoolgroups/groups/remove', {} ):
				req = umcp.Command( args = [ 'schoolgroups/groups/remove' ],
									opts= { 'group' : [], 'groupdn' : [], 'confirmed' : False, 'ou': currentOU } )
				req.set_flag( 'web:startup', True )
				req.set_flag( 'web:startup_reload', True )
				req.set_flag( 'web:startup_dialog', True )
				req.set_flag( 'web:startup_format', _('Remove Groups') )
				actions = ( umcd.Action( req, item_id_list ) )
				choices = [ ( 'schoolgroups/groups/remove', _( 'Remove Groups' ) ) ]
				select = umcd.SelectionButton( _( 'Select the Operation' ), choices, actions )
				lst.add_row( [ umcd.Fill( 2 ), select ] )
		else:
			lst.add_row( [ _( 'No groups could be found.' ) ] )



		opts = { 'ou': currentOU }
		res.dialog = [ umcd.Frame( [ self.__groups_search_form( opts, filter, key ) ], _('Search') ),
					   umcd.Frame( [ lst ], _( 'Search Result' ) ) ]
		if self.permitted('schoolgroups/group/add', {} ):
			res.dialog.insert(0, lstheader)

		self.revamped( object.id(), res )


	def _web_schoolgroups_group_edit( self, object, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_edit: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_edit: dialog: %s' % str( res.dialog ) )

		availableOU, basedn, description, userlist, classlist, classmemberfilter, groupdefault = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )

		group = object.options.get('group', None)
		if group == None:
			group = groupdefault
		groupdn = object.options.get('groupdn', None)
		if description == None:
			description = object.options.get('description', None)
		if userlist == None:
			userlist = object.options.get('userlist', [])
		classdn = object.options.get('classdn', None)
		newgrp = object.options.get( 'newgrp', False )

		item_id_list = []
		search_disabled = True

		if not classdn:
			classdn = '::allsearch'

		if classdn == '::allsearch':
			search_disabled = False

		if classmemberfilter == '' and not classdn in ['::all','::allsearch']:
			classmemberfilter = '(&(uid=not)(uid=possible))'



		lst = umcd.List()

		# make groupname editable while creating a new group - otherwise readonly
		if newgrp or not groupdn:
			item_group = umcd.make( self[ 'schoolgroups/group/edit' ][ 'group' ], default = group )
		else:
			item_group = umcd.make_readonly( self[ 'schoolgroups/group/edit' ][ 'group' ], default = group )
		item_description = umcd.make( self[ 'schoolgroups/group/edit' ][ 'description' ], default = description )
		item_id_list.extend( [ item_group.id(), item_description.id() ] )


		# build user selection widget
		item_userlist = umcd.make( self[ 'schoolgroups/group/edit' ][ 'userlist' ], modulename = 'users/user',
								   filter=classmemberfilter,
								   attr_display=[ 'username', ' (', 'firstname', ' ', 'lastname', ')' ],
								   default = userlist, search_disabled = search_disabled, basedn = basedn,
								   search_properties = ['username','firstname','lastname','mailPrimaryAddress']
								   )
		item_userlist['colspan'] = '2'
		item_id_list.append( item_userlist.id() )


		# user can select group by choice button
		default = 0
		choices = []

		req = umcp.Command( args = [ 'schoolgroups/group/edit' ],
							opts = { 'classdn' : '::all',
									 'groupdn' : groupdn,
									 'newgrp' : newgrp,
									 'ou': currentOU,
									 } )
		choices.append( { 'description': _( 'all groups' ), 'actions' : [ umcd.Action( req, item_id_list ) ] } )
		req = umcp.Command( args = [ 'schoolgroups/group/edit' ],
							opts = { 'classdn' : '::allsearch',
									 'groupdn' : groupdn,
									 'newgrp' : newgrp,
									 'ou': currentOU,
									 } )
		choices.append( { 'description': _( 'all groups with search option' ), 'actions' : [ umcd.Action( req, item_id_list ) ] } )
		if classdn == '::all':
			default = 0
		if classdn == '::allsearch':
			default = 1
			search_disabled = False
		for classobj in classlist:
			req = umcp.Command( args = [ 'schoolgroups/group/edit' ],
								opts = { 'classdn' : classobj['dn'],
										 'groupdn' : groupdn,
										 'newgrp' : newgrp,
										 'ou': currentOU,
										 } )
			choices.append( { 'description': classobj['name'], 'actions': [ umcd.Action( req, item_id_list ) ] } )

			if classdn == classobj['dn']:
				default = len(choices)-1

		item_choicebutton = umcd.ChoiceButton( _( 'Please select class:' ), choices = choices, default = default, close_dialog = False )
		item_choicebutton['width'] = '300'


		# build set/cancel button
		opts = { 'groupdn' : groupdn }

		req = umcp.Command( args = [ 'schoolgroups/group/set' ], opts = opts )
		actions = ( umcd.Action( req, item_id_list ) )
		if newgrp or not groupdn:
			item_btn_set = umcd.Button( _('Create Group'), 'actions/ok', actions = actions, attributes = {'class': 'submit', 'defaultbutton': '1'} )
		else:
			item_btn_set = umcd.Button( _('Save Changes'), 'actions/ok', actions = actions, attributes = {'class': 'submit', 'defaultbutton': '1'} )
		item_btn_cancel = umcd.CancelButton()


		# FIXME TODO HACK HARDCODED for SFB:
		# if 438 is in availableOU then disable selection of OU
		ouselect = None
		if len(availableOU) > 1 and '438' in availableOU:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['schoolgroups/group/edit'],
																			opts = { 'ou' : ou,
																					 'groupdn': groupdn,
																					 'description': description,
																					 'classdn': classdn,
																					 'newgrp': newgrp
																					 } ), item_id_list ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False )
			ouselect['width'] = '300'


		# build layout
		lst.add_row( [ item_group, item_description ] )
		if not ouselect == None:
			lst.add_row( [ ouselect ] )
		lst.add_row( [ item_choicebutton ] )
		lst.add_row( [ item_userlist ] )
		lst.add_row( [ item_btn_cancel, item_btn_set ] )


		if newgrp:
			if len(availableOU) > 1:
				header = _( 'Create Group' )
			else:
				header = _( 'Create Group (Department %s)') % currentOU
		else:
			header = _( 'Edit Group "%s"' ) % group

		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( object.id(), res )


	def _web_schoolgroups_groups_teacher_list( self, object, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_teacher_list: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_teacher_list: dialog: %s' % str( res.dialog ) )

		availableOU, departmentNumber, filter, key, groups = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_teacher_list: availableOU: %s' % availableOU )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_teacher_list: currentOU: %s' % currentOU )

		lstheader = umcd.List()

		# FIXME TODO HACK HARDCODED for SFB:
		# if 438 is in availableOU then disable selection of OU
		if len(availableOU) > 1 and not '438' in availableOU:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['schoolgroups/groups/teacher/list'],
																			opts = { 'ou' : ou,
																					 'hidesearchresult': True,
																					 'filter': filter,
																					 'key': key } ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False )
			ouselect['width'] = '300'
			lstheader.add_row( [ ouselect ] )

		if object.incomplete or object.options.get( 'hidesearchresult', False ):
			opts = { 'ou': currentOU }
			res.dialog = [ lstheader, umcd.Frame( [ self.__groups_search_form( opts, umccommand = 'schoolgroups/groups/teacher/list' ) ], _('Search') ) ]
			self.revamped( object.id(), res )
			return

		lst = umcd.List()
		if groups:
			headerlst = [ _( 'Group' ), _( 'Description' ) ]
			lst.set_header( headerlst )
			for group in groups:
				req = umcp.Command( args = [ 'schoolgroups/group/teacher/edit' ],
									opts =  { 'group' : group['name'],
											  'groupdn' :group['dn'],
											  'ou': currentOU,
											  } )
				req.set_flag( 'web:startup', True )
				req.set_flag( 'web:startup_reload', True )
				req.set_flag( 'web:startup_dialog', True )
				req.set_flag( 'web:startup_format', _('Assign teachers to group "%(group)s"') )

				row = [ umcd.Button( group['name'], 'school-groups/group', umcd.Action( req ) ), group['description'] ]

				lst.add_row( row )
		else:
			lst.add_row( [ _( 'No groups could be found.' ) ] )


		opts = { 'ou': currentOU }
		res.dialog = [ umcd.Frame( [ self.__groups_search_form( opts, filter, key, umccommand='schoolgroups/groups/teacher/list' ) ], _('Search') ),
					   umcd.Frame( [ lst ], _( 'Search Result' ) ) ]
		if lstheader:
			res.dialog.insert(0, lstheader)

		self.revamped( object.id(), res )



	def _web_schoolgroups_group_teacher_edit( self, object, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_teacher_edit: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_teacher_edit: dialog: %s' % str( res.dialog ) )

		availableOU, basedn, description, userlist = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )

		group = object.options.get('group', None)
		groupdn = object.options.get('groupdn', None)
		if description == None:
			description = object.options.get('description', None)
		if userlist == None:
			userlist = object.options.get('userlist', [])

		item_id_list = []

		lst = umcd.List()

		item_group = umcd.make_readonly( self[ 'schoolgroups/group/teacher/edit' ][ 'group' ], default = group )
		item_description = umcd.make_readonly( self[ 'schoolgroups/group/teacher/edit' ][ 'description' ], default = description )
		item_id_list.extend( [ item_group.id(), item_description.id() ] )


		# build user selection widget
		item_userlist = umcd.make( self[ 'schoolgroups/group/teacher/edit' ][ 'userlist' ], modulename = 'users/user',
								   filter='',
								   attr_display=[ 'username', ' (', 'firstname', ' ', 'lastname', ')' ],
								   default = userlist, search_disabled = True, basedn = basedn,
								   search_properties = ['username','firstname','lastname','mailPrimaryAddress']
								   )
		item_userlist['colspan'] = '2'
		item_id_list.append( item_userlist.id() )



		# build set/cancel button
		opts = { 'groupdn' : groupdn }

		req = umcp.Command( args = [ 'schoolgroups/group/teacher/set' ], opts = opts )
		actions = ( umcd.Action( req, item_id_list ) )
		item_btn_set = umcd.Button( _('Save Changes'), 'actions/ok', actions = actions, attributes = {'class': 'submit', 'defaultbutton': '1'} )
		item_btn_cancel = umcd.CancelButton()


		# FIXME TODO HACK HARDCODED for SFB:
		# if 438 is in availableOU then disable selection of OU
		ouselect = None
		if len(availableOU) > 1 and '438' in availableOU:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['schoolgroups/group/edit'],
																			opts = { 'ou' : ou,
																					 'groupdn': groupdn,
																					 'description': description,
																					 } ), item_id_list ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False )
			ouselect['width'] = '300'

		# build layout
		lst.add_row( [ item_group, item_description ] )
		if not ouselect == None:
			lst.add_row( [ ouselect ] )
		lst.add_row( [ item_userlist ] )
		lst.add_row( [ item_btn_cancel, item_btn_set ] )


		header = _( 'Assign teachers to group "%s"' ) % group

		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( object.id(), res )


	def _web_schoolgroups_groups_remove( self, object, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_remove: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_remove: dialog: %s' % str( res.dialog ) )

		availableOU, success, messages = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )

		grouplist = object.options.get('group', None)
		groupdnlist = object.options.get('groupdn', None)
		confirmed = object.options.get('confirmed', False)

		if not confirmed and not groupdnlist:
			lst = umcd.List()
			res.dialog = [ umcd.Frame( [ lst ], _('No group has been selected') ) ]
			self.revamped( object.id(), res )
			return

		lst = umcd.List()
		if not confirmed:
			header =  _('Please confirm removal of following groups:')
			if grouplist == None:
				grouplist = []
			elif not isinstance( grouplist, list ):
				grouplist = [ grouplist ]

			for grp in grouplist:
				lst.add_row( [ grp ] )

			opts = { 'groupdn': groupdnlist, 'confirmed': True, 'ou': currentOU }
			req = umcp.Command( args = [ 'schoolgroups/groups/remove' ], opts = opts )
			actions = ( umcd.Action( req ) )
			item_btn_ok = umcd.Button( _('Remove'), 'actions/ok', actions = actions, close_dialog = False, attributes = {'class': 'submit'} )
			item_btn_cancel = umcd.CancelButton()
			lst.add_row( [ item_btn_cancel, item_btn_ok ] )
		else:
			if success:
				header = _('Groups successfully deleted')
			else:
				header = _('Error while deleting following groups')
				lst.add_row( [] )
				lst.add_row( [ _('Please ask local administrator for further details.') ] )
			for msg in messages:
				lst.add_row( [ msg ] )


		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( object.id(), res )


	def _web_schoolgroups_groups_unused_list( self, umcobj, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_unused_list: options: %s' % str( umcobj.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_unused_list: dialog: %s' % str( res.dialog ) )

		availableOU, empty_groups = res.dialog
		currentOU = umcobj.options.get( 'ou', availableOU[0] )
		try:
			membercnt = int( umcobj.options.get( 'membercnt', 0 ) )
		except:
			membercnt = 0

		item_id_list = []
		lst = umcd.List()
		header =  _('Please select groups for removal:')

		# FIXME TODO HACK HARDCODED for SFB:
		# if 438 is in availableOU then disable selection of OU
		if len(availableOU) > 1 and not '438' in availableOU:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['schoolgroups/groups/unused/list'],
																			opts = { 'ou' : ou,
																					 'membercnt': membercnt,
																					 } ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False )
			ouselect['width'] = '300'
			lst.add_row( [ ouselect ] )
			item_id_list.append( ouselect.id() )

		item_membercnt = umcd.make( self[ 'schoolgroups/groups/unused/list' ][ 'membercnt' ], default = str(membercnt), attributes = { 'width' : '50' } )
		item_id_list.append( item_membercnt.id() )

		opts = { 'ou': currentOU }
		req = umcp.Command( args = [ 'schoolgroups/groups/unused/list' ], opts = opts )
		actions = ( umcd.Action( req, item_id_list ) )
		item_updatebtn = umcd.Button( _('Update list'), 'actions/ok', actions = actions, close_dialog = False, attributes = {'class': 'submit', 'defaultbutton': '1'} )
		lst.add_row( [ _('Number of pupils per group (max 5):'), item_membercnt, item_updatebtn ] )

		lstresult = umcd.List()
		lstresult.set_header( [ _( 'Group' ), _( 'Description' ), _( 'Pupils' ), _( 'Teachers' ) ] )
		for grp in empty_groups:
			uidlist_pupils = []
			for uid, uiddn in grp['listpupils']:
				uidlist_pupils.append(uid)

			uidlist_teachers = []
			for uid, uiddn in grp['listteachers']:
				uidlist_teachers.append(uid)

			row = [ grp['name'], grp['description'], ', '.join(uidlist_pupils), ', '.join(uidlist_teachers) ]

			# ONLY SHOW CHECKBOX IF NUMBER OF PUPILS IN GRP IS 0 AND USER IS PERMITTED TO REMOVE GROUPS
			if self.permitted('schoolgroups/groups/unused/remove', {} ) and len(grp['listpupils']) == 0:
				static_options = { 'group': grp['name'], 'groupdn': grp['dn'], 'ou': currentOU }
				chk_button = umcd.Checkbox( static_options = static_options )
				item_id_list.append( chk_button.id() )
				row.append(	chk_button )

			lstresult.add_row( row )

		if self.permitted('schoolgroups/groups/unused/remove', {} ):
			req = umcp.Command( args = [ 'schoolgroups/groups/unused/remove' ],
								opts= { 'group' : [], 'groupdn' : [], 'confirmed' : False, 'ou': currentOU } )
			req.set_flag( 'web:startup', True )
			req.set_flag( 'web:startup_reload', True )
			req.set_flag( 'web:startup_dialog', True )
			req.set_flag( 'web:startup_format', _('Remove Groups') )
			actions = ( umcd.Action( req, item_id_list ) )
			choices = [ ( 'schoolgroups/groups/remove', _( 'Remove Groups' ) ) ]
			select = umcd.SelectionButton( _( 'Select the Operation' ), choices, actions )
			lstresult.add_row( [ umcd.Fill( 4 ), select ] )

		res.dialog = [ 	umcd.Frame( [ lst ], header ),
						umcd.Frame( [ lstresult ], '' ) ]

		self.revamped( umcobj.id(), res )


	def _web_schoolgroups_groups_unused_remove( self, umcobj, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_unused_remove: options: %s' % str( umcobj.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_schoolgroups_groups_unused_remove: dialog: %s' % str( res.dialog ) )

		availableOU, success, messages = res.dialog
		currentOU = umcobj.options.get( 'ou', availableOU[0] )

		grouplist = umcobj.options.get('group', None)
		groupdnlist = umcobj.options.get('groupdn', None)
		confirmed = umcobj.options.get('confirmed', False)

		if not confirmed and not groupdnlist:
			lst = umcd.List()
			res.dialog = [ umcd.Frame( [ lst ], _('No group has been selected') ) ]
			self.revamped( umcobj.id(), res )
			return

		lst = umcd.List()
		if not confirmed:
			header =  _('Please confirm removal of following groups:')
			if grouplist == None:
				grouplist = []
			elif not isinstance( grouplist, list ):
				grouplist = [ grouplist ]

			for grp in grouplist:
				lst.add_row( [ grp ] )

			opts = { 'groupdn': groupdnlist, 'confirmed': True, 'ou': currentOU }
			req = umcp.Command( args = [ 'schoolgroups/groups/unused/remove' ], opts = opts )
			actions = ( umcd.Action( req ) )
			item_btn_ok = umcd.Button( _('Remove'), 'actions/ok', actions = actions, close_dialog = False, attributes = {'class': 'submit'} )
			item_btn_cancel = umcd.CancelButton()
			lst.add_row( [ item_btn_cancel, item_btn_ok ] )
		else:
			if success:
				header = _('Groups successfully deleted')
			else:
				header = _('Error while deleting following groups')
				lst.add_row( [] )
				lst.add_row( [ _('Please ask local administrator for further details.') ] )
			for msg in messages:
				lst.add_row( [ msg ] )
			btn = umcd.CloseButton()
			lst.add_row( [ btn ] )

		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( umcobj.id(), res )
