#!/usr/bin/python2.4
#
# Univention Management Console
#  module: Helpdesk Module
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

import univention.management.console as umc
import univention.management.console.categories as umcc
import univention.management.console.protocol as umcp
import univention.management.console.handlers as umch
import univention.management.console.dialog as umcd
import univention.management.console.tools as umct

import univention.debug as ud
import univention.config_registry

import notifier
import notifier.popen

import os, re
import smtplib

import _revamp
import _types
import _schoolldap

_ = umc.Translation( 'univention.management.console.handlers.helpdesk' ).translate

icon = 'helpdesk/module'
short_description = _( 'Helpdesk' )
long_description = _( 'Contact Helpdesk' )
categories = [ 'all' ]

command_description = {
	'helpdesk/form/show': umch.command(
		short_description = _( 'Display helpdesk mail formular' ),
		long_description = _( 'Display helpdesk mail formular' ),
		method = 'helpdesk_form_show',
		values = { 'username' : _types.user,
				   'department' : _types.department,
				   'category' : _types.category,
				   'message' : _types.message,
				   },
		startup = True,
		priority = 100
	),
	'helpdesk/form/send': umch.command(
		short_description = _( 'Send helpdesk mail formular' ),
		long_description = _( 'Send helpdesk mail formular' ),
		method = 'helpdesk_form_send',
		values = { 'username' : _types.user,
				   'department' : _types.department,
				   'category' : _types.category,
				   'message' : _types.message,
				   },
	),
}

class handler( umch.simpleHandler, _revamp.Web  ):
	def __init__( self ):
		global command_description
		umch.simpleHandler.__init__( self, command_description )
		_revamp.Web.__init__( self )

		# generate config objects
		self.configRegistry = univention.config_registry.ConfigRegistry()
		self.configRegistry.load()

		## inititate an anonymous LDAP connection to the local directory
		self.ldap_anon = _schoolldap.SchoolLDAPConnection()


	def helpdesk_form_show( self, object ):
		username = _( 'unknown' )
		if self._username:
			username = self._username
		department = _( 'unknown' )

		# use first available OU
		if self.ldap_anon.availableOU:
			department = self.ldap_anon.availableOU[0]

		# use username
		if username:
			regex = re.compile(',ou=([^,]+),')
			match = regex.match(username)
			if match:
				department = match.groups()[0]

		# override department by UCR variable ucsschool/helpdesk/fixedou if variable is set
		val = self.configRegistry.get( 'ucsschool/helpdesk/fixedou' )
		if val:
			department = val

		ud.debug( ud.ADMIN, ud.INFO, 'HELPDESK: username=%s  department=%s' % (username, department) )

		self.finished( object.id(), ( username, department ) )


	def helpdesk_form_send( self, object ):
		ud.debug( ud.ADMIN, ud.INFO, 'HELPDESK: helpdesk_form_send' )

		for key in ['username', 'department', 'category', 'message' ]:
			if object.options.has_key( key ) and object.options[ key ]:
				ud.debug( ud.ADMIN, ud.INFO, 'HELPDESK: helpdesk_form_send ' + key + '=' + object.options[ key ].replace('%','_') )

		if self.configRegistry.has_key('ucsschool/helpdesk/recipient') and self.configRegistry['ucsschool/helpdesk/recipient']:
			if self.configRegistry.has_key('hostname') and self.configRegistry['hostname'] and \
			   self.configRegistry.has_key('domainname') and self.configRegistry['domainname']:
				sender = 'ucsschool-helpdesk@%s.%s' % (self.configRegistry['hostname'], self.configRegistry['domainname'])
			else:
				sender = 'ucsschool-helpdesk@localhost'

			func = notifier.Callback( self._helpdesk_form_send_thread,
										sender,
										self.configRegistry['ucsschool/helpdesk/recipient'].split(' '),
										object.options[ 'username' ],
										object.options[ 'department' ],
										object.options[ 'category' ],
										object.options[ 'message' ] )
			ud.debug( ud.ADMIN, ud.INFO, 'HELPDESK: sending mail: starting thread' )
			cb = notifier.Callback( self._helpdesk_form_send_return, object )
			thread = notifier.threads.Simple( 'HelpdeskMessage', func, cb )
			thread.run()
		else:
			ud.debug( ud.ADMIN, ud.ERROR, 'HELPDESK: cannot send mail - config-registry variable "ucsschool/helpdesk/recipient" is not set' )
			self.finished( object.id(), None )


	def _helpdesk_form_send_thread( self, sender, recipients, username, department, category, message ):
		ud.debug( ud.ADMIN, ud.INFO, 'HELPDESK: sending mail: thread running' )

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


	def _helpdesk_form_send_return( self, thread, result, object ):
		ud.debug( ud.ADMIN, ud.INFO, 'HELPDESK: sending mail: complete' )
		self.finished( object.id(), None )

