#!/usr/bin/python2.4
#
# Univention Management Console
#  reservation module: revamp module command result for the specific user interface
#
# Copyright (C) 2007-2010 Univention GmbH
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

import operator
from datetime import date
import time
import copy
import _types
from _types import syntax

import notifier.popen

import univention.management.console as umc
import univention.management.console.dialog as umcd
import univention.management.console.protocol as umcp

import univention.debug as ud

_ = umc.Translation( 'univention.management.console.handlers.reservation' ).translate

import pwd
import inspect

def debugmsg( component, level, msg ):
	info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
	printInfo=[]
	if len(info[0])>20:
		printInfo.append('...'+info[0][-20:])
	else:
		printInfo.append(info[0])
	printInfo.extend(info[1:3])
	ud.debug(component, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))

def _defined(key, dict):
	return (key in dict and dict[key])

class Web( object ):
	def _create_search_form(self, cmdname, opts = {} ):
		headline = _( 'Search' )
		lst = umcd.List()

		if opts.has_key('filter'):
			my_filter = opts['filter']
		else:
			my_filter = '*'
		text = umcd.make( self[ cmdname ][ 'filter' ], default = my_filter, attributes = { 'width' : '250' } )
		form = umcd.SearchForm( cmdname, [ [ ( text, '*' ) ] ], opts, close_dialog = False )
		lst.add_row( [ form ] )

		return umcd.Frame( [ lst ], headline )

	def _web_reservation_list( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_reservation_list: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_reservation_list: dialog: %s' % str( res.dialog ) )

		( searchresult ) = res.dialog

		opts = _types.defaults.merge(object.options, 'reservation_list')

		headline = _( "School lesson configuration" )
		#lst = umcd.List()
		framelst = []
		idlist_create_button = []

		# create new button
		#lst = umcd.List()
		icon = 'reservation/reservation_add'
		req = umcp.Command( args = [ 'reservation/edit' ] )
		req.set_flag( 'web:startup', True )
		req.set_flag( 'web:startup_reload', True )
		req.set_flag( 'web:startup_dialog', True )
		req.set_flag( 'web:startup_format', _('New reservation') )
		createbtn = umcd.Button( _('New reservation'), icon, umcd.Action( req, idlist_create_button ) )
		#lst.add_row([createbtn])
		#framelst.append( umcd.Frame( [ lst ], headline ) )

		seperator_line = umcd.HTML(text='<hr>')
		lst = umcd.List()
		lst.add_row( [ createbtn ] )
		lst.add_row( [ seperator_line ] )

		# Search
		#headline = _( 'Search' )
		#lst = umcd.List()
		umccommand = 'reservation/list'
		#date_type = umc.String( _( 'Date' ), required = False )
		#searchdate = umcd.DateInput( ( 'date_start', date_type ), default=opts['date_start']  )
		#idlist_create_button.append(searchdate.id())
		key = umcd.make( self[ umccommand ][ 'key' ], default = opts['key'], attributes = { 'width' : '100' } )
		text = umcd.make( self[ umccommand ][ 'searchfilter' ], default = opts['searchfilter'], attributes = { 'width' : '250' } )
		form = umcd.SearchForm( umccommand, [ [ ( key, opts['key'] ), ( text, opts['searchfilter'] ) ] ], opts = {'action': 'search'}, search_button_label = _("Show all") )
		# the searchform
		lst.add_row( [ form ] )
		framelst.append( umcd.Frame( [ lst ], headline ) )

		# List / Search Results
		tablelst = umcd.List()
		#subheadline = '%s (date=%s) ( %s=%s )' % ( _('Searchresults'), opts['date_start'], _(opts['key']), opts['searchfilter'])
		subheadline = '%s:' % _('Searchresults')
		if searchresult:
			# sort reservations by date attribute
			#sorted_reservations = []
			#for reservationID, name, description, editable, date_start, room, ownername in searchresult:
			#	sorted_reservations.append( (  ) )
			#searchresult = sorted( searchresult, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
			#						key = operator.itemgetter( 3 ) )

			#subheadline = '%s ( %s=%s )' % ( _('Searchresults'), _(opts['key']), opts['searchfilter'])
			idlist_remove = []
			tablelst.set_header( [ _( 'Date' ), _( 'Start Time' ), _( 'End Time' ), _( 'Room'), _( 'Class/Group'), _( 'Reservation profile' ), _('Owner'), _( 'Edit' ), _( 'Delete' ) ] )
			for reservationID, reservation_name, description, date_start, time_begin, time_end, roomname, groupname, ownername, profile_name in searchresult:
				row = []
				datelist=date_start.split('-')
				datelist.reverse()
				item_date='.'.join(datelist)
				groupstring = groupname.replace(opts['ou']+'-','')
				if ownername == _types.AdminUser:
					ownerstring = 'Vorgabe'
				else:
					ownerstring = ownername

				school_lesson = _types.time_to_lesson(time_begin)
				if school_lesson['start'] == time_begin:
					time_begin_string = school_lesson['name']+' ('+time_begin+')'
				else:
					time_begin_string = time_begin
				school_lesson = _types.endtime_to_lesson(time_end)
				if school_lesson['end'] == time_end:
					time_end_string = school_lesson['name']+' ('+time_end+')'
				else:
					time_end_string = time_end

				#icon = 'reservation/reservation'
				#iconwidget = umcd.Button( '', icon, () )
				#row.append(iconwidget)
				row.append(item_date)
				row.append(time_begin_string)
				row.append(time_end_string)
				row.append(roomname)
				row.append(groupstring)
				row.append(profile_name)
				row.append(ownerstring)

				if ownername == self._username:
					acltarget = 'own'
				else:
					acltarget = 'other'
				if self.permitted('reservation/edit', { 'target': acltarget } ):
					# edit
					icon = 'reservation/edit'
					select_opts = { 'reservationID': reservationID, 'reservation_name' : reservation_name, 'roomname': roomname, 'date_start': date_start, 'target': acltarget }
					#object.options['roomname'] = roomname
					#object.options['date_start'] = date_start
					req = umcp.Command( args = [ 'reservation/edit' ],
							    opts = select_opts )
					req.set_flag( 'web:startup', True )
					req.set_flag( 'web:startup_reload', True )
					req.set_flag( 'web:startup_dialog', True )
					req.set_flag( 'web:startup_format', _('Edit reservation')+' [%(roomname)s/%(date_start)s]' )
					editbtn = umcd.Button( '', icon, umcd.Action( req ) , helptext =  _('Click to edit this reservation') )
					row.append(editbtn)
				else:
					# edit
					icon = 'reservation/edit_disabled'
					editbtn = umcd.Button( '', icon, actions=() , helptext = _('You are not the owner of this reservation') )
					row.append(editbtn)

				if self.permitted('reservation/remove', { 'target': acltarget } ):
					# delete
					icon = 'reservation/reservation_del'
					select_opts = { 'reservationID': reservationID, 'action': 'delete', 'ou': opts['ou'], 'target': acltarget }
					req = umcp.Command( args = [ 'reservation/remove' ],
							    opts = select_opts )
					req.set_flag( 'web:startup', True )
					req.set_flag( 'web:startup_reload', True )
					req.set_flag( 'web:startup_dialog', True )
					req.set_flag( 'web:startup_format', _('Remove reservation') )
					delbtn = umcd.Button( '', icon, umcd.Action( req ) , helptext = _('Click to remove this reservation') )
					row.append(delbtn)
				else:
					# edit
					icon = 'reservation/edit_disabled'
					editbtn = umcd.Button( '', icon, actions=() , helptext = _('You are not the owner of this reservation') )
					row.append(editbtn)

					# delete
					icon = 'reservation/reservation_del_disabled'
					delbtn = umcd.Button( '', icon, actions=() , helptext = _('You are not the owner of this reservation') )
					row.append(delbtn)

				#else:
				#	row.append(umcd.Fill( 2 ))
				tablelst.add_row( row )
		else:
			if opts.get('action') == 'search':
				tablelst.add_row( [_('No matching reservations found')] )
			else:
				tablelst.add_row( [_('Click search button to list reservations')] )

		framelst.append( umcd.Frame( [ tablelst ], subheadline ) )
		#lst.add_row( [ umcd.Frame( [ tablelst ], subheadline ) ] )

		#res.dialog = umcd.Frame( [ lst ], headline )
		res.dialog = framelst
		self.revamped( object.id(), res )


	def _web_reservation_edit( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_reservation_edit: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_reservation_edit: dialog: %s' % str( res.dialog ) )

		availableOU, roomdict, classgroupdict, prjgroupdict, profileList = res.dialog

		opts = _types.defaults.merge(object.options, 'reservation_edit')
		debugmsg( ud.ADMIN, ud.INFO, '_web_reservation_edit: opts: %s' % str( opts ) )

		if not _defined('reservationID', opts):
			headline = _( "Create reservation" )
		else:
			headline = _( "Edit reservation" )

		lst = umcd.List()
		idlist_ok_button = []

		action = opts.get('action')
		if action:
			del opts['action']
		else:
			action = 'edit'

		if action == 'message':
			msghead =  object.options.get('message', _('Reservation created.'))
			lst.add_row( [ umcd.CloseButton( ) ] )
			res.dialog = umcd.Frame( [ lst ], msghead )
			self.revamped( object.id(), res )
			return
		#ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_edit: start of widgets' )

		# create input widgets

		### Date
		descr_text = umc.String( _( 'Date' ), required = True )
		input_date = umcd.DateInput( ( 'date_start', descr_text ), default=opts['date_start'], attributes = { 'width' : '200' }  )
		idlist_ok_button.append( input_date.id() )
		row = [input_date]

		## TODO: Offer ComboBox Select
		# v0.1: default = opts.get('time_begin') or time.strftime('%H:%M')
		# v0.1: descr_text = umc.String( _( 'Start Time' ), required = True )
		# v0.1: input_time_begin = umcd.TextInput( ( 'time_begin', descr_text ), default=default  )
		# v1.0: input_time_begin = umcd.Selection( ( 'time_begin' , syntax['time_begin'] ), default = opts['time_begin'] )
		# v1.1:
		choices = []
		defaultID = 0
		_types.timetable.update()	# maybe the lessontimes table was updated
		for time_begin, description in _types.syntax['time_begin'].choices():
			choice_opts = copy.copy(opts)
			choice_opts['time_begin'] = time_begin
			choice_opts['action'] = 'edit'
			if time_begin == opts['time_begin']:
				defaultID = len( choices)
			req = umcp.Command( args = [ 'reservation/edit' ],
						opts = choice_opts ,
						incomplete = False )
			choices.append( { 'description' : description, 'actions' : [ umcd.Action( req, idlist_ok_button ) ] } )
		input_time_begin = umcd.ChoiceButton( _('Start time'), choices, default = defaultID, close_dialog = False, attributes = { 'width' : '300' } )
		input_time_begin[ 'width' ] = '200'
		idlist_ok_button.append(input_time_begin.id())
		row.append(input_time_begin)

		# v0.1: descr_text = umc.String( _( 'End Time' ), required = True )
		# v0.1: input_time_end = umcd.TextInput( ( 'time_end', descr_text ), default=default  )
		syntax['time_end'].set_time_begin(opts['time_begin'])
		#self[ 'reservation/edit' ][ 'time_end' ][1].set_time_begin(opts['time_begin'])

		#input_time_end = umcd.Selection( ( 'time_end' , syntax['time_end'] ), default = opts['time_end'] )
		input_time_end = umcd.make( self[ 'reservation/edit' ][ 'time_end' ], default = opts['time_end'], attributes = { 'width' : '200' } )
		## With new umcd.ComboboxButton:
		#choices_time_end = []
		#defaultID_time_end = 0
		#for time_end, description in _types.syntax['time_end'].choices():
		#	choice_opts = copy.copy(opts)
		#	choice_opts['time_end'] = time_end
		#	choice_opts['action'] = 'edit'
		#	if time_end == opts['time_end']:
		#		defaultID_time_end = len( choices)
		#	req = umcp.Command( args = [ 'reservation/edit' ],
		#				opts = choice_opts ,
		#				incomplete = False )
		#	choices_time_end.append( { 'description' : description, 'actions' : [ umcd.Action( req, idlist_ok_button ) ] } )
		#input_time_end = umcd.ComboboxButton( _('End Time'), choices_time_end, default = defaultID_time_end, close_dialog = False, attributes = { 'width' : '120' } )
		idlist_ok_button.append(input_time_end.id())
		row.append(input_time_end)
		lst.add_row( row )

		#ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_edit: time' )
#		if opts['time_begin'] != 'now':
#			## Iteration
#			choices = []
#			defaultID = 0
#			for iterationDays, description in _types.syntax['rhythm'].choices():
#				choice_opts = copy.copy(opts)
#				choice_opts['iterationDays'] = iterationDays
#				choice_opts['action'] = 'edit'
#				if iterationDays == opts['iterationDays']:
#					defaultID = len( choices)
#				req = umcp.Command( args = [ 'reservation/edit' ],
#							opts = choice_opts ,
#							incomplete = True )
#				choices.append( { 'description' : description, 'actions' : [ umcd.Action( req, idlist_ok_button ) ] } )
#
#			input_iterationDays = umcd.ChoiceButton( _('Please select rhythm:'), choices, default = defaultID, close_dialog = False, attributes = { 'width' : '120' } )
#			idlist_ok_button.append(input_iterationDays.id())
#			row = [input_iterationDays]
#
#			if int(opts['iterationDays']) != 0:
#				## Start-Stop
#				descr_text = umc.String( _( 'Until' ), required = True )
#				input_iterationEnd = umcd.DateInput( ( 'iterationEnd', descr_text ), default = opts['iterationEnd']  )
#				idlist_ok_button.append(input_iterationEnd.id())
#				row.append( input_iterationEnd )
#				## Terms
#				#input_terms = umcd.make( self[ 'reservation/edit' ][ 'terms' ], default = '::notset',
#				#			attributes = { 'width' : '200' } )
#				#row.append( input_terms )
#
#			lst.add_row( row )


		#ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_edit: ou' )
		### Build school selection widget
		# FIXME TODO HACK HARDCODED for SFB:
		# if 438 is in availableOU then disable selection of OU
		if len(availableOU) > 1 and not '438' in availableOU:
			choices = []
			defaultID = 0
			for ou in availableOU:
				choice_opts = copy.copy(opts)
				choice_opts['ou']=ou
				choice_opts['action'] = 'edit'
				if ou == opts['ou']:
					defaultID = len(choices)
				debugmsg( ud.ADMIN, ud.INFO, 'choice_opts: OU: %s' % choice_opts['ou'] )
				req = umcp.Command( args = [ 'reservation/edit' ],
							opts = choice_opts ,
							incomplete = True )
				choices.append( { 'description' : ou, 'actions' : [ umcd.Action( req ) ] } )

			input_ou = umcd.ChoiceButton( _('Please select school:'), choices, default = defaultID, close_dialog = False, attributes = { 'width' : '200' } )
			idlist_ok_button.append(input_ou.id())

		### stop here if no OU has been selected
		if not _defined('ou', opts):
			lst.add_row( [ input_ou ] )
			res.dialog = umcd.Frame( [ lst ], headline )
			self.revamped( object.id(), res )
			return

		#ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_edit: room' )
		### Room
		# sort groups by cn attribute
		sorted_rooms = []
		for roomdn, roomdata in roomdict.items():
			sorted_rooms.append( ( roomdata[ 0 ][ 'cn' ][ 0 ], roomdn, roomdata ) )

		sorted_rooms = sorted( sorted_rooms, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
								key = operator.itemgetter( 0 ) )
		syntax['roomname']._choices=[]
		for cn, roomdn, roomdata in sorted_rooms:
			#if cn == opts['roomname']:
			#	curroomdn = roomdn
			#	curroomattrs = roomdata[ 0 ]
			#	curroommembers = roomdata[ 1 ]
			syntax['roomname']._choices.append( ( roomdata[ 0 ][ 'cn' ][ 0 ], cn ) )

		#input_room = umcd.Selection( ( 'roomname' , syntax['roomname'] ), default = opts['roomname'] )
		input_room = umcd.make( self[ 'reservation/edit' ][ 'roomname' ], default = opts['roomname'], attributes = { 'width' : '200' } )
		idlist_ok_button.append(input_room.id())
		#lst.add_row( [ input_room ] )

		### User Group
		# sort groups by cn attribute
		sorted_classes = []
		for grpdn, grpdata in classgroupdict.items():
			sorted_classes.append( ( grpdata[ 0 ][ 'cn' ][ 0 ], grpdn, grpdata ) )

		sorted_classes = sorted( sorted_classes, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
								key = operator.itemgetter( 0 ) )
		sorted_prjgroups = []
		for grpdn, grpdata in prjgroupdict.items():
			sorted_prjgroups.append( ( grpdata[ 0 ][ 'cn' ][ 0 ], grpdn, grpdata ) )

		sorted_prjgroups = sorted( sorted_prjgroups, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
								key = operator.itemgetter( 0 ) )

		#choices=syntax['groupname']._choices
		syntax['groupname']._choices=[]
		schoolprefix = '%s-' % opts['ou']
		for cn, grpdn, grpdata in sorted_classes:
			syntax['groupname']._choices.append( ( grpdata[ 0 ][ 'cn' ][ 0 ], cn.replace(schoolprefix,'') ) )

		for cn, grpdn, grpdata in sorted_prjgroups:
			syntax['groupname']._choices.append( ( grpdata[ 0 ][ 'cn' ][ 0 ], cn.replace(schoolprefix,'') ) )

		#input_group = umcd.Selection( ( 'groupname' , syntax['groupname'] ), default = opts['groupname'] )
		input_group = umcd.make( self[ 'reservation/edit' ][ 'groupname' ], default = opts['groupname'], attributes = { 'width' : '200' } )
		idlist_ok_button.append(input_group.id())

		if len(availableOU) > 1 and not '438' in availableOU:
			lst.add_row( [ input_ou, input_room, input_group ] )
		else:
			lst.add_row( [ input_room, input_group ] )

		### Profile
		syntax['resprofileID']._choices=[]
		for resprofileID, profile_name, description, ownername in profileList:
			#if profile == opts['resprofileID']:
			#	defaultID = len( syntax['resprofileID']._choices )
			if ownername == _types.AdminUser:
				ownerstring = 'Vorgabe'
			else:
				ownerstring = ownername
			syntax['resprofileID']._choices.append( ( resprofileID, profile_name+' ('+ownerstring+')' ) )

		#input_profile = umcd.Selection( ( 'resprofileID' , syntax['resprofileID'] ), default = opts['resprofileID'] )
		input_profile = umcd.make( self[ 'reservation/edit' ][ 'resprofileID' ], default = opts['resprofileID'], attributes = { 'width' : '300' } )
		idlist_ok_button.append(input_profile.id())
		#lst.add_row( [ input_profile ] )

		#\item Auswahl des Druckermodus (ja/moderiert/nein)
		if _defined('printmode', opts):
			input_printmode = umcd.make( self[ 'reservation/edit' ][ 'printmode' ], default = opts['printmode'] )
		else:
			input_printmode = umcd.make( self[ 'reservation/edit' ][ 'printmode' ] )
		idlist_ok_button.append(input_printmode.id())
		#lst.add_row([input_printmode])
		lst.add_row( [ input_profile, input_printmode ] )

#                 # file
#                 default = []
#                 if 'files' in opts:
#                 	for filename in opts['files']:
#                                 #default.append( { 'files' : filename } )
#                                 default.append( filename )
# 		input_filename = umcd.TextInput( ( 'filenames', umc.String( _( 'Filename' ), required = False ) ) )
# 		#input_filename = umcd.make( self[ 'reservation/edit' ][ 'filename' ], default = '', attributes = { 'width' : '250' } )
#                 input_files = umcd.DynamicList( self[ 'reservation/edit' ][ 'files' ],
#                                                                   [ _( 'Upload Digital Teaching Resources' ) ], [ input_filename ],
#                                                                   default = default )
#                 input_files[ 'colspan' ] = '2'
# 		idlist_ok_button.append(input_files.id())
#                 lst.add_row( [ input_files ] )
# 
		# Teaching Resource Upload
		if object.options.get('distributionID'):
			lst.add_row( [ _('Distribution project %s has been created for this reservation.') % object.options.get('distributionID') ] )
		else:
			input_fileupload = umcd.make( self[ 'reservation/edit' ][ 'files' ], default= opts['files'] )
			idlist_ok_button.append(input_fileupload.id())
			lst.add_row( [ input_fileupload ] )

			# Copy back to teacher
			input_collectfiles = umcd.make( self[ 'reservation/edit' ][ 'collectfiles' ], default= int(opts['collectfiles']) )
			idlist_ok_button.append(input_collectfiles.id())
			lst.add_row( [ input_collectfiles ] )

		lst.add_row( [ ] )	# empty line

		# determine acltarget
		if not _defined('reservationID', opts):
			acltarget = 'own'
		else:
			if opts['ownername'] == self._username:
				acltarget = 'own'
			else:
				acltarget = 'other'
		opts['target'] = acltarget

		#ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_edit: widgets done' )
		if action == 'edit':
			# build set/cancel button
			#req_list = umcp.Command( args = [ 'reservation/list' ], opts = opts )
			write_opts = copy.copy(opts)
			write_opts['action'] = 'write'
			req = umcp.Command( args = [ 'reservation/edit' ], opts = write_opts )
			actions = ( umcd.Action( req, idlist_ok_button ) )#, umcd.Action( req_list, idlist_ok_button ) )
			if not _defined('reservationID', opts):
				item_btn_set = umcd.Button( _('Save reservation'), 'actions/ok', actions = actions, close_dialog = False )
			else:
				item_btn_set = umcd.Button( _('Save changes'), 'actions/ok', actions = actions )
			item_btn_cancel = umcd.CancelButton( attributes = { 'align' : 'right' } )
			lst.add_row( [ item_btn_set, item_btn_cancel ] )
		elif action in ('collisionmessage', 'override'):
			#ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_edit: action: %s' % action )
			reservationID, reservation_name, description, date_start, time_begin, time_end, roomname, groupname, profile = opts['collision']
			#header =  _('Collision: confirm cancellation of following reservation:')

			if action == 'collisionmessage':
				headline =  _('Collision: reservation not possible.')
			else:
				headline =  _('Collision: override existing reservation?')

			msghead =  _('Colliding reservation:')
			msglst = umcd.List()
			msglst.set_header( [ '', _( 'Date' ), _( 'Start Time' ), _( 'End Time' ), _( 'Room'), _( 'Class/Group'), _( 'Reservation profile' ) ] )
			ou = object.options['ou']
			row = []
			datelist=date_start.split('-')
			datelist.reverse()
			item_date='.'.join(datelist)
			if description:
				string = profile+' ['+description+']'
			else:
				string = profile
			groupstring = groupname.replace(ou+'-','')

			school_lesson = _types.time_to_lesson(time_begin)
			if school_lesson['start'] == time_begin:
				time_begin_string = school_lesson['name']+' ('+time_begin+')'
			else:
				time_begin_string = time_begin
			school_lesson = _types.time_to_lesson(time_end)
			if school_lesson['end'] == time_end:
				time_end_string = school_lesson['name']+' ('+time_end+')'
			else:
				time_end_string = time_end

			icon = 'reservation/reservation'
			iconwidget = umcd.Button( '', icon, () )
			row.append(iconwidget)
			row.append(item_date)
			row.append(time_begin_string)
			row.append(time_end_string)
			row.append(roomname)
			row.append(groupstring)
			row.append(profile)

			msglst.add_row( row )

			row = []
			if action == 'override':
				override_opts = copy.copy(opts)
				override_opts['action'] = 'override'
				req = umcp.Command( args = [ 'reservation/edit' ], opts = override_opts )
				actions = ( umcd.Action( req, idlist_ok_button ) )
				item_btn_ok = umcd.Button( _('Override'), 'actions/ok', actions = actions, close_dialog = False )
				row.append(item_btn_ok)

			item_btn_cancel = umcd.CancelButton( attributes = { 'align' : 'right' } )
			row.append(item_btn_cancel)
			msglst.add_row( row )
			msgframe = umcd.Frame( [msglst], msghead )
			#msgframe[ 'colspan' ] = '3'
			topframe = umcd.Frame( [ lst ], headline )
			frames = []
			frames.append( topframe )
			frames.append( msgframe )
			res.dialog = frames
			#ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_edit: msg done' )
			self.revamped( object.id(), res )
			return

		ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_edit: revamped' )
		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )

	def _web_reservation_remove( self, object, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_remove: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_remove: dialog: %s' % str( res.dialog ) )

		success, messages, reservationdata = res.dialog

		reservation = object.options.get('reservationID')
		confirmed = object.options.get('confirmed')

		if not confirmed and not reservation:
			lst = umcd.List()
			res.dialog = [ umcd.Frame( [ lst ], _('No reservation has been selected') ) ]
			self.revamped( object.id(), res )
			return

		# determine acltarget
		if object.options.get('ownername') == self._username:
			acltarget = 'own'
		else:
			acltarget = 'other'

		lst = umcd.List()
		if not confirmed:
			header =  _('Please confirm cancellation of following reservation:')
			lst.set_header( [ '', _( 'Date' ), _( 'Start time' ), _( 'End time' ), _( 'Room'), _( 'Class/Group'), _( 'Reservation profile' ) ] )
			reservationID, reservation_name, description, date_start, time_begin, time_end, roomname, groupname, profile = reservationdata
			ou = object.options['ou']
			row = []
			datelist=date_start.split('-')
			datelist.reverse()
			item_date='.'.join(datelist)
			if description:
				string = profile+' ['+description+']'
			else:
				string = profile
			groupstring = groupname.replace(ou+'-','')

			school_lesson = _types.time_to_lesson(time_begin)
			if school_lesson['start'] == time_begin:
				time_begin_string = school_lesson['name']+' ('+time_begin+')'
			else:
				time_begin_string = time_begin
			school_lesson = _types.time_to_lesson(time_end)
			if school_lesson['end'] == time_end:
				time_end_string = school_lesson['name']+' ('+time_end+')'
			else:
				time_end_string = time_end

			icon = 'reservation/reservation'
			iconwidget = umcd.Button( '', icon, () )
			row.append(iconwidget)
			row.append(item_date)
			row.append(time_begin_string)
			row.append(time_end_string)
			row.append(roomname)
			row.append(groupstring)
			row.append(profile)

			lst.add_row( row )

			opts = { 'reservationID': reservationID, 'confirmed': True, 'target': acltarget }
			req = umcp.Command( args = [ 'reservation/remove' ], opts = opts )
			actions = ( umcd.Action( req ) )
			item_btn_ok = umcd.Button( _('Remove'), 'actions/ok', actions = actions, close_dialog = False )
			item_btn_cancel = umcd.CancelButton( attributes = { 'align' : 'right' } )
			lst.add_row( [ item_btn_ok, item_btn_cancel ] )
		else:
			if success:
				header = _('Reservation cancelled successfully')
			else:
				header = _('Error while cancelling reservation')
				lst.add_row( [] )
				lst.add_row( [ _('Please ask local administrator for further details.') ] )
			for msg in messages:
				lst.add_row( [ msg ] )
			lst.add_row( [ umcd.CloseButton( ) ] )

		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( object.id(), res )


	def _web_reservation_profile_list( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_profile_list: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_profile_list: dialog: %s' % str( res.dialog ) )

		( searchresult ) = res.dialog
 
		opts = _types.defaults.merge(object.options, 'reservation_profile_list')
		debugmsg( ud.ADMIN, ud.INFO, '_web_profile_list: opts: %s' % str( opts ) )

		headline = _( "Reservation profiles" )
		framelst = []

		# 'create new' button
		icon = 'reservation/profile_add'
		req = umcp.Command( args = [ 'reservation/profile/edit' ],
				    opts = { 'resprofileID': '' } )
		req.set_flag( 'web:startup', True )
		req.set_flag( 'web:startup_reload', True )
		req.set_flag( 'web:startup_dialog', True )
		req.set_flag( 'web:startup_format', _('New reservation profile') )
		createbtn = umcd.Button( _('New Reservation Profile'), icon, umcd.Action( req ) )
		seperator_line = umcd.HTML(text='<hr>')

		lst = umcd.List()
		lst.add_row( [ createbtn ] )
		lst.add_row( [ seperator_line ] )


		# Search
		#headline = _( 'Search' )

		umccommand = 'reservation/profile/list'
		select = umcd.make( self[ umccommand ][ 'key' ], default = opts['key'], attributes = { 'width' : '200' } )
		text = umcd.make( self[ umccommand ][ 'searchfilter' ], default = opts['searchfilter'], attributes = { 'width' : '250' } )
		#form = umcd.SearchForm( umccommand, [ [ ( select, 'profile_name' ), ( text, '*' ) ] ], opts )
		form = umcd.SearchForm( umccommand, [ [ ( select, opts['key'] ), ( text, opts['searchfilter'] ) ] ], opts = {'action': 'search'}, search_button_label = _("Show all") )
		lst.add_row([ form ] )
		framelst.append( umcd.Frame( [ lst ], headline ) )

		# List / Search Results
		#headline = '%s ( %s=%s )' % ( _('Searchresults'), _(opts['key']), opts['searchfilter'])
		headline = '%s:' % _('Searchresults')
		tablelst = umcd.List()
		if searchresult:
			tablelst.set_header( [ _( 'Reservation profile' ), _( 'Description' ), _('Owner'), _('Edit'), _('Copy'), _('Delete') ] )
			for resprofileID, profile_name, description, ownername, isglobaldefault in searchresult:
				row = []
				#icon = 'reservation/profile_lights'
				#iconbtn = umcd.Button( '', icon, actions = () )
				#row.append(iconbtn)
				row.append(profile_name)

				row.append(description or '')

				if ownername == _types.AdminUser or isglobaldefault:
					ownerstring = 'Vorgabe'
				else:
					ownerstring = ownername
				row.append(ownerstring)

				if ownername == self._username:
					acltarget = 'own'
				else:
					acltarget = 'other'
				if self.permitted('reservation/profile/edit', { 'target': acltarget } ) and not isglobaldefault:
					# edit
					select_opts = { 'resprofileID': resprofileID, 'profile_name': profile_name, 'target': acltarget }
					req = umcp.Command( args = [ 'reservation/profile/edit' ],
							    opts = select_opts )
					req.set_flag( 'web:startup', True )
					req.set_flag( 'web:startup_reload', True )
					req.set_flag( 'web:startup_dialog', True )
					req.set_flag( 'web:startup_format', _('Edit Profile')+' [%(profile_name)s]' )
					icon = 'reservation/edit'
					editbtn = umcd.Button( '', icon, umcd.Action( req ) , helptext = _('Click to edit this profile') )
					row.append(editbtn)
				else:
					# edit
					icon = 'reservation/edit_disabled'
					if isglobaldefault:
						helptext = _('This profile is a given default')
					else:
						helptext = _('You are not the owner of this profile')
					editbtn = umcd.Button( '', icon, actions=() , helptext = helptext )
					row.append(editbtn)
				#else:
				#	row.append(umcd.Fill( 1 ))

				# copy
				req = umcp.Command( args = [ 'reservation/profile/edit' ], opts =  { 'action': 'copy', 'resprofileID': resprofileID, 'profile_name': profile_name } )
				req.set_flag( 'web:startup', True )
				req.set_flag( 'web:startup_reload', True )
				req.set_flag( 'web:startup_dialog', True )
				req.set_flag( 'web:startup_format', _('Copy reservation profile')+' [(%(profile_name)s]' )
				icon = 'reservation/copy'
				copybtn = umcd.Button( '', icon, umcd.Action( req ), helptext = _('Click to copy and edit this profile') )
				row.append(copybtn)

				if self.permitted('reservation/profile/remove', { 'target': acltarget } ) and not isglobaldefault:
					# delete
					select_opts = { 'resprofileID': resprofileID, 'action': 'delete', 'target': acltarget }
					req = umcp.Command( args = [ 'reservation/profile/remove' ],
							    opts = select_opts )
					req.set_flag( 'web:startup', True )
					req.set_flag( 'web:startup_reload', True )
					req.set_flag( 'web:startup_dialog', True )
					req.set_flag( 'web:startup_format', _('Remove profile') )
					icon = 'reservation/profile_lights_del'
					delbtn = umcd.Button( '', icon, umcd.Action( req ), helptext = _('Click to remove this profile') )
					row.append(delbtn)

				else:
					# delete
					icon = 'reservation/profile_lights_del_disabled'
					if isglobaldefault:
						helptext = _('This profile is a given default')
					else:
						helptext = _('You are not the owner of this profile')
					delbtn = umcd.Button( '', icon, actions=(), helptext = helptext )
					row.append(delbtn)
				#else:
				#	row.append(umcd.Fill( 1 ))

				tablelst.add_row( row )
		else:
			if opts.get('action') == 'search':
				tablelst.add_row( [_('No matching reservation profiles found')] )
			else:
				tablelst.add_row( [_('Click search button to list reservation profiles')] )

		framelst.append( umcd.Frame( [ tablelst ], headline ) )

		#res.dialog = umcd.Frame( [ lst ], headline )
		res.dialog = framelst
		self.revamped( object.id(), res )


	def _web_reservation_profile_edit( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_profile_edit: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_profile_edit: dialog: %s' % str( res.dialog ) )

		#opts = res.dialog
		opts = _types.defaults.merge(object.options, 'reservation_profile_edit')
		debugmsg( ud.ADMIN, ud.INFO, '_web_profile_edit: opts: %s' % str( opts ) )

		headline = _( "Edit reservation profile" )
		#framelst = []

		lst = umcd.List()
		idlist_ok_button = []

		# determine acltarget
		if not _defined('resprofileID', opts):
			acltarget = 'own'
		else:
			if opts['ownername'] == self._username:
				acltarget = 'own'
			else:
				acltarget = 'other'
		opts['target'] = acltarget
		debugmsg( ud.ADMIN, ud.INFO, '_web_profile_edit: target: %s' % str( acltarget ) )

		# Name
		if not _defined('resprofileID', opts):
			#opts['new_profile']=True
			widget_profilename = umcd.make( self[ 'reservation/profile/edit' ][ 'profile_name' ], default = opts['profile_name'] )
		else:
			widget_profilename = umcd.make_readonly( self[ 'reservation/profile/edit' ][ 'profile_name' ], default = opts['profile_name'] )

		input_description = umcd.make( self[ 'reservation/profile/edit' ][ 'description' ], default = opts['description'] )
		idlist_ok_button.extend( [ widget_profilename.id(), input_description.id() ] )
		lst.add_row([widget_profilename, input_description])
		#framelst.append( umcd.Frame( [ lst ], headline ) )

		#\item Auswahl des Internet-Filters
		input_internetfilter = umcd.make( self[ 'reservation/profile/edit' ][ 'internetfilter' ], default = opts['internetfilter'] )
		idlist_ok_button.append(input_internetfilter.id())
		#lst.add_row([input_internetfilter])

####################### Noch nicht zu implementieren
#		#\item Auswahl an erlaubten Programmen
#		debugmsg( ud.ADMIN, ud.INFO, '_web_profile_edit: white start:' )
#		fields = [
#			umcd.make( ( None, _types.licensedprogram_whitelist ), default = 'pleaseselect', labelID='pleaseselect' ),
#			umcd.make( ( None, _types.licenses_avail ), default = '1' )
#			
#			]
#		defaults=[]
#		if _defined('licensedprogram_whitelist', opts):
#			for k in opts['licensedprogram_whitelist']:
#				key = k.split(' : ')
#				# get program Name
#				for pair in _types.syntax['licensedprogram_whitelist']._choices:
#					if pair[0] == key[0]:
#						#defaults.append( ( k, '%s' % pair[1] ) ) 
#						defaults.append( ( k, '%s : %s' % ( pair[1], key[1] ) ) ) 
#						break
#			#debugmsg( ud.ADMIN, ud.INFO, '_web_profile_edit: white defaults: %s' % defaults )
#		input_programs_whitelist = umcd.make( self[ 'reservation/profile/edit' ][ 'licensedprogram_whitelist' ], fields = fields, default = defaults, separator = ' : ' )
#		idlist_ok_button.append(input_programs_whitelist.id())
#		#lst.add_row([input_programs_whitelist])
#
#		#\item Auswahl an nicht erwuenschten Programmen
#		fields = [ umcd.make( ( None, _types.freeprogram_blacklist ), default = 'pleaseselect', labelID='pleaseselect' ) ]
#		defaults=[]
#		if _defined('freeprogram_blacklist', opts):
#			for i in opts['freeprogram_blacklist']:
#				for pair in _types.syntax['freeprogram_blacklist']._choices:
#					if pair[0] == i:
#						defaults.append( ( i, pair[1]) ) 
#						break
#		input_programs_blacklist = umcd.make( self[ 'reservation/profile/edit' ][ 'freeprogram_blacklist' ], fields = fields, default = defaults )
#		idlist_ok_button.append(input_programs_blacklist.id())
#		lst.add_row([input_programs_whitelist, input_programs_blacklist])

		#\item Auswahl erlaubter Zugriffe auf Serverfreigaben
		input_allow_homeshare = umcd.make( self[ 'reservation/profile/edit' ][ 'homeshare' ] , default = int(opts['homeshare']) )
		input_allow_classshare = umcd.make( self[ 'reservation/profile/edit' ][ 'classshare' ] , default = int(opts['classshare']) )
		input_allow_schoolshare = umcd.make( self[ 'reservation/profile/edit' ][ 'schoolshare' ], default = int(opts['schoolshare']) )
		input_allow_extrashares = umcd.make( self[ 'reservation/profile/edit' ][ 'extrashares' ] , default = int(opts['extrashares']) )
		idlist_ok_button.append(input_allow_homeshare.id())
		idlist_ok_button.append(input_allow_classshare.id())
		idlist_ok_button.append(input_allow_schoolshare.id())
		idlist_ok_button.append(input_allow_extrashares.id())
		lst.add_row([input_internetfilter])
		lst.add_row([input_allow_homeshare, input_allow_classshare ] )
		lst.add_row([input_allow_schoolshare, input_allow_extrashares ] )

		# build set/cancel button
		#req_list = umcp.Command( args = [ 'reservation/profile/list' ] )
		req = umcp.Command( args = [ 'reservation/profile/write' ], opts = opts )
		actions = ( umcd.Action( req, idlist_ok_button ) )#, umcd.Action( req_list ) )
		#if 'new_profile' in opts:
		if not _defined('resprofileID', opts):
			item_btn_set = umcd.Button( _('Create reservation profile'), 'actions/ok', actions = actions )
		else:
			item_btn_set = umcd.Button( _('Save changes'), 'actions/ok', actions = actions )
		item_btn_cancel = umcd.CancelButton( attributes = { 'align' : 'right' } )
		lst.add_row( [ item_btn_set, item_btn_cancel ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )

	def _web_reservation_profile_remove( self, object, res ):
		ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_profile_remove: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_reservation_profile_remove: dialog: %s' % str( res.dialog ) )

		success, messages, profiledata = res.dialog

		resprofileID = object.options.get('resprofileID')
		confirmed = object.options.get('confirmed')

		if not confirmed and not resprofileID:
			lst = umcd.List()
			res.dialog = [ umcd.Frame( [ lst ], _('No reservation profile has been selected') ) ]
			self.revamped( object.id(), res )
			return

		# determine acltarget
		if object.options.get('ownername') == self._username:
			acltarget = 'own'
		else:
			acltarget = 'other'

		lst = umcd.List()
		if not confirmed:
			header =  _('Please confirm removal of following reservation profile:')
			lst.set_header( [ '', _( 'Reservation profile' ), _('Description') ] )
			profile_name, description = profiledata
			row = []

			icon = 'reservation/profile_lights'
			iconwidget = umcd.Button( '', icon, () )
			row.append(iconwidget)
			row.append(profile_name)
			row.append(description)

			lst.add_row( row )

			opts = { 'resprofileID': resprofileID, 'confirmed': True, 'target': acltarget }
			req_list = umcp.Command( args = [ 'reservation/profile/list' ] )
			req = umcp.Command( args = [ 'reservation/profile/remove' ], opts = opts )
			actions = ( umcd.Action( req ), umcd.Action( req_list ) )
			item_btn_ok = umcd.Button( _('Remove'), 'actions/ok', actions = actions, close_dialog = False )
			item_btn_cancel = umcd.CancelButton( attributes = { 'align' : 'right' } )
			lst.add_row( [ item_btn_ok, item_btn_cancel ] )
		else:
			if success:
				header = _('Reservation profile successfully removed')
			else:
				header = _('Error while removing reservation profile')
				lst.add_row( [] )
				lst.add_row( [ _('Please ask local administrator for further details.') ] )
			for msg in messages:
				lst.add_row( [ msg ] )

		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( object.id(), res )

	def _web_reservation_lessontimes_edit( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_lessontimes_edit: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_lessontimes_edit: dialog: %s' % str( res.dialog ) )

		# No defaults need to be processed
		#opts = _types.defaults.merge(object.options, 'reservation_lessontimes_edit')
		#debugmsg( ud.ADMIN, ud.INFO, '_web_lessontimes_edit: opts: %s' % str( opts ) )

		message = res.dialog

		headline = _( "Edit lessontime definitions" )

		lst = umcd.List()
		idlist_ok_button = []

		if message:
			lst.add_row( [ message ] )
			lst.add_row( [ ] )

		#defaultList =[]
		#for lessontime_name, description, startTime, endTime in object.options['lessontimes']:
		#	defaultList.append( { 'lessontime_name' : lessontime_name, 'description' : description,
		#	                  'startTime' : startTime, 'endTime' : endTime } )

                #input_lessontime_name = umcd.TextInput( ( 'lessontime_name', _types.descr_text ) )
                #input_description = umcd.TextInput( ( 'description', self[ 'reservation/lessontimes/edit' ][ 'description' ] ) )
                #input_startTime = umcd.TextInput( ( 'startTime', self[ 'reservation/lessontimes/edit' ][ 'startTime' ] ) )
                #input_endTime = umcd.TextInput( ( 'endTime', self[ 'reservation/lessontimes/edit' ][ 'endTime' ] ) )
		
		heading = []
		widgets = []
		attrs = [ 'lessontime_name', 'startTime', 'endTime', 'description' ]
		widthlist = [ '80', '40', '40', '300' ]
		width = dict( zip(attrs, widthlist) )
		for key in attrs:
			heading.append( self[ 'reservation/lessontimes/edit' ][ key ][1].label )
			widgets.append( umcd.TextInput( ( key, self[ 'reservation/lessontimes/edit' ][ key ][1] ), attributes = { 'width' : width[key] } ) )
			#widgets.append( umcd.make( ( key, self[ 'reservation/lessontimes/edit' ][ key ] ) ) )
                multiInput = umcd.DynamicList( ('lessontimes', _types.lessontime_table) , heading, widgets,
                                                                  default = object.options['lessontimes'] )
                multiInput[ 'colspan' ] = str(len(heading))
		idlist_ok_button.append( multiInput.id() )
                lst.add_row( [ multiInput ] )

                lst.add_row( [ ] )	# empty line

		write_opts = copy.copy(object.options)
		write_opts['action'] = 'write'
		req = umcp.Command( args = [ 'reservation/lessontimes/edit' ], opts = write_opts )
		actions = ( umcd.Action( req, idlist_ok_button ) )
		#item_btn_set = umcd.SetButton( actions )
		item_btn_set = umcd.Button( _('Save changes'), 'actions/ok', actions = actions )
		#item_btn_cancel = umcd.CancelButton( attributes = { 'align' : 'right' } )
		lst.add_row( [ item_btn_set ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )

