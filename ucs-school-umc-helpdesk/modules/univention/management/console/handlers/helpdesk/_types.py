#!/usr/bin/python2.4
#
# Univention Management Console
#  module: manages a CUPS server
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

_ = umc.Translation( 'univention.management.console.handlers.helpdesk' ).translate

class HelpdeskCategory( umc.StaticSelection ):
	def __init__( self, required = True, choices = [] ):
		self.helpdesk_choices = []

		# generate config objects
		self.configRegistry = univention.config_registry.ConfigRegistry()
		self.configRegistry.load()

		try:
			self.lo = univention.uldap.access( host = self.configRegistry[ 'ldap/server/name' ], base = self.configRegistry[ 'ldap/base' ], start_tls = 2 )
			ud.debug( ud.ADMIN, ud.INFO, 'HELPDESK-TYPES: got ldap connection' )
		except:
			self.lo = None
			ud.debug( ud.ADMIN, ud.ERROR, 'HELPDESK: unable to get ldap connection' )

		try:
			res = self.lo.searchDn( filter = 'objectClass=univentionUMCHelpdeskClass' )
			# use only first object found
			if res and res[0]:
				categories = self.lo.getAttr(res[0], 'univentionUMCHelpdeskCategory')
				for category in categories:
					self.helpdesk_choices.append( category )
			ud.debug( ud.ADMIN, ud.INFO, 'HELPDESK: categories=%s' % str(self.helpdesk_choices) )
		except:
			pass

		if len(self.helpdesk_choices) == 0:
			self.helpdesk_choices = [ _( 'unable to get categories' ) ]

		umc.StaticSelection.__init__( self, _( 'Category' ), required = required )

	def choices( self ):
		choices = []

		# build list of categories
		for cat_name in self.helpdesk_choices:
			choices.append( ( cat_name, cat_name ) )

		return choices

umcd.copy( umc.StaticSelection, HelpdeskCategory )


user = umc.String( _( 'User' ) )
department = umc.String( _( 'Department' ) )
category = HelpdeskCategory()
message = umc.Text( _( 'Message' ) )
