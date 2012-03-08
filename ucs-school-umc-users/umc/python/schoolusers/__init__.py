#!/usr/bin/python2.6
#
# Univention Management Console
#  module: school accounts Module
#
# Copyright 2007-2012 Univention GmbH
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

from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules import UMC_CommandError, UMC_OptionTypeError

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions
import univention.admin.objects as udm_objects
import univention.admin.uldap as udm_uldap

from univention.lib.i18n import Translation

from ucsschool.lib import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, Display, USER_READ, USER_WRITE

import notifier
import notifier.popen

_ = Translation( 'ucs-school-umc-schoolusers' ).translate

class Instance( SchoolBaseModule ):
	@LDAP_Connection()
	def query( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Searches for students

		requests.options = {}
		  'school' -- school OU (optiona)
		  'class' -- if not  set to 'all' the print jobs of the given class are listed only
		  'pattern' -- search pattern that must match the name or username of the students

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		self.required_options( request, 'class', 'pattern' )

		klass = request.options.get( 'class' )
		if klass in ( None, 'None' ):
			klass = None
		result = self._users( ldap_user_read, search_base, group = klass, user_type = request.flavor, pattern = request.options.get( 'pattern', '' ) )
		self.finished( request.id, map( lambda usr: { 'id' : usr.dn, 'name' : Display.user( usr ), 'passwordexpiry' : usr.get( 'passwordexpiry', '' ) }, result ) )

	def _reset_passwords( self, userdn, newPassword, lo, pwdChangeNextLogin = True ):
		'''helper function for resetting passwords of one or many accounts'''

		try:
			user_module = udm_modules.get( 'users/user' )
			ur = udm_objects.get( user_module, None, lo, None, userdn )
			ur.open()
			ur[ 'password' ] = newPassword
			ur[ 'overridePWHistory' ] = '1'
			dn = ur.modify()

			ur.open()
			ur['locked'] = 'none'
			dn = ur.modify()

			ur = udm_objects.get( user_module, None, lo, None, dn )
			ur.open()
			if pwdChangeNextLogin:
				ur[ 'pwdChangeNextLogin' ] = '1'
			else:
				ur[ 'pwdChangeNextLogin' ] = '0'
			dn = ur.modify()
			return True
		except udm_exceptions.permissionDenied, e:
			MODULE.process( '_reset_passwords: dn=%s' % ur.dn )
			MODULE.process( '_reset_passwords: exception=%s' % str( e.__class__ ) )
			return _( 'Failed to reset password (permission denied)' )
		except udm_exceptions.base, e:
			MODULE.process( '_reset_passwords: dn=%s' % ur.dn )
			MODULE.process( '_reset_passwords: exception=%s' % str( e.__class__ ) )
			return _( 'Failed to reset password (exception: %s)' ) % str( e.__class__ )
		except Exception, e:
			MODULE.process( '_reset_passwords: dn=%s' % ur.dn )
			MODULE.process( '_reset_passwords: exception=%s' % str( e.__class__ ) )
			return _( 'Failed to reset password (unknown error: %s)' ) % str( e )

	@LDAP_Connection( USER_READ, USER_WRITE )
	def password_reset( self, request, ldap_user_read = None, ldap_user_write = None, ldap_position = None, search_base = None ):
		'''reset passwords of selected users'''
		self.required_options( request, 'userDN', 'newPassword' )

		if request.options.get( 'newPassword' ):
			result = self._reset_passwords( request.options[ 'userDN' ], request.options[ 'newPassword' ], ldap_user_write, pwdChangeNextLogin = request.options.get( 'nextLogin', True ) )
		else:
			raise UMC_OptionTypeError( _( 'No passwords changed, need a new password.') )

		self.finished( request.id, result )
