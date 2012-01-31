#!/usr/bin/python2.6
#
# Univention Management Console
#  module: Helpdesk Module
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

from univention.management.console.modules import Base

from univention.management.console.log import MODULE
from univention.management.console.config import ucr

from univention.lib.i18n import Translation

from ucsschool.lib import SchoolLDAPConnection

import notifier
import notifier.popen

import os, re
import smtplib

_ = Translation( 'ucs-school-umc-helpdesk' ).translate

class Instance( Base ):
	def init( self ):
		MODULE.error( 'init module' )
		## inititate an LDAP connection to the local directory
		self.ldap_anon = SchoolLDAPConnection( binddn = self._user_dn, bindpw = self._password, username = self._username )

	def configuration( self, request ):
		MODULE.error( 'return configuration' )
		username = _( 'unknown' )
		if self._username:
			username = self._username
		department = _( 'unknown' )

		# use first available OU
		if self.ldap_anon.availableOU:
			department = self.ldap_anon.availableOU[ 0 ]

		# use username
		if self._user_dn:
			regex = re.compile(',ou=([^,]+),')
			match = regex.match( self._user_dn )
			if match:
				department = match.groups()[ 0 ]

		# override department by UCR variable ucsschool/helpdesk/fixedou if variable is set
		val = ucr.get( 'ucsschool/helpdesk/fixedou' )
		if val:
			department = val

		MODULE.info( 'username=%s  department=%s' % ( self._username, department ) )

		self.finished( request.id, {
			'username' : self._username,
			'department' : department,
			'recipient' : ucr.has_key( 'ucsschool/helpdesk/recipient' ) and ucr[ 'ucsschool/helpdesk/recipient' ] } )


	def send( self, request ):
		def _send_thread( sender, recipients, username, department, category, message ):
			MODULE.info( 'sending mail: thread running' )

			msg = u'From: ' + sender + u'\r\n'
			msg += u'To: ' + (', '.join(recipients)) + u'\r\n'
			msg += u'Subject: %s (%s: %s)\r\n' % (category, _('Department'), department)
			msg += u'\r\n'
			msg += u'%s: %s\r\n' % ( _( 'Sender' ), username )
			msg += u'%s: %s\r\n' % ( _( 'Department' ), department )
			msg += u'%s: %s\r\n' % ( _( 'Category' ), category )
			msg += u'%s:\r\n' % _( 'Message' )
			msg += message + u'\r\n'
			msg += u'\r\n'

			msg = msg.encode('latin1')

			server = smtplib.SMTP('localhost')
			server.set_debuglevel(0)
			server.sendmail(sender, recipients, msg)
			server.quit()

		def _send_return( thread, result, request ):
			import traceback

			if not isinstance( result, BaseException ):
				MODULE.info( 'sending mail: completed successfully' )
				self.finished( request.id, True )
			else:
				msg = '%s\n%s: %s\n' % ( ''.join( traceback.format_tb( thread.exc_info[ 2 ] ) ), thread.exc_info[ 0 ].__name__, str( thread.exc_info[ 1 ] ) )
				MODULE.process( 'sending mail:An internal error occurred: %s' % msg )
				self.finished( request.id, False, msg, False )


		keys = [ 'username', 'department', 'category', 'message' ]
		self.required_options( request, *keys )
		for key in keys:
			if request.options[ key ]:
				MODULE.info( 'send ' + key + '=' + request.options[ key ].replace('%','_') )

		if ucr.has_key( 'ucsschool/helpdesk/recipient' ) and ucr[ 'ucsschool/helpdesk/recipient' ]:
			if ucr.has_key( 'hostname' ) and ucr[ 'hostname' ] and ucr.has_key( 'domainname' ) and ucr[ 'domainname' ]:
				sender = 'ucsschool-helpdesk@%s.%s' % ( ucr[ 'hostname' ], ucr[ 'domainname' ] )
			else:
				sender = 'ucsschool-helpdesk@localhost'

			func = notifier.Callback( _send_thread,
									  sender,	ucr[ 'ucsschool/helpdesk/recipient' ].split( ' ' ),
									  request.options[ 'username' ], request.options[ 'department' ],
									  request.options[ 'category' ], request.options[ 'message' ] )
			MODULE.info( 'sending mail: starting thread' )
			cb = notifier.Callback( _send_return, request )
			thread = notifier.threads.Simple( 'HelpdeskMessage', func, cb )
			thread.run()
		else:
			MODULE.error( 'HELPDESK: cannot send mail - config-registry variable "ucsschool/helpdesk/recipient" is not set' )
			self.finished( request.id, False, _( 'The email address for the helpdesk team is not configured.' ) )

	def categories( self, request ):
		categories = []
		lo = self.ldap_anon.getConnection()
		res = lo.searchDn( filter = 'objectClass=univentionUMCHelpdeskClass' )
		# use only first object found
		if res and res[ 0 ]:
			categories = lo.getAttr( res[ 0 ], 'univentionUMCHelpdeskCategory' )

		self.finished( request.id, map( lambda x: { 'id' : x, 'label' : x }, categories ) )
