#!/usr/bin/python2.4
#
# Univention Management Console
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

import operator, time

import univention.management.console as umc
import univention.management.console.dialog as umcd
import univention.management.console.protocol as umcp

import univention.debug as ud
import univention.config_registry

_ = umc.Translation( 'univention.management.console.handlers.roomadmin' ).translate

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


class Web( object ):
	def _web_roomadmin_room_list( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_search: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_search: dialog: %s' % str( res.dialog ) )

		( computers_blocked4internet, groups, computers, host2user, user2realname, onlinestatus, demomode, hideitems ) = res.dialog

		room = object.options.get( 'room', None )
		javascript = umcd.HTML ("<script src='/univention-management-console/js/umc/roomadmin/request_snapshot.js' type='text/javascript'></script>" +
				"""<script type='text/javascript'>
				dojo.addOnLoad (function () {
						window.setInterval( function () {umc.roomadmin.updateData ('%s', '%s');}, 5000);
				});
				</script>""" % (self._sessionid, room))

		curgrpdn = None
		curgrpattrs = None
		curgrpmembers = None

		headline = _( "Computer Room Administration" )

		lst = umcd.List()

		# create choiceButton
		choices = [ { 'description': _('--- Please choose ---'), 'actions': () } ]

		default = 0

		actions = []
		req = umcp.Command( args = [ 'roomadmin/room/list' ], opts = { 'room' : '::all' } )
		actions.append( umcd.Action( req ) )
		choices.append( { 'description': _('All'), 'actions': actions } )

		if room == '::all':
			default = len(choices)-1

		# sort groups by cn attribute
		sorted_groups = []
		for grpdn, grpdata in groups.items():
			sorted_groups.append( ( grpdata[ 0 ][ 'cn' ][ 0 ], grpdn, grpdata ) )

		sorted_groups = sorted( sorted_groups, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
								key = operator.itemgetter( 0 ) )

		for cn, grpdn, grpdata in sorted_groups:
			req = umcp.Command( args = [ 'roomadmin/room/list' ], opts = { 'room' : cn } )
			choices.append( { 'description' : cn, 'actions' : [ umcd.Action( req ) ] } )

			if cn == room:
				default = len( choices ) - 1
				curgrpdn = grpdn
				curgrpattrs = grpdata[ 0 ]
				curgrpmembers = grpdata[ 1 ]

		if room == '::all':
			curgrpmembers = computers.keys()

		choicebutton = umcd.ChoiceButton( _( 'Computer Room' ), choices = choices, default = default )
		choicebutton['width'] = '250'
		buttons = [ choicebutton ]

		if room and room != '':
			refresh_actions = []
			refresh_icon = 'roomadmin/view-refresh'
			refresh_req = umcp.Command( args = [ 'roomadmin/room/list' ], opts = { 'room' : room } )
			refresh_actions.append( umcd.Action( refresh_req ) )
			refresh_button = umcd.Button( _( 'Refresh' ), refresh_icon, actions=refresh_actions )
			buttons.append (refresh_button)

			if demomode and room != '::all':
				stop_actions = []
				stop_icon = 'roomadmin/demoend'
				stop_req = umcp.Command( args = [ 'roomadmin/italc/demo/stop' ], opts = { 'ipaddrs': [], 'room' : room } )
				stop_actions.append( umcd.Action( stop_req ) )
				stop_actions.append( umcd.Action( refresh_req ) )
				stop_demo_button = umcd.Button( _( 'Stop video mode' ), stop_icon, actions=stop_actions )
				buttons.append (stop_demo_button)

			if room != '::all':
				if demomode:
					buttons.extend ((umcd.Text (''), umcd.Text ('')))
				else:
					buttons.extend ((umcd.Text (''), umcd.Text (''), umcd.Text (''), umcd.Text (''), umcd.Text ('')))
				italc_demo_master_selection = umcd.make( self[ 'roomadmin/italc/demo/start/window' ][ 'masterip' ], attributes = { 'width' : '250' } )
				italc_demo_master_selection.syntax.clearChoices ()

				buttons.append (italc_demo_master_selection)

		select_refresh = umcd.List()
		select_refresh.add_row (buttons)
		lst.add_row( [ select_refresh ] )

		# stop here if no room has been selected

		if not room or room == '':
			res.dialog = umcd.Frame( [ lst ], headline )
			self.revamped( object.id(), res )
			return

		# create computer table

		tablelst = umcd.List()

		headerlist = [ _( 'Monitor Desktop With UltraVNC' ), _('Room'), _( 'Logged On' ) ]
		if not 'ipaddress' in hideitems or not 'macaddress' in hideitems:
			headerlist.append( _( 'Addresses' ) )
		if not 'inventorynumber' in hideitems:
			headerlist.append( _( 'Inventory#' ) )
		headerlist.append( _('Internet Access') )
		if demomode:
			headerlist.append( _('Video mode') )
		headerlist.append( '' )
		tablelst.set_header( headerlist )

		boxes = []

		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_list: curgrpmembers=%s' % str( curgrpmembers ) )

		sorted_members = []
		for memberdn in curgrpmembers:
			computer = computers[memberdn]

			sorted_members.append( ( computer[ 'cn' ][ 0 ], memberdn ) )

		sorted_members = sorted( sorted_members, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
								 key = operator.itemgetter( 0 ) )

		configRegistry = univention.config_registry.ConfigRegistry()
		configRegistry.load()
		vncPort = configRegistry.get('umc/roomadmin/vnc/port','5900')
		vncEnabled = configRegistry.get('umc/roomadmin/vnc/enable','yes').lower() in ('yes','true','1')

		idlist = []
		for cn, memberdn in sorted_members:
			computer = computers[memberdn]
			ipaddr = None
			box_id = None

			# computername and VNC link
			icon = 'roomadmin/%s' % self._determine_host_icon( computer )
			if computer.has_key('aRecord') and computer['aRecord'] and vncEnabled:
				img = umcd.Link( description = cn,
								 icon=icon,
								 link='/univention-management-console/ultravnc.php?hostname=%s&port=%s' % (computer['aRecord'][0], vncPort)
								)
				btn = umcd.Link( description = cn,
								 link='/univention-management-console/ultravnc.php?hostname=%s&port=%s' % (computer['aRecord'][0], vncPort) )
			else:
				img = umcd.Image( icon )
				btn = umcd.Text( cn )
			img[ 'type' ] = 'object_links'
			btn[ 'type' ] = 'object_links'


			# room name(s)
			roomlist = []
			for grpcn, grpdn, grpdata in sorted_groups:
				if memberdn in grpdata[1]:
					roomlist.append(grpcn)
			roomlist = [ umcd.Image('roomadmin/room'), ', '.join(roomlist) ]

			# user that is logged on
			if computer.has_key('aRecord') and computer['aRecord']:
				ipaddr = computer['aRecord'][0]
				if vncEnabled:
					userlst = [ umcd.Link( description = cn,
										   icon = 'roomadmin/user',
										   link = '/univention-management-console/ultravnc.php?hostname=%s&port=%s' % (ipaddr, vncPort),
										   attributes = {	'onmouseover' : "umc.roomadmin.showSnapshot (this, '%s', '%s');" % (self._sessionid, ipaddr),
															'onmouseout':"umc.roomadmin.hideSnapshot ('%s');" % (ipaddr, ),
															}
										   ) ]
				else:
					userlst = [ umcd.Image('roomadmin/user', attributes = {
						'onmouseover':"umc.roomadmin.showSnapshot (this, '%s', '%s');" % (self._sessionid, ipaddr),
						'onmouseout':"umc.roomadmin.hideSnapshot ('%s');" % (ipaddr, ),
						}) ]
			else:
				userlst = [ umcd.Image('roomadmin/user') ]
			username = _('unknown')
			if host2user.has_key( cn.lower() ):
				username = host2user[ cn.lower() ]
				if user2realname.has_key( username ):
					username = "%s (%s)" % (user2realname[ username ], username)
				if ipaddr:
					userdiv = umcd.HTML (("<div id='%s.username'>" % ipaddr) + username + '</div>')
					userlst.append(userdiv)
				else:
					userlst.append(username)
			else:
				if computer.has_key('aRecord') and computer['aRecord'] and onlinestatus.has_key(computer['aRecord'][0]):
					if not onlinestatus[ computer['aRecord'][0] ]:
						userlst = [ umcd.Image('roomadmin/offline'), _('offline') ]
					else:
						if ipaddr:
							userdiv = umcd.HTML (("<div id='%s.username'>" % ipaddr) + username + '</div>')
							userlst.append(userdiv)
						else:
							userlst.append(username)
				else:
					if ipaddr:
						userdiv = umcd.HTML (("<div id='%s.username'>" % ipaddr) + username + '</div>')
						userlst.append(userdiv)
					else:
						userlst.append(username)
			if room and room != '::all' and ipaddr:
				italc_demo_master_selection.syntax.addChoice (ipaddr, '%s: %s' % (cn, username))

			# IP Address
			str_ipaddr = computer.get('aRecord',[''])[0]
			# MAC Address
			str_macaddr = computer.get('macAddress', [''])[0]
			# Inventory Number
			text_inventorynumber = umcd.Text( computer.get('univentionInventoryNumber', ['---'])[0] )

			# icon for internet access status
			internetaccess = umcd.Text( '---' )
			chk = ''

			if computer.has_key('aRecord') and computer['aRecord']:
				if computer['aRecord'][0] in computers_blocked4internet:
					internetaccess = umcd.Image('roomadmin/internetdisabled')
				else:
					internetaccess = umcd.Image('roomadmin/internetenabled')

				chk = umcd.Checkbox( static_options = { 'ipaddrs': computer['aRecord'][0] } )
				idlist.append( chk.id() )

			demostatus = umcd.Text( '' )
			if demomode and ipaddr:
				if ipaddr in demomode['ipaddrs']:
					demostatus = umcd.Image('roomadmin/democlient')
				elif ipaddr == demomode['masterip']:
					demostatus = umcd.Image('roomadmin/demomaster')

			row = [ (img, btn), roomlist, userlst ]
			if not 'ipaddress' in hideitems or not 'macaddress' in hideitems:
				addrlst = []
				if not 'ipaddress' in hideitems and str_ipaddr:
					addrlst.append( str_ipaddr )
				if not 'macaddress' in hideitems and str_macaddr:
					addrlst.append( str_macaddr )
				if not addrlst:
					addrlst = [ '---' ]
				row.append( umcd.HTML('<br>'.join(addrlst)) )
			if not 'inventorynumber' in hideitems:
				row.append( text_inventorynumber )
			row.append( internetaccess )
			if demomode:
				row.append( demostatus )
			row.append( chk )
			tablelst.add_row( row )


		def createChoiceEntry(cmd, description):
			req_set = umcp.Command( args = [ cmd ], opts = { 'ipaddrs': [], 'room' : room } )
			req = umcp.Command( args = [ 'roomadmin/room/list' ], opts = { 'room' : room } )
			actions = ( umcd.Action( req_set, idlist, True ), umcd.Action( req ) )
			return { 'description': description, 'actions': actions }

		# add select box
		if room and room != '::all':
			idlist.append (italc_demo_master_selection.id ())

		choices = [ { 'description': '---', 'actions': '::none' },
					{ 'description': 'INVERT SELECTION', 'actions': '::invert',     'idlist': idlist },
					{ 'description': 'SELECT ALL',       'actions': '::select_all', 'idlist': idlist },
					createChoiceEntry( 'roomadmin/set/access/internet/enable', _( 'enable internet access' ) ),
					createChoiceEntry( 'roomadmin/set/access/internet/disable', _( 'disable internet access' ) ),
					createChoiceEntry( 'roomadmin/italc/lock/screen', _( 'Lock Screen' ) ),
					createChoiceEntry( 'roomadmin/italc/unlock/screen', _( 'Unlock Screen' ) ),
					createChoiceEntry( 'roomadmin/italc/lock/input', _( 'Lock Input Devices' ) ),
					createChoiceEntry( 'roomadmin/italc/unlock/input', _( 'Unlock Input Devices' ) ),
					createChoiceEntry( 'roomadmin/wol/send', _( 'Power On By Wake On LAN') ),
					createChoiceEntry( 'roomadmin/italc/logout', _( 'Logout Users' ) ),
					createChoiceEntry( 'roomadmin/italc/reboot', _( 'Reboot Computers' ) ),
					createChoiceEntry( 'roomadmin/italc/shutdown', _( 'Shutdown Computers' ) ),
					]

		if room and room != '::all':
			req = umcp.Command( args = [ 'roomadmin/italc/supervising/mode' ], opts = { 'ipaddrs': [], 'room' : room } )
			req.set_flag( 'web:startup', True )
			req.set_flag( 'web:startup_reload', True )
			req.set_flag( 'web:startup_dialog', True )
			req.set_flag( 'web:startup_format', _('Supervising Computers') )
			actions = [ umcd.Action( req, idlist, True ) ]

			choices.extend ([
				{ 'actions': actions, 'description': _( 'Start supervising mode' ) },
				createChoiceEntry( 'roomadmin/italc/demo/start/window', _( 'Start video mode (window)' ) ),
				createChoiceEntry( 'roomadmin/italc/demo/start/fullscreen', _( 'Start video mode (fullscreen)' ) ),
				])

		select = umcd.ChoiceButton( _( 'Select the Operation' ), choices, close_dialog = False )

		# use length of headerlist for fill-item
		tablelst.add_row( [ umcd.Fill( len(headerlist)-1 ), select ] )

		lst.add_row( [ javascript ] )
		lst.add_row( [ tablelst ] )


		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )



	def _determine_host_icon(self, attrs):
		if not attrs or not attrs.has_key('objectClass'):
			return "unknown"

		if 'univentionClient' in attrs['objectClass']:
			if 'posixAccount' in attrs['objectClass'] or 'shadowAccount' in attrs['objectClass']:
				return 'client'
			else:
				return 'ipmanagedclient'
		elif 'univentionMacOSClient' in attrs['objectClass']:
			return 'macos'
		elif 'univentionMobileClient' in attrs['objectClass']:
			return 'mobileclient'
		elif 'univentionThinClient' in attrs['objectClass']:
			return 'thinclient'
		elif 'univentionWindows' in attrs['objectClass']:
			return 'windows'
		elif 'univentionWindows' in attrs['objectClass']:
			return 'windows'
		elif 'univentionMemberServer' in attrs['objectClass']:
			return 'memberserver'
		elif 'univentionDomainController' in attrs['objectClass']:
			if attrs.has_key('univentionServerRole'):
				for role in ['master', 'backup', 'slave']:
					if role in attrs['univentionServerRole']:
						return 'domaincontroller_%s' % role
		return 'unknown'


	def __roomadmin_search_form( self, opts, filter = '*', key = 'name', umccommand = 'roomadmin/room/search' ):
		select = umcd.make( self[ umccommand ][ 'key' ], default = key, attributes = { 'width' : '200' } )
		text = umcd.make( self[ umccommand ][ 'filter' ], default = filter, attributes = { 'width' : '250' } )
		form = umcd.SearchForm( umccommand, [ [ ( select, 'name' ), ( text, '*' ) ] ], opts )
		return form

	def _web_roomadmin_room_search( self, object, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_search: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_search: dialog: %s' % str( res.dialog ) )

		searchfilter = object.options.get('filter', '*')
		searchkey = object.options.get('key', 'name')
		availableOU, roomgroups = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )
		debugmsg( ud.ADMIN, ud.INFO, 'availableOU: %s' % availableOU )
		debugmsg( ud.ADMIN, ud.INFO, 'currentOU: %s' % currentOU )

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
									'actions': [ umcd.Action( umcp.Command( args = ['roomadmin/room/search'],
																			opts = { 'ou' : ou,
																					 'filter': searchfilter,
																					 'key': searchkey },
																			incomplete = True ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False )
			lstheader.add_row( [ ouselect ] )

		req = umcp.Command( args = [ 'roomadmin/room/add' ],
							opts =  { 'ou': currentOU } )
		req.set_flag( 'web:startup', True )
		req.set_flag( 'web:startup_reload', True )
		req.set_flag( 'web:startup_dialog', True )
		req.set_flag( 'web:startup_format', _('Create new room') )
		item_createbtn = umcd.Button( _('Create new room'), 'roomadmin/roomadd', umcd.Action( req ), attributes = { 'width' : '250' } )
		item_createbtn['colspan']='2'
		if self.permitted('roomadmin/room/add', {} ):
			lstheader.add_row( [ item_createbtn ] )

		if object.incomplete:
			opts = { 'ou': currentOU }
			res.dialog = [ lstheader, umcd.Frame( [ self.__roomadmin_search_form( opts ) ], _('Search') ) ]
			self.revamped( object.id(), res )
			return

		lst = umcd.List()
		item_id_list = []
		if roomgroups:
			lst.set_header( [ _( 'Room' ), _( 'Description' ) ] )

			# sort groups by cn attribute
			sorted_groups = []
			for grpdn, grpdata in roomgroups.items():
				sorted_groups.append( ( grpdata[ 0 ][ 'cn' ][ 0 ], grpdn ) )

			sorted_groups = sorted( sorted_groups, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
									key = operator.itemgetter( 0 ) )

			for cn, roomdn in sorted_groups:
				roomattr, roommembers = roomgroups[roomdn]
				req = umcp.Command( args = [ 'roomadmin/room/edit' ],
									opts =  { 'room' : roomattr['cn'][0],
											  'roomdn': roomdn,
											  'ou': currentOU,
											  } )
				req.set_flag( 'web:startup', True )
				req.set_flag( 'web:startup_reload', True )
				req.set_flag( 'web:startup_dialog', True )
				req.set_flag( 'web:startup_format', _('Edit room "%(room)s"') )

				row = [ umcd.Button( roomattr['cn'][0], 'roomadmin/room', umcd.Action( req ) ), roomattr.get('description','') ]

				if self.permitted('roomadmin/room/remove', {} ):
					static_options = { 'room': roomattr['cn'][0], 'roomdn' : roomdn, 'ou': currentOU }
					chk_button = umcd.Checkbox( static_options = static_options )
					item_id_list.append( chk_button.id() )
					row.append(	chk_button )

				lst.add_row( row )

			if self.permitted('roomadmin/room/remove', {} ):
				req = umcp.Command( args = [ 'roomadmin/room/remove' ],
									opts= { 'room' : [], 'roomdn' : [], 'confirmed' : False, 'ou': currentOU } )
				req.set_flag( 'web:startup', True )
				req.set_flag( 'web:startup_reload', True )
				req.set_flag( 'web:startup_dialog', True )
				req.set_flag( 'web:startup_format', _('Remove Rooms') )
				actions = ( umcd.Action( req, item_id_list ) )
				choices = [ ( 'roomadmin/room/remove', _( 'Remove Rooms' ) ) ]
				select = umcd.SelectionButton( _( 'Select the Operation' ), choices, actions )
				lst.add_row( [ umcd.Fill( 2 ), select ] )
		else:
			lst.add_row( [ _( 'No groups could be found.' ) ] )



		opts = { 'ou': currentOU }
		res.dialog = [ umcd.Frame( [ self.__roomadmin_search_form( opts, searchfilter, searchkey ) ], _('Search') ),
					   umcd.Frame( [ lst ], _( 'Search Result' ) ) ]
		if self.permitted('roomadmin/room/add', {} ):
			res.dialog.insert(0, lstheader)

		self.revamped( object.id(), res )


	def _web_roomadmin_room_add(self, object, res):
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_add is calling _web_roomadmin_room_edit' )
		self._web_roomadmin_room_edit(object, res)


	def _web_roomadmin_room_edit(self, object, res):
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_edit: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_edit: dialog: %s' % str( res.dialog ) )

		availableOU, searchbaseComputers, description, roommembers, roomnamedefault = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_edit: availableOU: %s' % availableOU )
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_edit: currentOU: %s' % currentOU )

		createroom = False
		room = object.options.get('room', None)
		if room == None:
			room = roomnamedefault
			createroom = True
		roomdn = object.options.get('roomdn', None)
		if roomdn == None:
			createroom = True
		if description == None:
			description = object.options.get('description', None)

		item_id_list = []

		lst = umcd.List()

		if createroom:
			item_room = umcd.make( self[ 'roomadmin/room/set' ][ 'room' ], default = room )
		else:
			item_room = umcd.make_readonly( self[ 'roomadmin/room/set' ][ 'room' ], default = room )
		item_description = umcd.make( self[ 'roomadmin/room/set' ][ 'description' ], default = description )
		item_id_list.extend( [ item_room.id(), item_description.id() ] )


		# build user selection widget
		item_roommembers = umcd.make( self[ 'roomadmin/room/set' ][ 'roommembers' ], modulename = 'computers/computer',
									  filter='(!(&(objectClass=sambaSamAccount)(sambaAcctFlags=[I          ])))',
									  attr_display=[ 'name', ' (', 'ip', ')' ],
									  default = roommembers,
									  search_disabled = False, basedn = searchbaseComputers,
									  search_properties = [ 'name', 'mac', 'ip' ]
									  )
		item_roommembers['colspan'] = '2'
		item_id_list.append( item_roommembers.id() )


		# build set/cancel button
		opts = { 'roomdn' : roomdn, 'createroom': createroom }

		req = umcp.Command( args = [ 'roomadmin/room/set' ], opts = opts )
		actions = ( umcd.Action( req, item_id_list ), )
		if createroom:
			item_btn_set = umcd.Button( _('Create Room'), 'actions/ok', actions = actions, close_dialog = False, attributes = { 'class': 'submit', 'defaultbutton': '1' } )
		else:
			item_btn_set = umcd.Button( _('Save Changes'), 'actions/ok', actions = actions, close_dialog = False, attributes = { 'class': 'submit', 'defaultbutton': '1' } )
		item_btn_cancel = umcd.CancelButton()


		# FIXME TODO HACK HARDCODED for SFB:
		# if 438 is in availableOU then disable selection of OU
		ouselect = None
# 		if len(availableOU) > 1 and not '438' in availableOU:
# 			ouchoices = []
# 			defaultchoice = 0
# 			for ou in availableOU:
# 				if ou == currentOU:
# 					defaultchoice = len(ouchoices)
# 				ouchoices.append( { 'description' : ou,
# 									'actions': [ umcd.Action( umcp.Command( args = ['roomadmin/room/edit'],
# 																			opts = { 'ou' : ou,
# 																					 'roomdn': roomdn,
# 																					 'description': description,
# 																					 'roommembers': [],
# 																					 } ), item_id_list ) ] } )

# 			ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False )


		# build layout
		lst.add_row( [ item_room, item_description ] )
		if ouselect != None:
			lst.add_row( [ ouselect ] )
		lst.add_row( [ item_roommembers ] )
		lst.add_row( [ item_btn_cancel, item_btn_set ] )

		if createroom:
			header = _( 'Create room and assign computers' )
		else:
			header = _( 'Assign computers to room "%(room)s"' ) % { 'room': room }

		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( object.id(), res )


	def _web_roomadmin_room_set(self, object, res):
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_set: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_room_set: dialog: %s' % str( res.dialog ) )

		roomdn = object.options.get( 'roomdn', None )
		room = object.options.get('room','')

		if not roomdn:
			header = _( 'Created room "%(room)s" successfully.' ) % { 'room': room }
		else:
			header = _( 'Updated room "%(room)s" successfully.' ) % { 'room': room }

		btn = umcd.ErrorButton()

		lst = umcd.List()
		lst.add_row( [ btn ] )

		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( object.id(), res )


	def _web_roomadmin_room_remove(self, object, res):
		ud.debug( ud.ADMIN, ud.INFO, '_web_roomadmin_room_remove: options: %s' % str( object.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_roomadmin_room_remove: dialog: %s' % str( res.dialog ) )

		availableOU, success, messages = res.dialog
		currentOU = object.options.get( 'ou', availableOU[0] )

		roomlist = object.options.get('room', None)
		roomdnlist = object.options.get('roomdn', None)
		confirmed = object.options.get('confirmed', False)

		if not confirmed and not roomdnlist:
			lst = umcd.List()
			res.dialog = [ umcd.Frame( [ lst ], _('No room has been selected') ) ]
			self.revamped( object.id(), res )
			return

		lst = umcd.List()
		if not confirmed:
			header =  _('Please confirm removal of following rooms:')
			if roomlist == None:
				roomlist = []
			elif not isinstance( roomlist, list ):
				roomlist = [ roomlist ]

			for grp in roomlist:
				lst.add_row( [ grp ] )

			opts = { 'roomdn': roomdnlist, 'confirmed': True, 'ou': currentOU }
			req = umcp.Command( args = [ 'roomadmin/room/remove' ], opts = opts )
			actions = ( umcd.Action( req ) )
			item_btn_ok = umcd.Button( _('Remove'), 'actions/ok', actions = actions, close_dialog = False )
			item_btn_cancel = umcd.CancelButton( attributes = { 'align' : 'right' } )
			lst.add_row( [ item_btn_ok, item_btn_cancel ] )
		else:
			if success:
				header = _('Deleted rooms successfully.')
			else:
				header = _('Error while deleting following rooms:')
				lst.add_row( [] )
				lst.add_row( [ _('Please ask local administrator for further details.') ] )
			for msg in messages:
				lst.add_row( [ msg ] )

			btn = umcd.ErrorButton()
			lst.add_row( [ btn ] )

		res.dialog = [ umcd.Frame( [ lst ], header ) ]

		self.revamped( object.id(), res )

	def _web_roomadmin_italc_request_snapshot (self, object, res):
		ud.debug( ud.ADMIN, ud.INFO, '_web_roomadmin_italc_request_snapshot: options: %s' % str( object.options ) )
		content_type, content = res.dialog
		res.dialog = { 'Content-Type': content_type, 'Content': content }
		self.revamped( object.id(), res, rawresult = True )

	def _web_roomadmin_italc_request_data (self, object, res):
		ud.debug( ud.ADMIN, ud.INFO, '_web_roomadmin_italc_request_data: options: %s' % str( object.options ) )
		content_type, content = res.dialog
		res.dialog = { 'Content-Type': content_type, 'Content': content }
		self.revamped( object.id(), res, rawresult = True )

	def _web_roomadmin_italc_supervising_mode(self, object, res):
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_supervising_mode: options: %s' % str( object.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_roomadmin_supervising_mode: dialog: %s' % str( res.dialog ) )

		( hosts ) = res.dialog

		room = object.options.get( 'room', None )
		javascript = umcd.HTML ("<script src='/univention-management-console/js/umc/roomadmin/request_snapshot.js' type='text/javascript'></script>" +
				"""<script type='text/javascript'>
				dojo.addOnLoad (function () {
						window.setInterval( function () {umc.roomadmin.updateData ('%s', '%s');}, 5000);
				});
				</script>""" % (self._sessionid, room))

		headline = _( "Supervising Mode" )

		lst = umcd.List()

		row = []
		hosts_sorted = sorted( hosts, cmp = lambda x, y: cmp( x.get('hostname'), y.get('hostname') ) )
		for host in hosts_sorted:
			icon = 'roomadmin/%s' % self._determine_host_icon( host )
			ipaddr = host.get('aRecord', '127.0.0.1')
			hostname = host.get('hostname')
			if not hostname:
				hostname = _('unknown')
			username = host.get('username')
			if not username:
				username = _('unknown')
			realname = host.get('realname')
			if not realname:
				realname = _('unknown')

			if len(row) >= 4:
				lst.add_row( row )
				row = []

			row.append( ( umcd.Image( icon ), umcd.Text(hostname), umcd.HTML('<br>'),
						  umcd.Image( 'roomadmin/user' ), umcd.HTML (("<div id='%s.username'>" % ipaddr) + username + '</div>') ) )
			row.append( umcd.HTML( '<div id="%s.screenshot"><img src="ajax.py?session_id=%s&umcpcmd=roomadmin/italc/request/snapshot&ipaddr=%s&date=%s" width="200" height="150" /></div>'  %
								   (ipaddr, self._sessionid, ipaddr, int(time.time())) ) )

		if len(row):
			lst.add_row( row )

		lst.add_row( [ javascript ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( object.id(), res )
