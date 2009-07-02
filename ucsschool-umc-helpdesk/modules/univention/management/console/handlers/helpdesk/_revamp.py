#!/usr/bin/python2.4
#
# Univention Management Console
#  helpdesk module: revamp module command result for the specific user interface
#
# Copyright (C) 2007 Univention GmbH
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

_ = umc.Translation( 'univention.management.console.handlers.helpdesk' ).translate

class Web( object ):
	def _web_helpdesk_form_show( self, object, res ):
		username, department = res.dialog

		headline = _( "Send message to helpdesk" )

		lst = umcd.List()
		user = umcd.make_readonly( self[ 'helpdesk/form/send' ][ 'username' ], default = username )
		lst.add_row( [ user ] )
		items = [ user.id() ]

		department = umcd.make_readonly( self[ 'helpdesk/form/send' ][ 'department' ], default = department )
		lst.add_row( [ department ] )
		items.append( department.id() )

		category = umcd.make( self[ 'helpdesk/form/send' ][ 'category' ] )
		lst.add_row( [ category ] )
		items.append( category.id() )

		message = umcd.make( self[ 'helpdesk/form/send' ][ 'message' ], default = '' )
		lst.add_row( [ message ] )
		items.append( message.id() )


		req = umcp.Command( args = [ 'helpdesk/form/send' ], opts = { } )
		req_show = umcp.Command( args = [ 'helpdesk/form/show' ], opts = { } )

		actions = ( umcd.Action( req, items ), umcd.Action( req_show, items ) )
		button = umcd.Button( _( 'Send' ), 'actions/ok', actions )
		lst.add_row( [ button ] )

		res.dialog = umcd.Frame( [ lst ], headline )

		self.revamped( object.id(), res )
