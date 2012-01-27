#!/usr/bin/python2.4
#
# Univention Management Console
#  helpdesk module: revamp module command result for the specific user interface
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
