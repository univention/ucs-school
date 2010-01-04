#!/usr/bin/python2.4
#
# Univention Management Console
#  module: school groups Module
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
#import univention.admin.uldap

import univention.debug as ud
import univention.config_registry

import notifier
import notifier.popen

import os, re
import smtplib
import codecs
import traceback, sys

import _revamp
import _types

_ = umc.Translation( 'univention.management.console.handlers.school-groups' ).translate

icon = 'school-groups/module'
short_description = _( 'school groupmanager' )
long_description = _( 'Administrate Additional Groups' )
categories = [ 'all' ]

command_description = {
	'schoolgroups/groups/list': umch.command(
		short_description = _( 'List additional groups' ),
		long_description = _( 'List additional groups of one school' ),
		method = 'schoolgroups_groups_list',
		values = { 'key' : _types.searchkey,
				   'filter' : _types.filter,
				   'ou': _types.ou },
		startup = True,
		caching = True,
		priority = 100,
	),
	'schoolgroups/group/edit': umch.command(
		short_description = _( 'Edit group' ),
		long_description = _( 'Edit group' ),
		method = 'schoolgroups_group_edit',
		values = { 'group' : _types.group,
				   'groupdn' : _types.groupdn,
				   'description' : _types.description,
				   'userlist' : _types.userdnlist,
				   'classdn': _types.group,
				   'newgrp': _types.bool,
				   'ou': _types.ou
				   },
		caching = True,
	),
	'schoolgroups/group/add': umch.command(
		short_description = _( 'Add group' ),
		long_description = _( 'Add group' ),
		method = 'schoolgroups_group_edit',
		values = { 'group' : _types.group,
				   'groupdn' : _types.groupdn,
				   'description' : _types.description,
				   'userlist' : _types.userdnlist,
				   'classdn': _types.group,
				   'newgrp': _types.bool,
				   'ou': _types.ou
				   },
		caching = True,
	),
	'schoolgroups/groups/remove': umch.command(
		short_description = _( 'Remove groups' ),
		long_description = _( 'Remove groups' ),
		method = 'schoolgroups_groups_remove',
		values = { 'groupdn' : _types.groupdnlist,
				   'group' : _types.grouplist,
				   'confirmed' : _types.bool,
				   'ou': _types.ou },
	),
	'schoolgroups/group/set': umch.command(
		short_description = _( 'Modify group' ),
		long_description = _( 'Modify members of one additional group' ),
		method = 'schoolgroups_group_set',
		values = { 'group' : _types.group,
				   'groupdn' : _types.groupdn,
				   'description' : _types.description,
				   'userlist' : _types.userdnlist,
				   'ou': _types.ou
				   },
	),
	'schoolgroups/groups/teacher/list': umch.command(
		short_description = _( 'Assign teachers to groups' ),
		long_description = _( 'Assign teachers to groups' ),
		method = 'schoolgroups_groups_teacher_list',
		values = { 'key' : _types.searchkey,
				   'filter' : _types.filter,
				   'ou': _types.ou },
		startup = True,
		caching = True,
		priority = 90,
	),
	'schoolgroups/group/teacher/edit': umch.command(
		short_description = _( 'Assign teachers to specific group' ),
		long_description = _( 'Assign teachers to specific group' ),
		method = 'schoolgroups_group_teacher_edit',
		values = { 'group' : _types.group,
				   'groupdn' : _types.groupdn,
				   'description' : _types.description,
				   'userlist' : _types.userdnlist,
				   'classdn': _types.group,
				   'newgrp': _types.bool,
				   'ou': _types.ou
				   },
		caching = True,
	),
	'schoolgroups/group/teacher/set': umch.command(
		short_description = _( 'Assign teachers to specific group' ),
		long_description = _( 'Assign teachers to specific group' ),
		method = 'schoolgroups_group_teacher_set',
		values = {  'group' : _types.group,
					'groupdn' : _types.groupdn,
					'description' : _types.description,
					'userlist' : _types.userdnlist,
					'ou': _types.ou
					},
	),
	'schoolgroups/groups/unused/list': umch.command(
		short_description = _( 'List unused groups' ),
		long_description = _( 'List unused groups' ),
		method = 'schoolgroups_groups_unused_list',
		values = { 	'ou': _types.ou,
					'membercnt': _types.membercnt,
					},
		startup = True,
		caching = True,
		priority = 90,
	),
	'schoolgroups/groups/unused/remove': umch.command(
		short_description = _( 'Remove unused group' ),
		long_description = _( 'Remove unused group' ),
		method = 'schoolgroups_groups_unused_remove',
		values = {  'group' : _types.group,
					'groupdn' : _types.groupdn,
					'confiremd' : _types.bool,
					'ou': _types.ou,
					},
		caching = True,
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
		self.adminlo = None
		self.dcslavelo = None
		self.ouswitchenabled = False
		self.availableOU = []

	def _switch_ou( self, ou ):
		# FIXME search for OU to get correct dn
		self.searchbaseDepartment = 'ou=%s,%s' % (ou, self.configRegistry[ 'ldap/base' ] )
		self.departmentNumber = ou

		self.searchbaseUsers = "cn=users,%s" % self.searchbaseDepartment
		self.searchbaseExtGroups = "cn=schueler,cn=groups,%s" % self.searchbaseDepartment
		self.searchbaseClasses = "cn=klassen,cn=schueler,cn=groups,%s" % self.searchbaseDepartment
		self.searchbasePupils = "cn=schueler,cn=users,%s" % self.searchbaseDepartment
		self.searchbaseTeachers = "cn=lehrer,cn=users,%s" % self.searchbaseDepartment
		self.searchbaseClassShares = "cn=klassen,cn=shares,%s" % self.searchbaseDepartment
		self.searchbaseShares = "cn=shares,%s" % self.searchbaseDepartment


	def _make_ldap_connection( self, ldapHost = None, hostaccount = False ):
		self.admin = univention.admin
		self.binddn = ''

		if ldapHost == None:
			ldapHost = self.configRegistry[ 'ldap/server/name' ]

		# create authenticated ldap connection
		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: hostname: %s' % ldapHost)
		lo = univention.uldap.access( host = ldapHost, base = self.configRegistry[ 'ldap/base' ], start_tls = 2 )

		if hostaccount:
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: using machine account for ldap connection')
		else:
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: username: %s' % self._username)

		if self._username or hostaccount:
			if hostaccount:
				# try to get machine account password
				try:
					machinesecret = open('/etc/machine.secret','r').read().strip()
				except:
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: cannot read /etc/machine.secret')
					hostaccount = False
				if hostaccount:
					# get ldap connection if password could be read
					binddn = self.configRegistry['ldap/hostdn']
					ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: binddn: %s' % binddn)
					lo = univention.admin.uldap.access( host = ldapHost,
														base = self.configRegistry['ldap/base'],
														binddn = binddn,
														start_tls = 2,
														bindpw = machinesecret )

			# if connection with hostaccount is not required or not possible due to missing password then
			# use normal user account for ldap connection
			if not hostaccount:
				self.binddn = lo.searchDn( filter = 'uid=%s' % self._username )[0]
				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: binddn: %s' % self.binddn)
				#lo.close() #FIXME: how to close the connection?
				self.bindpwd = self._password
				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: config-registry ldap/server/name: %s ldap/base: %s' % ( self.configRegistry['ldap/server/name'], self.configRegistry['ldap/base'] ) )
				lo = univention.admin.uldap.access( host = ldapHost,
													base = self.configRegistry['ldap/base'],
													binddn = self.binddn,
													start_tls = 2,
													bindpw = self.bindpwd )
			self.co = univention.admin.config.config()

			self.departmentNumber = None

			self.usermodule = univention.admin.modules.get('users/user')
			self.groupmodule = univention.admin.modules.get('groups/group')
			self.sharemodule = univention.admin.modules.get('shares/share')
			self.oumodule = univention.admin.modules.get('container/ou')

			self.searchScopeExtGroups = 'one'

			if len(self.availableOU) == 0:
				# OU list override
				oulist = self.configRegistry.get('ucsschool/local/oulist')
				if oulist:
					self.availableOU = [ x.strip() for x in oulist.split(',') ]
					ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: availableOU overridden by UCR' )
				else:
					self.availableOU = []
					# get available OUs
					ouresult = univention.admin.modules.lookup( self.oumodule, self.co, lo,
																scope = 'one', superordinate = None,
																base = self.configRegistry[ 'ldap/base' ] )
					for ou in ouresult:
						self.availableOU.append(ou['name'])

				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: availableOU=%s' % self.availableOU )

				# TODO FIXME HARDCODED HACK for SFB
				# set departmentNumber and available OU to hardcoded defaults
				if '438' in self.availableOU:
					self.departmentNumber = '438'
					self._switch_ou(self.departmentNumber)
				else:
					self._switch_ou(self.availableOU[0])

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
				ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: was not able to identify ou of this account - OU select box enabled!' )
				self.ouswitchenabled = True

		else:
			ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: no username given, further actions may fail!' )
			lo = None

		return lo


	def _generate_grouplist ( self, object, asdict = False ):
		grouplist = []

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not asdict:
			grouplist.append( _( 'No group selected' ) )

		groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.lo,
						 scope = 'sub', superordinate = None,
						 base = self.searchbaseClasses, filter = None)
		for gr in groupresult:
			if not asdict:
				grouplist.append( gr['name'] )
			else:
				oldinfo = gr.oldinfo
				oldinfo['dn'] = gr.dn
				grouplist.append( oldinfo )

		if not asdict:
			grouplist = sorted( grouplist )
		else:
			grouplist = sorted( grouplist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
								key = lambda x: x[ 'name' ] )
		return grouplist

	def _generate_grouplist_with_info ( self, object, filter = None, scope = 'one', base = None ):
		if base == None:
			base = self.searchbaseExtGroups

		grouplist = []

		if not self.lo:
			self.lo = self._make_ldap_connection()

		try:
			groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.lo,
														   scope = scope, superordinate = None,
														   base = base, filter = filter)
			for gr in groupresult:
				grouplist.append( { 'name': gr['name'],
									   'description': gr.oldinfo.get('description',''),
									   'dn': gr.dn
									   }
									 )
			grouplist = sorted( grouplist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
								   key = lambda x: x[ 'name' ] )
		except Exception, e:
			ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: gen_grouplist_with_info: lookup failed: %s' % e )

		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: gen_grouplist_with_info: extended groups = %s' % grouplist )
		return grouplist



	def _get_group_member_list( self, object, groupdn, filterbase = None ):
		memberlist = []

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not groupdn:
			return memberlist

		try:
			groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.lo,
														   scope = 'sub', superordinate = None,
														   base = groupdn, filter = '')
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: group(%s) = %s' % (groupdn, groupresult) )
			for gr in groupresult:
				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: group(%s) gr=%s' % (groupdn, gr) )
				gr.open()
				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: group(%s) gr["users"]=%s' % (groupdn, gr['users']) )
				for memberdn in gr['users']:
					if filterbase == None or memberdn.endswith(filterbase):
						memberlist.append( memberdn )
		except Exception, e:
			ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: get_group_member_list: lookup failed: %s' % e )

		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: group(%s) memberlist=%s' % (groupdn, memberlist) )
		return memberlist


	def _verify_group_share(self, groupname, groupdn):

		position_dn='cn=%s,%s' % (groupname, self.searchbaseShares)

		# look if share exists, else create it
		share_exists = 0
		type=position_dn[0:position_dn.find("=")]
		name=position_dn[position_dn.find("=")+1:position_dn.find(",")]
		position=position_dn[position_dn.find(",")+1:]
		objects = None

		if not self.adminlo:
			self.adminlo = self._make_ldap_connection( self.configRegistry['ldap/master'] )

		try:
			objects = univention.admin.modules.lookup(self.sharemodule, self.co, self.adminlo, scope='sub', superordinate=None, base=position,
													  filter=univention.admin.filter.expression(type,name))
		except:
			ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: exist_lookup: position=%s  filter="%s=%s"' % (position, type, name) )
			pass
		if objects:
			for object in objects:
				if codecs.latin_1_encode(univention.admin.objects.dn(object))[0].lower() == position_dn.lower():
					share_exists = 1
					ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: groupshare %s already exists' % position_dn )
		if not share_exists:
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: need to create groupshare %s' % position_dn )

			# get gid form corresponding group
			gid = 0
			try:
				groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.adminlo,
															   scope = 'sub', superordinate = None,
															   base = groupdn, filter = '')
				if groupresult and groupresult[0]:
					gr = groupresult[0]
					gr.open()
					gid = gr['gidNumber']
			except Exception, e:
				ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: getting group id failed (group=%s): %s' % (groupdn, e) )
				lines = traceback.format_exc().replace('%','#')
				ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while getting group id! Please consult local administrator.')

			ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: verify_group_share: using gid=%s' % gid)

			# set default server
			serverfqdn = "%s.%s" % (self.configRegistry.get('hostname'), self.configRegistry.get('domainname'))

			# get alternative server (defined at ou object if a dc slave is responsible for more than one ou)
			ou_dn = "ou=%s,%s" % (self.departmentNumber, self.configRegistry['ldap/base'])
			ou_attr_LDAPAccessWrite = self.adminlo.get(ou_dn,['univentionLDAPAccessWrite'])
			alternativeServer_dn = None
			if len(ou_attr_LDAPAccessWrite) > 0:
				alternativeServer_dn = ou_attr_LDAPAccessWrite["univentionLDAPAccessWrite"][0]
				if len(ou_attr_LDAPAccessWrite) > 1:
					ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: more than one corresponding univentionLDAPAccessWrite found at ou=%s' % self.departmentNumber )

			# build fqdn of alternative server and set serverfqdn
			if alternativeServer_dn:
				alternativeServer_attr = self.adminlo.get(alternativeServer_dn,['uid'])
				if len(alternativeServer_attr) > 0:
					alternativeServer_uid = alternativeServer_attr['uid'][0]
					alternativeServer_uid = alternativeServer_uid.replace('$','')
					if len(alternativeServer_uid) > 0:
						serverfqdn = "%s.%s" % (alternativeServer_uid, self.configRegistry['domainname'])


			position=univention.admin.uldap.position(self.configRegistry['ldap/base'])
			position.setDn(position_dn[position_dn.find(",")+1:])
			object = self.sharemodule.object(self.co, self.adminlo, position, superordinate=None)
			object.open()
			object["name"] = "%s" % groupname
			object["host"] = serverfqdn
			object["path"] = "/home/groups/%s" % groupname
			object["writeable"] = "1"
			object["sambaWriteable"] = "1"
			object["sambaBrowseable"] = "1"
			object["sambaForceGroup"] = "+%s" % groupname
			object["sambaCreateMode"] = "0770"
			object["sambaDirectoryMode"] = "0770"
			object["owner"]="0"
			object["group"]=gid
			object["directorymode"]="0770"

			try:
				dn=object.create()
			except univention.admin.uexceptions.objectExists:
				ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: verify_group_share: object exists')
			except Exception, e:
				ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: verify_group_share: creating object failed (dn=%s): %s' % (position_dn, e) )
				lines = traceback.format_exc().replace('%','#')
				ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )



	def schoolgroups_groups_list( self, object ):
		filter = object.options.get( 'filter', '*' )
		key = object.options.get( 'key', 'name' )

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not self.lo: # if still no LDAP-connection available
			ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: school_groups_list: NO LDAP')
			self.finished( object.id(), None,
						   report = _( 'No Connection to the LDAP-Database available, please try again later' ),
						   success = False )
			return

		if '438' in self.availableOU:
			self._switch_ou( '438' )
		else:
			if object.options.get('ou',None):
				self._switch_ou( object.options.get('ou') )

		groups = self._generate_grouplist_with_info( object, '%s=%s' % (key, filter), scope=self.searchScopeExtGroups, base=self.searchbaseExtGroups )

		self.finished( object.id(), ( self.availableOU, self.departmentNumber, filter, key, groups ) )


	def schoolgroups_group_edit( self, object ):
		self.adminlo = None
		if not self.adminlo:
			self.adminlo = self._make_ldap_connection( self.configRegistry['ldap/master'] )

		if not self.adminlo: # if still no LDAP-connection available
			self.finished( object.id(), None,
						   report = _( 'No Connection to the LDAP-Database available, please try again later' ),
						   success = False )
			return

		if object.options.get('ou',None):
			self._switch_ou( object.options.get('ou') )

		groupdn = object.options.get( 'groupdn', None )

		description = object.options.get( 'description', None )
		if description == None and groupdn:
			try:
				groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.adminlo,
															   scope = 'sub', superordinate = None,
															   base = groupdn, filter = '')
				if groupresult and groupresult[0]:
					gr = groupresult[0]
					gr.open()
					description = gr['description']
			except Exception, e:
				ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: getting group description failed (group=%s): %s' % (groupdn, e) )
				lines = traceback.format_exc().replace('%','#')
				ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while getting group description! Please consult local administrator.')
		else:
			description = None

		userlist = object.options.get( 'userlist', None )
		if userlist == None and groupdn:
			userlist = self._get_group_member_list( object, groupdn, filterbase=self.searchbasePupils )
		else:
			userlist = None
		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: userlist=%s' % userlist)

		classlist = self._generate_grouplist( object, asdict = True )

		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: classlist=%s' % classlist)

		classmemberfilter = ''
		classdn = object.options.get( 'classdn', None )
		if not classdn in ['::all', '::allsearch' ]:
			classmember = self._get_group_member_list( object, classdn, filterbase=self.searchbasePupils )

			if classmember:
				classmemberfilter = '(|'
				for member in classmember:
					classmemberfilter += '(uid=' + self.adminlo.explodeDn( member, 1 )[0] + ')'
				classmemberfilter += ')'

			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: classmember=%s' % classmember)
		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: classmemberfilter=%s' % classmemberfilter)

		if self.configRegistry.get('umc/schooladmin/groups/regex'):
			regex = self.configRegistry['umc/schooladmin/groups/regex']
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: group.regex (PRE) = %s' % regex)

			# TODO FIXME HARDCODED HACK for SFB
			# set departmentNumber and available OU to hardcoded defaults
			if '438' in self.availableOU:
				regex = regex % { 'departmentNumber': '438' }
			else:
				regex = regex % { 'departmentNumber': self.departmentNumber }

			try:
				_types.group.regex = re.compile(regex)
			except:
				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: invalid regexp - exception caught: %s' % regex)
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: group.regex (POST) = %s' % regex)

		groupdefault = None
		if self.configRegistry.has_key('umc/schooladmin/groups/defaultgroupprefix') and self.configRegistry['umc/schooladmin/groups/defaultgroupprefix']:
			groupdefault = self.configRegistry['umc/schooladmin/groups/defaultgroupprefix']
			groupdefault = groupdefault % { 'departmentNumber': self.departmentNumber }
			ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: groupdefault = %s' % groupdefault)

		self.finished( object.id(), ( self.availableOU, self.searchbasePupils, description, userlist, classlist, classmemberfilter, groupdefault ) )

	def schoolgroups_group_set( self, object ):
		self.adminlo = None
		if not self.adminlo:
			self.adminlo = self._make_ldap_connection( self.configRegistry['ldap/master'] )

		if not self.adminlo: # if still no LDAP-connection available
			self.finished( object.id(), None,
						   report = _( 'No Connection to the LDAP-Database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set departmentNumber and available OU to hardcoded defaults
		if '438' in self.availableOU:
			self.departmentNumber = '438'
			self._switch_ou(self.departmentNumber)
		else:
			if object.options.get('ou',None):
				self._switch_ou( object.options.get('ou') )

		groupdn = object.options.get( 'groupdn', None )
		group = object.options.get( 'group', None )
		userlist = object.options.get( 'userlist', None )
		description = object.options.get( 'description', None )

		report = ''

		if userlist == None:
			ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: cannot change group members: userlist == None')
			self.finished( object.id(), None, success = False, report = _( 'Cannot change group members') )
			return

		if groupdn:
			# change group object
			report = ''

			# get teacher members of specified group
			userlist_teachers = self._get_group_member_list( object, groupdn, filterbase=self.searchbaseTeachers )
			# add teacher members to selected pupils
			userlist.extend(userlist_teachers)

			try:
				groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.adminlo,
															   scope = 'sub', superordinate = None,
															   base = groupdn, filter = '')
				if groupresult and groupresult[0]:
					gr = groupresult[0]
					gr.open()
					gr['description'] = description
					gr['users'] = userlist
					dn = gr.modify()
			except Exception, e:
				ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: change of group members failed (group=%s): %s' % (groupdn, e) )
				lines = traceback.format_exc().replace('%','#')
				ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while modifying group! Please consult local administrator.')
		else:
			# no groupdn present ==> create new group

			tmpPosition = univention.admin.uldap.position(self.configRegistry['ldap/base'])
			tmpPosition.setDn(self.searchbaseExtGroups)

			try:
				groupObject=self.groupmodule.object(self.co, self.adminlo, position=tmpPosition)
				groupObject.open()
				groupObject.options = [ 'posix' ]
				groupObject['name'] = group
				groupObject['description'] = description
				groupObject['users'] = userlist
				dn = groupObject.create()

			except univention.admin.uexceptions.objectExists:
				ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: creating group %s failed: objectExists' % group )
				report = _('Cannot create group - object already exists!')
			except univention.admin.uexceptions.permissionDenied:
				ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: creating group %s failed: permissionDenied' % group )
				report = _('Cannot create group - permission denied!')
			except univention.admin.uexceptions.groupNameAlreadyUsed:
				ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: creating group %s failed: groupNameAlreadyUsed' % group )
				report = _('Cannot create group - groupname already used!')
			except Exception, e:
				ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: creating group %s at %s failed: %s' % (group, tmpPosition.getDn(), e) )
				lines = traceback.format_exc().replace('%','#')
				ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while creating group! Please consult local administrator.')

			self._verify_group_share( group, 'cn=%s,%s' % (group, self.searchbaseExtGroups) )

		self.finished( object.id(), None, report = report, success = (len(report)==0) )


	def schoolgroups_groups_teacher_list( self, object ):
		"""
		create list of all groups teachers can join to (classes and additional groups)
		"""
		filter = object.options.get( 'filter', '*' )
		key = object.options.get( 'key', 'name' )

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not self.lo: # if still no LDAP-connection available
			ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: school_groups_list: NO LDAP')
			self.finished( object.id(), None,
						   report = _( 'No Connection to the LDAP-Database available, please try again later' ),
						   success = False )
			return

		if '438' in self.availableOU:
			self._switch_ou( '438' )
		else:
			if object.options.get('ou',None):
				self._switch_ou( object.options.get('ou') )

		groups = self._generate_grouplist_with_info( object, '%s=%s' % (key, filter), scope='sub', base=self.searchbaseExtGroups )

		self.finished( object.id(), ( self.availableOU, self.departmentNumber, filter, key, groups ) )



	def schoolgroups_group_teacher_edit( self, object ):
		"""
		add/remove teachers to/from group selected group
		"""
		ud.debug( ud.ADMIN, ud.INFO, 'schoolgroups_groups_teacher_edit: options: %s' % str( object.options ) )

		if not self.dcslavelo:
			self.dcslavelo = self._make_ldap_connection( self.configRegistry['ldap/master'], hostaccount = True )

		if not self.dcslavelo: # if still no LDAP-connection available
			self.finished( object.id(), None,
						   report = _( 'No Connection to the LDAP-Database available, please try again later' ),
						   success = False )
			return

		if object.options.get('ou',None):
			self._switch_ou( object.options.get('ou') )

		groupdn = object.options.get( 'groupdn', None )

		description = object.options.get( 'description', None )
		if description == None and groupdn:
			try:
				groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.dcslavelo,
															   scope = 'sub', superordinate = None,
															   base = groupdn, filter = '')
				if groupresult and groupresult[0]:
					gr = groupresult[0]
					gr.open()
					description = gr['description']
			except Exception, e:
				ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: getting group description failed (group=%s): %s' % (groupdn, e) )
				lines = traceback.format_exc().replace('%','#')
				ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while getting group description! Please consult local administrator.')
		else:
			description = None

		userlist = object.options.get( 'userlist', None )
		if userlist == None and groupdn:
			userlist = self._get_group_member_list( object, groupdn, filterbase=self.searchbaseTeachers )
		else:
			userlist = None
		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: userlist=%s' % userlist)

		self.finished( object.id(), ( self.availableOU, self.searchbaseTeachers, description, userlist ) )


	def schoolgroups_group_teacher_set( self, object ):
		if not self.dcslavelo:
			self.dcslavelo = self._make_ldap_connection( self.configRegistry['ldap/master'], hostaccount = True )

		if not self.dcslavelo: # if still no LDAP-connection available
			self.finished( object.id(), None,
						   report = _( 'No Connection to the LDAP-Database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set departmentNumber and available OU to hardcoded defaults
		if '438' in self.availableOU:
			self.departmentNumber = '438'
			self._switch_ou(self.departmentNumber)
		else:
			if object.options.get('ou',None):
				self._switch_ou( object.options.get('ou') )

		groupdn = object.options.get( 'groupdn', None )
		group = object.options.get( 'group', None )
		userlist = object.options.get( 'userlist', None )
		description = object.options.get( 'description', None )

		report = ''

		if userlist == None:
			ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: cannot change group members: userlist == None')
			self.finished( object.id(), None, success = False, report = _( 'Cannot change group members') )
			return

		if groupdn:
			# get pupil members of specified group
			userlist_pupils = self._get_group_member_list( object, groupdn, filterbase=self.searchbasePupils )
			# add pupil members to selected teachers
			userlist.extend(userlist_pupils)

			# change group object
			report = ''
			try:
				groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.dcslavelo,
															   scope = 'sub', superordinate = None,
															   base = groupdn, filter = '')
				if groupresult and groupresult[0]:
					gr = groupresult[0]
					gr.open()
					gr['description'] = description
					gr['users'] = userlist
					dn = gr.modify()
			except Exception, e:
				ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: change of group members failed (group=%s): %s' % (groupdn, e) )
				lines = traceback.format_exc().replace('%','#')
				ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				report = _('An error occured while modifying group! Please consult local administrator.')
		else:
			# no groupdn present ==> error
			ud.debug( ud.ADMIN, ud.WARN, 'SCHOOLGROUPS: no groupdn present' )
			report = _('An error occured while modifying group! Please consult local administrator.')

		self.finished( object.id(), None, report = report, success = (len(report)==0) )


	def schoolgroups_groups_remove( self, object ):
		self.adminlo = None
		if not self.adminlo:
			self.adminlo = self._make_ldap_connection( self.configRegistry['ldap/master'] )

		if not self.adminlo: # if still no LDAP-connection available
			self.finished( object.id(), None,
						   report = _( 'No Connection to the LDAP-Database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set departmentNumber and available OU to hardcoded defaults
		if '438' in self.availableOU:
			self.departmentNumber = '438'
			self._switch_ou(self.departmentNumber)
		else:
			if object.options.get('ou',None):
				self._switch_ou( object.options.get('ou') )

		groupdnlist = object.options.get( 'groupdn', [] )
		confirmed = object.options.get( 'confirmed', False )

		message = []

		if confirmed:
			for dn in groupdnlist:
				sharedn = 'cn=%s,%s' % (self.adminlo.explodeDn( dn, 1 )[0], self.searchbaseShares)
				try:
					tmpPosition = univention.admin.uldap.position(self.searchbaseShares)
					obj = univention.admin.objects.get( self.sharemodule, self.co, self.adminlo, tmpPosition, dn = sharedn )
					obj.open()
					obj.remove()
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: removed %s' % sharedn )
				except Exception, e:
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: removal of share %s failed: %s' % (sharedn, e) )
					message.append( sharedn )
					lines = traceback.format_exc().replace('%','#')
					ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK:\n%s' % lines )

				try:
					tmpPosition = univention.admin.uldap.position(self.searchbaseExtGroups)
					obj = univention.admin.objects.get( self.groupmodule, self.co, self.adminlo, tmpPosition, dn = dn )
					obj.open()
					obj.remove()
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: removed %s' % dn )
				except Exception, e:
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: removal of group %s failed: %s' % (dn, e) )
					message.append( dn )
					lines = traceback.format_exc().replace('%','#')
					ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK:\n%s' % lines )

		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: confirmed=%s  grplist=%s' % (confirmed, groupdnlist))

		self.finished( object.id(), (self.availableOU, len(message)==0, message) )


	def schoolgroups_groups_unused_list( self, umcobj ):
		"""
		list unused groups
		"""
		ud.debug( ud.ADMIN, ud.INFO, 'schoolgroups_groups_unused_list: options: %s' % str( umcobj.options ) )

		if not self.lo:
			self.lo = self._make_ldap_connection()

		if not self.lo: # if still no LDAP-connection available
			self.finished( 	umcobj.id(), None,
							report = _( 'No Connection to the LDAP-Database available, please try again later' ),
							success = False )
			return

		if umcobj.options.get('ou', None):
			self._switch_ou( umcobj.options.get('ou') )

		try:
			membercnt = int( umcobj.options.get( 'membercnt', 0 ) )
		except:
			membercnt = 0

		if membercnt > 5:
			membercnt = 5

		umcobj.options['membercnt'] = str(membercnt)

		empty_groups = []
		groupresult = []
		try:
			groupresult = univention.admin.modules.lookup( 	self.groupmodule, self.co, self.lo,
															scope = 'sub', superordinate = None,
															base = self.searchbaseExtGroups, filter = '')
			for grp in groupresult:
				grp.open()
				grpdict = { 'dn': grp.dn,
							'name': grp['name'],
							'description': grp['description'],
							'listteachers': [],
							'listpupils': [],
							}

				for usrdn in grp['users']:
					uid = self.lo.explodeDn( usrdn, 1 )[0]
					if '.' in uid:
						grpdict[ 'listteachers' ].append( [ uid, usrdn ] )
					else:
						grpdict[ 'listpupils' ].append( [ uid, usrdn ] )

				if len( grpdict['listpupils'] ) <= membercnt:
					empty_groups.append( grpdict )

		except Exception, e:
			ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: searching groups failed (membercnt=%s): %s' % (membercnt, e) )
			lines = traceback.format_exc().replace('%','#')
			ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
			self.finished( 	umcobj.id(), [ [], [] ] ,
							report = _( 'An error occured while searching for unused groups. Please try again later or contact local administrator.' ),
							success = False )
			return

		empty_groups.sort(lambda x,y: cmp(x['name'], y['name']))

		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: empty_groups=%s' % (empty_groups))

		self.finished( umcobj.id(), (self.availableOU, empty_groups) )


	def schoolgroups_groups_unused_remove( self, umcobj ):
		"""
		remove unused groups if user confirmed removal
		"""
		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: schoolgroups_groups_unused_remove: options: %s' % str( umcobj.options ) )

		if not self.dcslavelo:
			self.dcslavelo = self._make_ldap_connection( self.configRegistry['ldap/master'], hostaccount = True )

		if not self.dcslavelo: # if still no LDAP-connection available
			self.finished( 	umcobj.id(), None,
							report = _( 'No Connection to the LDAP-Database available, please try again later' ),
							success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set departmentNumber and available OU to hardcoded defaults
		if '438' in self.availableOU:
			self.departmentNumber = '438'
			self._switch_ou(self.departmentNumber)
		else:
			if umcobj.options.get('ou',None):
				self._switch_ou( umcobj.options.get('ou') )

		grouplist = umcobj.options.get( 'group', [] )
		groupdnlist = umcobj.options.get( 'groupdn', [] )
		confirmed = umcobj.options.get( 'confirmed', False )

		message = []

		if confirmed:
			for dn in groupdnlist:
				# get group object specified by "dn"
				try:
					groupresult = univention.admin.modules.lookup( 	self.groupmodule, self.co, self.dcslavelo,
																	scope = 'sub', superordinate = None,
																	base = dn, filter = '')
				except univention.admin.uexceptions.noObject:
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: remove unused: find group %s failed: noObject' % dn )
					message.append( _('- noObject: %s') % dn )
					continue
				except Exception, e:
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: remove unused: find group %s failed: %s' % (dn, e) )
					try:
						message.append( '- %s: %s' % (str(e.__class__), dn) )
					except:
						message.append( '- %s: %s' % (str(e), dn) )
					lines = traceback.format_exc().replace('%','#')
					ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK:\n%s' % lines )
					continue

				if len(groupresult) != 1:
					continue

				grp = groupresult[0]
				grp.open()
				nopupils = True
				# check if group contains pupils
				for usrdn in grp['users']:
					uid = self.lo.explodeDn( usrdn, 1 )[0]
					if not '.' in uid:
						nopupils = False
						break

				if not nopupils:
					message.append( _('- contains pupils: %s') % dn )
					continue

				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: grpdn: %s' % dn )

				if dn.endswith(self.searchbaseClasses):
					sharedn = 'cn=%s,%s' % (self.dcslavelo.explodeDn( dn, 1 )[0], self.searchbaseClassShares)
					posShare = self.searchbaseClassShares
					posGrp = self.searchbaseClasses
				else:
					sharedn = 'cn=%s,%s' % (self.dcslavelo.explodeDn( dn, 1 )[0], self.searchbaseShares)
					posShare = self.searchbaseShares
					posGrp = self.searchbaseExtGroups

				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: sharedn: %s' % sharedn )
				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: posShare: %s' % posShare )
				ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: posGrp: %s' % posGrp )

				try:
					tmpPosition = univention.admin.uldap.position(posShare)
					obj = univention.admin.objects.get( self.sharemodule, self.co, self.dcslavelo, tmpPosition, dn = sharedn )
					obj.open()
					obj.remove()
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: remove unused: removed %s' % sharedn )
				except Exception, e:
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: remove unused: removal of share %s failed: %s' % (sharedn, e) )
					try:
						message.append( '- %s: %s' % (str(e.__class__), sharedn) )
					except:
						message.append( '- %s: %s' % (str(e), sharedn) )
					lines = traceback.format_exc().replace('%','#')
					ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK:\n%s' % lines )

				try:
					tmpPosition = univention.admin.uldap.position(posGrp)
					obj = univention.admin.objects.get( self.groupmodule, self.co, self.dcslavelo, tmpPosition, dn = dn )
					obj.open()
					obj.remove()
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: remove unused: removed %s' % dn )
				except Exception, e:
					ud.debug( ud.ADMIN, ud.ERROR, 'SCHOOLGROUPS: remove unused: removal of group %s failed: %s' % (dn, e) )
					try:
						message.append( '- %s: %s' % (str(e.__class__), dn) )
					except:
						message.append( '- %s: %s' % (str(e), dn) )
					lines = traceback.format_exc().replace('%','#')
					ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK:\n%s' % lines )

		ud.debug( ud.ADMIN, ud.INFO, 'SCHOOLGROUPS: remove unused: confirmed=%s  grplist=%s' % (confirmed, groupdnlist))

		self.finished( umcobj.id(), [ self.availableOU, len(message)==0, message ] )
