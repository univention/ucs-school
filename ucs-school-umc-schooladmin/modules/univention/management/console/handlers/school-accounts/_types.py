#!/usr/bin/python2.4
#
# Univention Management Console
#  school accounts module: manages passwords for pupils and teachers
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
