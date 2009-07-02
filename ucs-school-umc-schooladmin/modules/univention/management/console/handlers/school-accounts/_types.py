#!/usr/bin/python2.4
#
# Univention Management Console
#  school accounts module: manages passwords for pupils and teachers
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

import univention.management.console as umc
import univention.management.console.dialog as umcd
import univention.debug as ud
import univention.config_registry
import univention.uldap

_ = umc.Translation( 'univention.management.console.handlers.school-accounts' ).translate

class SchoolAccounts_SearchKeys( umc.StaticSelection ):
	def __init__( self, required = True ):
		umc.StaticSelection.__init__( self, unicode( _( 'Search Key' ) ), required = required )

	def choices( self ):
		return ( ( 'uid', _( 'Username' ) ),
				 ( 'givenName', _( 'First Name' ) ),
				 ( 'sn', _( 'Last Name' ) ),
				 )

umcd.copy( umc.StaticSelection, SchoolAccounts_SearchKeys )

ou = umc.String( _( 'Department' ) )
user = umc.String( _( 'User' ) )
group = umc.String( _( 'Group' ) )
searchkeys = SchoolAccounts_SearchKeys()
searchfilter = umc.String( '&nbsp;' , required = False )
