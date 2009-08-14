#!/usr/bin/python2.4
#
# Univention Management Console
#  module: school accounts Module
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
import univention.admin.modules
import univention.admin.objects
import univention.admin.uldap

import univention.debug as ud
import univention.config_registry

import notifier
import notifier.popen

import os, re
import smtplib

import _revamp
import _types

_ = umc.Translation( 'univention.management.console.handlers.school-accounts' ).translate

icon = 'school-accounts/module'
short_description = _( 'school usermanager' )
long_description = _( 'Administrate Pupils and Teachers' )
categories = [ 'all' ]

command_description = {
	'schoolaccounts/class/show': umch.command(
		short_description = _( 'Display pupils of one class.' ),
		long_description = _( 'Display pupils of one class.' ),
		method = 'schoolaccounts_class_show',
		values = { 'ou': _types.ou,
	           'class' : _types.group,
			   'username' : _types.user,
			   },
		startup = True,
		caching = True,
		priority = 100
	),
	'schoolaccounts/pupil/search': umch.command(
		short_description = _( 'Search pupils' ),
		long_description = _( 'Search pupils' ),
		method = 'schoolaccounts_pupil_search',
		values = { 'ou': _types.ou,
	           'key' : _types.searchkeys,
			   'filter' : _types.searchfilter,
			   },
		startup = True,
		caching = True,
		priority = 90
	),
	'schoolaccounts/teacher/show': umch.command(
		short_description = _( 'Display teachers of one school' ),
		long_description = _( 'Display teachers of one school' ),
		method = 'schoolaccounts_teacher_show',
		values = { 'ou': _types.ou,
			   'class' : _types.group,
			   'username' : _types.user,
			   },
		startup = True,
		caching = True,
		priority = 80
	),
	'schoolaccounts/user/passwd': umch.command(
		short_description = _( 'Reset password for users.' ),
		long_description = _( 'Reset password for users' ),
		method = 'schoolaccounts_user_passwd',
		values = { 'ou': _types.ou,
				   'newPassword' : umc.String( _( 'new password' ), required = True ),
				   'pwdChangeNextLogin': umc.Boolean( _('User has to change password at next login') ),
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
		self.lo = None
		self.ouswitchenabled = False
		self.availableOU = []

	def _switch_ou( self, ou ):
		self.searchbaseDepartment = 'ou=%s,%s' % (ou, self.configRegistry[ 'ldap/base' ] )
		self.departmentNumber = ou

		self.searchbaseClasses = "cn=klassen,cn=schueler,cn=groups,%s" % self.searchbaseDepartment
		self.searchbaseGroups = "cn=schueler,cn=groups,%s" % self.searchbaseDepartment
		self.searchbasePupils = "cn=schueler,cn=users,%s" % self.searchbaseDepartment
		self.searchbaseTeachers = "cn=lehrer,cn=users,%s" % self.searchbaseDepartment


	def _make_ldap_connection( self, ldapHost = None ):
		self.admin = univention.admin
		self.binddn = ''

		if ldapHost == None:
			ldapHost = self.configRegistry[ 'ldap/server/name' ]

		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: hostname: %s' % ldapHost)
		lo = univention.uldap.access( host = ldapHost, base = self.configRegistry[ 'ldap/base' ], start_tls = 2 )
		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: username: %s' % self._username)
		if self._username:
			self.binddn = lo.searchDn( filter = 'uid=%s' % self._username )[0]
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: binddn: %s' % self.binddn)
			#lo.close() #FIXME: how to close the connection?
			self.bindpwd = self._password
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: config-registry ldap/server/name: %s ldap/base: %s' % ( self.configRegistry['ldap/server/name'], self.configRegistry['ldap/base'] ) )
			lo = univention.admin.uldap.access( host = ldapHost,
								 base = self.configRegistry['ldap/base'],
								 binddn = self.binddn,
								 start_tls = 2,
								 bindpw = self.bindpwd )
			self.co = univention.admin.config.config()

			self.usermodule = univention.admin.modules.get('users/user')
			self.groupmodule = univention.admin.modules.get('groups/group')
			self.oumodule = univention.admin.modules.get('container/ou')

			if len(self.availableOU) == 0:
				# OU list override
				oulist = self.configRegistry.get('ucsschool/local/oulist')
				if oulist:
					self.availableOU = [ x.strip() for x in oulist.split(',') ]
					ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: availableOU overridden by UCR' )
				else:
					self.availableOU = []
					# get available OUs
					ouresult = univention.admin.modules.lookup( self.oumodule, self.co, self.lo,
																scope = 'one', superordinate = None,
																base = self.configRegistry[ 'ldap/base' ] )
					for ou in ouresult:
						self.availableOU.append(ou['name'])

				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: availableOU=%s' % self.availableOU )

				# TODO FIXME HARDCODED HACK for SFB
				# set departmentNumber and available OU to hardcoded defaults
				if '438' in self.availableOU:
					self.departmentNumber = '438'
					self._switch_ou(self.departmentNumber)
				else:
					self._switch_ou(hostou)

			if self.binddn.find('ou=') > 0:
				self.searchbaseDepartment = self.binddn[self.binddn.find('ou='):]
				self.departmentNumber = lo.explodeDn( self.searchbaseDepartment, 1 )[0]

				# TODO FIXME HARDCODED HACK for SFB
				# set departmentNumber and available OU to hardcoded defaults
				if '438' in self.availableOU:
					self.departmentNumber = '438'
				else:
					# cut list down to default OU
					self.availableOU = [ self.departmentNumber ]

				self._switch_ou(self.departmentNumber)

			else:
				ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLACCOUNTS: was not able to identify ou of this account - OU select box enabled!' )
				self.ouswitchenabled = True

		else:
			ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLACCOUNTS: no username given, further actions may fail!' )
			lo = None

		return lo

	def _get_selected_group ( self, object ):
		selectedgroup = None
		if object.options.has_key( 'selectedgroup' ) and object.options[ 'selectedgroup' ]:
			selectedgroup = object.options[ 'selectedgroup' ]

		return selectedgroup

	def _generate_grouplist ( self, object ):
		grouplist = []

		ud.debug( ud.ADMIN, ud.INFO, '_generate_grouplist: %s' % self.searchbaseGroups )

		groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.lo,
						 scope = 'sub', superordinate = None,
						 base = self.searchbaseGroups, filter = None)
		for gr in groupresult:
			grouplist.append( gr['name'] )

		grouplist = sorted( grouplist )
		grouplist.insert( 0, _( 'No group selected' ) )

		return grouplist

	def _generate_userlist( self, userdns, lo = None ):
		if lo == None:
			lo = self.lo

		userlist = []
		for userdn in userdns:
			ud.debug( ud.ADMIN, ud.INFO, 'schoolaccounts_generate_userlist: get user %s' % userdn )
			ur = univention.admin.objects.get(self.usermodule, None, lo, None, userdn)
			userlist.append( ur )

		userlist = sorted( userlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
						   key = lambda x: x[ 'username' ] )

		return userlist

	def _generate_accountlist ( self, object, filterbase = None ):
		accountlist = []
		selectedgroup = self._get_selected_group( object )
		if selectedgroup and selectedgroup != _( 'No group selected' ):
			accountresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.lo,
									 scope = 'sub', superordinate = None,
									 base = self.searchbaseGroups, filter = 'cn=%s' % selectedgroup)
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: list accounts from groups %s' % str( accountresult ) )

			for ar in accountresult:
				ar.open()
				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: got users %s' % ar['users'] )
				userlist = ar['users']
				if filterbase:
					userlist = [ dn for dn in userlist if dn.endswith(filterbase) ]
				accountlist += self._generate_userlist( userlist )

		accountlist = sorted( accountlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
							  key = lambda x: x[ 'username' ] )

		return accountlist

	def _generate_teacherlist ( self, object ):
		teacherlist = []
		accountresult = univention.admin.modules.lookup( self.usermodule, self.co, self.lo,
								 scope = 'sub', superordinate = None,
								 base = self.searchbaseTeachers, filter = '' )
		for ar in accountresult:
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: got teacher %s' % ar.dn )
			teacherlist.append( ar )

		teacherlist = sorted( teacherlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
							  key = lambda x: x[ 'username' ] )

		return teacherlist

	def schoolaccounts_class_show ( self, object, messages = [] ):
		'''Show pupils selectable by class (group)'''
		ud.debug( ud.ADMIN, ud.INFO, 'schoolaccounts_class_show: options=%s' % object.options)

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not self.lo: # if still no LDAP-connection available
			self.finished( object.id(), None,
				       report = _( 'No Connection to the LDAP-Database available, please try again later' ),
				       success = False )
			return

		if object.options.get('ou',None):
			self._switch_ou( object.options.get('ou') )

		selectedgroup = self._get_selected_group ( object )
		grouplist = self._generate_grouplist ( object )
		accountlist = self._generate_accountlist ( object, self.searchbasePupils )

		self.finished( object.id(), ( self.availableOU, grouplist, accountlist, selectedgroup, messages ) )

	def schoolaccounts_teacher_show ( self, object, messages = [] ):
		'''Show teachers selected by LDAP-position'''
		ud.debug( ud.ADMIN, ud.INFO, 'schoolaccounts_teacher_show: options=%s' % object.options)

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not self.lo: # if still no LDAP-connection available
			self.finished( object.id(), None,
				       report = _( 'No Connection to the LDAP-Database available, please try again later' ),
				       success = False )
			return

		if object.options.get('ou',None):
			self._switch_ou( object.options.get('ou') )

		teacherlist = self._generate_teacherlist ( object )
		self.finished( object.id(), ( self.availableOU, teacherlist, messages ) )

	def _reset_passwords( self, userlist, newPassword, lo, pwdChangeNextLogin = True ):
		'''helper function for resetting passwords of one or many accounts'''
		ud.debug( ud.ADMIN, ud.INFO, 'schoolaccounts_reset_passwords: pwdChangeNextLogin=%s' % pwdChangeNextLogin )

		messages = []
		failedlist = []

		for ur in userlist:
			try:
				ur.open()
				ur['password'] = newPassword
				ur['overridePWHistory'] = '1'
				dn = ur.modify()

				ur.open()
				ur['locked'] = '0'
				dn = ur.modify()

				ur = univention.admin.objects.get(self.usermodule, None, lo, None, dn)
				ur.open()
				if pwdChangeNextLogin:
					ur['pwdChangeNextLogin'] = '1'
				else:
					ur['pwdChangeNextLogin'] = '0'
				dn = ur.modify()

				messages.append( _('%s: password has been reset successfully') % (ur['username']))
			except univention.admin.uexceptions.base, e:
				ud.debug( ud.ADMIN, ud.ERROR, '_reset_passwords: dn=%s' % ur.dn)
				ud.debug( ud.ADMIN, ud.ERROR, '_reset_passwords: exception=%s' % str(e.__class__))
				messages.append( _('password reset failed for user %(user)s (%(exception)s)') % { 'user': ur['username'], 'exception': str(e.__class__)})
				failedlist.append(ur)
			except Exception, e:
				ud.debug( ud.ADMIN, ud.ERROR, '_reset_passwords: dn=%s' % ur.dn)
				ud.debug( ud.ADMIN, ud.ERROR, '_reset_passwords: exception=%s' % str(e.__class__))
				messages.append( _('password reset failed for user %(user)s (%(exception)s)') % { 'user': ur['username'], 'exception': str(e.__class__)})
				failedlist.append(ur)

		return (failedlist, messages)

	def schoolaccounts_user_passwd ( self, object ):
		'''reset passwords of selected users'''
		ud.debug( ud.ADMIN, ud.INFO, 'schoolaccounts_user_passwd, options: %s' % object.options)

		# WARNING: workaround!
		# use new ldap connection to master if user passwords shall be reset
		# (python-ldap cannot handle referrals correctly)
		lo = self.lo
		if object.options.has_key( 'reallyChangePasswords' ):
			if object.options[ 'reallyChangePasswords' ]:
				if object.options.has_key( 'newPassword' ) and object.options[ 'newPassword' ]:
					lo = self._make_ldap_connection( self.configRegistry['ldap/master'] )

		if object.options.get('ou',None):
			self._switch_ou( object.options.get('ou') )

		userlist = []
		if object.options.has_key( 'userdns' ):
			userlist = self._generate_userlist( object.options[ 'userdns' ], lo )

		success = False
		messages = []
		if object.options.has_key( 'reallyChangePasswords' ):
			if object.options[ 'reallyChangePasswords' ]:
				if object.options.has_key( 'newPassword' ) and object.options[ 'newPassword' ]:
					failedlist, messages = self._reset_passwords( userlist, object.options[ 'newPassword' ], lo, pwdChangeNextLogin = object.options.get( 'pwdChangeNextLogin' ) )
					success = len(failedlist) == 0
					userlist = failedlist
					object.options[ 'userdns' ] = []
					for ur in userlist:
						object.options[ 'userdns' ].append( ur.dn )
				else:
					messages = [ _('No passwords changed, need a new password.') ]
			else:
				messages = [ _('No passwords changed.') ]

		ud.debug( ud.ADMIN, ud.INFO, 'schoolaccounts_user_passwd, finish: %s, %s, %s' % ( userlist, success, messages ))
		self.finished( object.id(), ( self.availableOU, userlist, success, messages ) )

	def _search_accounts ( self, object ):
		accountlist = []
		searchkey = object.options.get('key',None)
		searchfilter = object.options.get('filter',None)

		if searchkey and searchfilter:
			accountresult = univention.admin.modules.lookup( self.usermodule, self.co, self.lo,
															 scope = 'sub', superordinate = None,
															 base = self.searchbasePupils, filter = '%s=%s' % (searchkey, searchfilter))
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLACCOUNTS: search accounts with %s=%s' % (searchkey,searchfilter) )

			for ar in accountresult:
				ar.open()
				accountlist.append( ar )

		sortmap = { 'uid': 'username',
					'sn': 'lastname',
					'givenName': 'firstname' }
		if searchkey in sortmap:
			sortkey = sortmap[ searchkey ]
		else:
			sortkey = 'username'

		accountlist = sorted( accountlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
							  key = lambda x: x[ sortkey ] )

		return accountlist

	def schoolaccounts_pupil_search ( self, object, messages = [] ):
		'''Search pupils by username, first name or last name'''
		ud.debug( ud.ADMIN, ud.INFO, 'schoolaccounts_class_search: options=%s' % object.options)

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not self.lo: # if still no LDAP-connection available
			self.finished( object.id(), None,
				       report = _( 'No Connection to the LDAP-Database available, please try again later' ),
				       success = False )
			return

		if object.options.get('ou',None):
			ud.debug( ud.ADMIN, ud.INFO, 'schoolaccounts_class_show: switching OU=%s' % object.options.get('ou'))
			self._switch_ou( object.options.get('ou') )

		accountlist = self._search_accounts( object )

		self.finished( object.id(), ( self.availableOU, accountlist, messages ) )
