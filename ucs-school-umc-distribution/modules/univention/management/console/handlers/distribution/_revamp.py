#!/usr/bin/python2.4
#
# Univention Management Console
#  distribution module
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

import time

import notifier.popen

import univention.management.console as umc
import univention.management.console.dialog as umcd
import univention.management.console.protocol as umcp

import univention.debug as ud

_ = umc.Translation( 'univention.management.console.handlers.distribution' ).translate

import inspect
def debugmsg( component, level, msg ):
	info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
	printInfo=[]
	if len(info[0])>28:
		printInfo.append('...'+info[0][-25:])
	else:
		printInfo.append(info[0])
	printInfo.extend(info[1:3])
	ud.debug(component, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))


class Web( object ):
	def __distribution_search_form( self, opts, filter = '*', key = 'name', umccommand = 'distribution/project/search' ):
		select = umcd.make( self[ umccommand ][ 'key' ], default = key, attributes = { 'width' : '200' } )
		text = umcd.make( self[ umccommand ][ 'filter' ], default = filter, attributes = { 'width' : '250' } )
		form = umcd.SearchForm( umccommand, [ [ ( select, 'name' ), ( text, '*' ) ] ], opts )
		return form

	def _web_distribution_project_search( self, umcobject, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_distribution_search: options: %s' % str( umcobject.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_distribution_search: dialog: %s' % str( res.dialog ) )

		#
		# get data
		#
		cmddata = res.dialog

		searchfilter = umcobject.options.get('filter', '*')
		searchkey = umcobject.options.get('key', 'name')
		availableOU = cmddata.get('availableOU', [])
		currentOU = umcobject.options.get( 'ou', availableOU[0] )
		debugmsg( ud.ADMIN, ud.INFO, 'currentOU: %s' % currentOU )

		#
		# create widgets
		#
		item_id_list = []
		lstheader = umcd.List()

		# create "add distribution" button
		req = umcp.Command( args = [ 'distribution/project/distribute' ],
							opts =  { 'ou': currentOU }
							)
		req.set_flag( 'web:startup', True )
		req.set_flag( 'web:startup_reload', True )
		req.set_flag( 'web:startup_dialog', True )
		req.set_flag( 'web:startup_format', _('Add Project') )
		item_addbtn = umcd.Button( _('Add Project'), 'distribution/projectadd', umcd.Action( req, item_id_list ), attributes = { 'width' : '250' } )
		item_addbtn['colspan']='2'
		if self.permitted('distribution/project/distribute', {} ):
			lstheader.add_row( [ item_addbtn ] )


		lstresult = umcd.List()
		lstresult.set_header( [ _( 'Project' ), _( 'Description' ), _('Sender'), _( '#Users' ), _( '#Files' ) ] )
		for project in cmddata.get('projectlist', []):
			req = umcp.Command( args = [ 'distribution/project/show' ],
								opts =  { 'projectname' : project['name'] } )
			req.set_flag( 'web:startup', True )
			req.set_flag( 'web:startup_reload', True )
			req.set_flag( 'web:startup_dialog', True )
			req.set_flag( 'web:startup_format', _('Collect Project "%(projectname)s"') )

			description = project['description']
			if not description:
				description = _('--- no description ---')
			row = [ umcd.Button( project['name'], 'distribution/project', umcd.Action( req ) ), description, project['sender_uid'], len(project['recipients_dn']), len(project['files']) ]

			lstresult.add_row( row )


		#
		# build layout
		#
		headline = _('Teaching Material Distribution')
		opts = { 'ou': currentOU }
		res.dialog = [ umcd.Frame( [ lstheader ], headline ), umcd.Frame( [ self.__distribution_search_form( opts ) ], _('Search') ) ]

		if umcobject.incomplete:
			self.revamped( umcobject.id(), res )
			return

		res.dialog.append( umcd.Frame( [ lstresult ], _( 'Search results' ) ) )
		self.revamped( umcobject.id(), res )


	def __distribution_status_dialog( self, umcobject, cmddata ):
		if cmddata['cmdexitcode'] == 'success':
			headline = _('Action finished successfully')
		else:
			headline = _('Action failed')
		lst = umcd.List()
		for msg in cmddata.get('msg', []):
			if msg:
				lst.add_row( [ msg ] )

		btn = umcd.CloseButton( attributes = {'class': 'submit'} )
		lst.add_row( [ btn ] )

		return umcd.Frame( [ lst ], headline )


	def _web_distribution_project_distribute( self, umcobject, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_distribution_distribute: options: %s' % str( umcobject.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_distribution_distribute: dialog: %s' % str( res.dialog ) )

		cmddata = res.dialog

		availableOU = cmddata.get('availableOU', [])
		currentOU = umcobject.options.get( 'ou', availableOU[0] )
		userdnlist = umcobject.options.get( 'userdnlist', [] )
		groupdn = umcobject.options.get( 'groupdn', None )
		debugmsg( ud.ADMIN, ud.INFO, 'currentOU: %s' % currentOU )

		if cmddata.get('cmdexitcode', None):
			res.dialog = self.__distribution_status_dialog( umcobject, cmddata )
			self.revamped( umcobject.id(), res )
			return


		#
		# create widgets
		#
		item_id_list = []
		item_ouselect = None

		item_projectname = umcd.make( self[ 'distribution/project/distribute' ][ 'projectname' ], default = umcobject.options.get('projectname','') )
		item_description = umcd.make( self[ 'distribution/project/distribute' ][ 'description' ], default = umcobject.options.get('description','') )
		item_deadline = umcd.make( self[ 'distribution/project/distribute' ][ 'deadline' ], default = umcobject.options.get('deadline','') )
		item_fileupload = umcd.make( self[ 'distribution/project/distribute' ][ 'fileupload' ], maxfiles = 0, default = umcobject.options.get('fileupload') )
		item_fileupload['colspan'] = '2'
		item_id_list.extend( [ item_projectname.id(), item_description.id(), item_deadline.id(), item_fileupload.id() ] )

		# build user selection widget
		item_userlist = umcd.make( self[ 'distribution/project/distribute' ][ 'userdnlist' ], modulename = 'users/user',
								   filter = cmddata.get('userfilter', ''),
								   attr_display = [ 'firstname', ' ', 'lastname', ' (', 'username', ')' ],
								   default = umcobject.options.get('userdnlist',[]),
								   search_disabled = True,
								   basedn = cmddata.get('searchbaseUsers', ''),
#								   search_properties = [ 'firstname', 'lastname', 'username' ]
								   )
		item_userlist['colspan'] = '2'
		item_id_list.append( item_userlist.id() )

		# select group
		default = 0
		choices = []
		for grp in cmddata.get('grouplist', []):
			req = umcp.Command( args = [ 'distribution/project/distribute' ],
								opts = { 'groupdn' : grp['dn'],
										 'ou': currentOU,
										 } )
			choices.append( { 'description': grp['name'], 'actions': [ umcd.Action( req, item_id_list ) ] } )

			if groupdn == grp['dn']:
				default = len(choices)-1

		item_groupselect = umcd.ChoiceButton( _( 'Please select class:' ), choices = choices, default = default, close_dialog = False, attributes = { 'width': '300' } )
		item_id_list.append( item_groupselect.id() )

		# select OU
		if len(availableOU) > 1:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['distribution/project/distribute'],
																			opts = { 'ou' : ou,
																					 } ), item_id_list ) ] } )

			item_ouselect = umcd.ChoiceButton( _('Please select school:'), ouchoices, default = defaultchoice, close_dialog = False, attributes = { 'width': '300' } )


		opts = { 'ou' : currentOU,
				 'complete': '1' }
		req = umcp.Command( args = [ 'distribution/project/distribute' ], opts = opts )
		actions = ( umcd.Action( req, item_id_list ) )
		item_create = umcd.Button( _('Create Project'), 'actions/ok', actions = actions, close_dialog = False, attributes = {'class': 'submit', 'defaultbutton': '1'} )
		item_cancel = umcd.CancelButton()



		#
		# build layout
		#
		res.dialog = []

		if cmddata.get('msg', None):
			lst = umcd.List()
			for msg in cmddata.get('msg', []):
				lst.add_row( [ msg ] )

			res.dialog.append( umcd.Frame( [ umcd.Image('distribution/error'), lst ], _('ERROR') ) )


		headline = _('Create new distribution')
		lst = umcd.List()
		lst.add_row( [ item_projectname, item_description ] )
		lst.add_row( [ item_deadline ] )
		if item_ouselect:
			lst.add_row( [ item_ouselect ] )
		lst.add_row( [ item_groupselect ] )
		lst.add_row( [ item_userlist ] )
		lst.add_row( [ item_fileupload ] )
		lst.add_row( [ item_cancel, item_create ] )

		res.dialog.append( umcd.Frame( [ lst ], headline ) )

		self.revamped( umcobject.id(), res )


	def _web_distribution_project_show( self, umcobject, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_distribution_show: options: %s' % str( umcobject.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_distribution_show: dialog: %s' % str( res.dialog ) )

		cmddata = res.dialog

		if cmddata['project'] == None:
			res.dialog = umcd.Frame( [ 'ERROR' ], 'ERROR' )
			self.revamped( umcobject.id(), res )

		headline = _('Collect Distributed Teaching Material')
		lst = umcd.List()

		lst.add_row( [ _('Projectname:'), [ umcd.Image('distribution/project'), cmddata['project']['name'] ] ] )
		description = cmddata['project']['description']
		if not description:
			description = _('--- no description ---')
		lst.add_row( [ _('Description:'), description ] )
		if cmddata['project']['deadline']:
			deadline = time.strftime( _('%m/%d/%Y at %H:%M'), time.localtime( cmddata['project']['deadline'] ) )
		else:
			deadline = _('no deadline given - please collect data manually')
		lst.add_row( [ _('Deadline:'), deadline ] )
		lst.add_row( [ _('Sender:'), [ umcd.Image('distribution/user'), '%s %s (%s)' % (cmddata['project']['sender']['obj']['firstname'],
																						cmddata['project']['sender']['obj']['lastname'],
																						cmddata['project']['sender']['obj']['username']) ] ] )
		lst.add_row( [ _('Sender Project Dir:'),  cmddata['project']['sender']['projectdir'] ] )
		lstfiles = umcd.List()
		for f in cmddata['project']['files']:
			lstfiles.add_row( [ [ umcd.Image('distribution/file'), f ] ] )
		lst.add_row( [ umcd.Text( _('Files:'), attributes = { 'valign': 'top' }), lstfiles ] )
		if cmddata['project']['recipients']:
			lstrecipients = umcd.List()
			for recipient in cmddata['project']['recipients']:
				lstrecipients.add_row( [ [ umcd.Image('distribution/user'), '%s %s (%s)' % (recipient['obj']['firstname'], recipient['obj']['lastname'], recipient['obj']['username']) ] ] )
			lst.add_row( [ umcd.Text( _('Recipients:'), attributes = { 'valign': 'top' } ), lstrecipients ] )
		else:
			lst.add_row( [ _('Recipients:'), _('no recipients specified') ] )

		opts = { 'projectname' : cmddata['project']['name'] }
		req = umcp.Command( args = [ 'distribution/project/collect' ], opts = opts )
		actions = ( umcd.Action( req ) )
		item_collect = umcd.Button( _('Collect Data'), 'actions/ok', actions = actions, close_dialog = False, attributes = {'class': 'submit'} )
		item_cancel = umcd.CancelButton()
		lst.add_row( [ item_cancel, item_collect ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( umcobject.id(), res )


	def _web_distribution_project_collect( self, umcobject, res ):
		debugmsg( ud.ADMIN, ud.INFO, '_web_distribution_collect: options: %s' % str( umcobject.options ) )
		debugmsg( ud.ADMIN, ud.INFO, '_web_distribution_collect: dialog: %s' % str( res.dialog ) )

		cmddata = res.dialog

		res.dialog = self.__distribution_status_dialog( umcobject, cmddata )
		self.revamped( umcobject.id(), res )
