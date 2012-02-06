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
from univention.management.console.modules import UMC_CommandError

import univention.admin.modules as udm_modules
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
		self.required_options( request, 'school', 'class', 'pattern' )

		klass = request.options.get( 'class' )
		if klass in ( None, 'None' ):
			klass = None
		result = self._users( ldap_user_read, search_base, group = klass, user_type = request.flavor, pattern = request.options.get( 'pattern', '' ) )
		self.finished( request.id, map( lambda usr: { 'id' : usr.dn, 'name' : Display.user( usr ), 'passwordexpiry' : ucr[ 'passwordexpiry' ] }, result ) )

	def _reset_passwords( self, userlist, newPassword, lo, pwdChangeNextLogin = True ):
		'''helper function for resetting passwords of one or many accounts'''
		MODULE.info( 'schoolaccounts_reset_passwords: pwdChangeNextLogin=%s' % pwdChangeNextLogin )

		messages = []
		failedlist = []

		for ur in userlist:
			try:
				ur.open()
				ur['password'] = newPassword
				ur['overridePWHistory'] = '1'
				dn = ur.modify()

				ur.open()
				ur['locked'] = 'none'
				dn = ur.modify()

				ur = univention.admin.objects.get(self.usermodule, None, lo, None, dn)
				ur.open()
				if pwdChangeNextLogin:
					ur['pwdChangeNextLogin'] = '1'
				else:
					ur['pwdChangeNextLogin'] = '0'
				dn = ur.modify()

				messages.append( _('%s: password has been reset successfully') % (ur['username']))
			except univention.admin.uexceptions.permissionDenied, e:
				MODULE.process( '_reset_passwords: dn=%s' % ur.dn)
				MODULE.process( '_reset_passwords: exception=%s' % str(e.__class__))
				messages.append( _('password reset failed for user %(user)s (permission denied)') % { 'user': ur['username'] })
				failedlist.append(ur)
			except univention.admin.uexceptions.base, e:
				MODULE.process( '_reset_passwords: dn=%s' % ur.dn)
				MODULE.process( '_reset_passwords: exception=%s' % str(e.__class__))
				messages.append( _('password reset failed for user %(user)s (%(exception)s)') % { 'user': ur['username'], 'exception': str(e.__class__)})
				failedlist.append(ur)
			except Exception, e:
				MODULE.process( '_reset_passwords: dn=%s' % ur.dn)
				MODULE.process( '_reset_passwords: exception=%s' % str(e.__class__))
				messages.append( _('password reset failed for user %(user)s (%(exception)s)') % { 'user': ur['username'], 'exception': str(e.__class__)})
				failedlist.append(ur)

		return (failedlist, messages)

	@LDAP_Connection( USER_READ, USER_WRITE )
	def password_reset( self, request, ldap_user_read = None, ldap_user_write = None, ldap_base = None, search_base = None ):
		'''reset passwords of selected users'''
		self.required_options( request, 'userDN', 'newPassword' )

		if request.options.has_key( 'reallyChangePasswords' ):
			if request.options[ 'reallyChangePasswords' ]:
				if request.options.has_key( 'newPassword' ) and request.options[ 'newPassword' ]:
					failedlist, messages = self._reset_passwords( userlist, request.options[ 'newPassword' ], lo, pwdChangeNextLogin = request.options.get( 'pwdChangeNextLogin' ) )
					success = len(failedlist) == 0
					userlist = failedlist
					request.options[ 'userdns' ] = []
					for ur in userlist:
						request.options[ 'userdns' ].append( ur.dn )
				else:
					messages = [ _('No passwords changed, need a new password.') ]
			else:
				messages = [ _('No passwords changed.') ]

		MODULE.info( 'schoolaccounts_user_passwd, finish: %s, %s, %s' % ( userlist, success, messages ))
		self.finished( request.id, ( self.availableOU, userlist, success, messages ) )

	def _search_accounts ( self, request ):
		accountlist = []
		searchkey = request.options.get('key',None)
		searchfilter = request.options.get('filter',None)

		if searchkey and searchfilter:
			accountresult = univention.admin.modules.lookup( self.usermodule, self.co, self.lo,
															 scope = 'sub', superordinate = None,
															 base = self.searchbasePupils, filter = '%s=%s' % (searchkey, searchfilter))
			MODULE.info( 'SCHOOLACCOUNTS: search accounts with %s=%s' % (searchkey,searchfilter) )

			for ar in accountresult:
				ar.open()
				accountlist.append( ar )

		sortmap = { 'uid': 'username',
					'sn': 'lastname',
					'givenName': 'firstname' }
		if searchkey in sortmap:
			sortkey = sortmap[ searchkey ]
		else:
			sortkey = 'firstname'

		accountlist = sorted( accountlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
							  key = lambda x: x[ sortkey ] )

		return accountlist

	def schoolaccounts_pupil_search ( self, request, messages = [] ):
		'''Search pupils by username, first name or last name'''
		MODULE.info( 'schoolaccounts_class_search: options=%s' % request.options)

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not self.lo: # if still no LDAP-connection available
			self.finished( request.id, None,
				       report = _( 'No Connection to the LDAP-Database available, please try again later' ),
				       success = False )
			return

		if request.options.get('ou',None):
			MODULE.info( 'schoolaccounts_class_show: switching OU=%s' % request.options.get('ou'))
			self._switch_ou( request.options.get('ou') )

		accountlist = self._search_accounts( request )

		self.finished( request.id, ( self.availableOU, accountlist, messages ) )
