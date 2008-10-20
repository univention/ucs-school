#!/usr/bin/python2.4
#
# Univention Management Console
#  module: Helpdesk Module
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
import univention.management.console.categories as umcc
import univention.management.console.protocol as umcp
import univention.management.console.handlers as umch
import univention.management.console.dialog as umcd
import univention.management.console.tools as umct
import univention.admin.modules
import univention.admin.objects

import univention.debug as ud
import univention.config_registry
import univention.uldap

import notifier
import notifier.popen

import univention.config_registry

import os, re, fnmatch

import _revamp
import _types
import _schoolldap

_ = umc.Translation( 'univention.management.console.handlers.roomadmin' ).translate

icon = 'roomadmin/module'
short_description = _( 'Room Admin' )
long_description = _( 'Computer Room Administration' )
categories = [ 'all' ]

command_description = {
	'roomadmin/room/search': umch.command(
		short_description = _( 'Administrate rooms' ),
		long_description = _( 'Administrate rooms' ),
		method = 'roomadmin_room_search',
		values = { 'key' : _types.searchkey,
				   'filter' : _types.sfilter,
				   'ou': _types.ou
				   },
		startup = True,
		priority = 90
	),
	'roomadmin/room/add': umch.command(
		short_description = _( 'add room' ),
		long_description = _( 'add room' ),
		method = 'roomadmin_room_add',
		values = {  'ou': _types.ou
					},
		priority = 80
	),
	'roomadmin/room/edit': umch.command(
		short_description = _( 'edit room' ),
		long_description = _( 'edit room' ),
		method = 'roomadmin_room_edit',
		values = {  'room': _types.room,
					'roomdn': _types.roomdn,
					'description': _types.description,
					'roommembers': _types.hostdnlist,
					'ou': _types.ou,
					},
		priority = 80
	),
	'roomadmin/room/set': umch.command(
		short_description = _( 'set room' ),
		long_description = _( 'set room' ),
		method = 'roomadmin_room_set',
		values = {  'room': _types.room,
					'roomdn': _types.roomdn,
					'description': _types.description,
					'roommembers': _types.hostdnlist,
					'ou': _types.ou,
					},
		priority = 80
	),
	'roomadmin/room/remove': umch.command(
		short_description = _( 'remove room' ),
		long_description = _( 'remove room' ),
		method = 'roomadmin_room_remove',
		values = {  'room': _types.room,
					'roomdn': _types.roomdn,
					'ou': _types.ou
					},
		priority = 80
	),

	'roomadmin/room/list': umch.command(
		short_description = _( 'List rooms and associated computers' ),
		long_description = _( 'List rooms and associated computers' ),
		method = 'roomadmin_room_list',
		values = { 'room' : _types.room	},
		startup = True,
		priority = 100
	),
	'roomadmin/set/access/internet/enable': umch.command(
		short_description = _( 'Enable internet access' ),
		long_description = _( 'Enable access to internet for selected computers' ),
		method = 'roomadmin_set_access_internet_enable',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
	'roomadmin/set/access/internet/disable': umch.command(
		short_description = _( 'Disable internet access' ),
		long_description = _( 'Disable access to internet for selected computers' ),
		method = 'roomadmin_set_access_internet_disable',
		values = { 'ipaddrs': _types.ipaddrs },
		priority = 90
	),
}

import inspect
def debugmsg( component, level, msg ):
	info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
	printInfo=[]
	if len(info[0])>20:
		printInfo.append('...'+info[0][-17:])
	else:
		printInfo.append(info[0])
	printInfo.extend(info[1:3])
	ud.debug(component, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))


class handler( umch.simpleHandler, _revamp.Web  ):
	def __init__( self ):
		global command_description
		umch.simpleHandler.__init__( self, command_description )
		_revamp.Web.__init__( self )

		# generate config objects
		self.configRegistry = univention.config_registry.ConfigRegistry()
		self.configRegistry.load()

		self.ldap_anon = _schoolldap.SchoolLDAPConnection()
		self.ldap_master = _schoolldap.SchoolLDAPConnection( ldapserver = self.configRegistry['ldap/master'] )

		debugmsg( ud.ADMIN, ud.INFO, 'availableOU=%s' % self.ldap_anon.availableOU )



	def _get_groups_and_computers( self, basedn_computers, basedn_groups ):
		"""
		returns ( groupdict, computerdict )

		groupdict[grpdn] = [ grpattrs, memberlist ]
		grpattrs = { 'attr': [ 'val1', 'val2' ], ... }
		memberlist = [ 'dn1', 'dn2', ... ]

		computerdict[ compdn ] = compattr
		compattr = { 'attr': [ 'val1', 'val2' ], ... }
		"""
		groupdict = {}
		computerdict = {}
		computer2grp = {}
		computerflag = {}

		if self.ldap_anon.checkConnection():
			computers = self.ldap_anon.lo.search( filter='objectClass=univentionHost', base=basedn_computers,
										scope='sub', attr=[ 'cn', 'aRecord', 'objectClass', 'univentionServerRole' ] )
			# iterate over all computer objects
			for compdn, compattr in computers:
				# create dict dn ==> ( attributes, used_flag )
				computerdict[ compdn ] = compattr
				computerflag[ compdn ] = 0

			debugmsg( ud.ADMIN, ud.INFO, 'got %d computer objects' % len(computerdict) )
#			debugmsg( ud.ADMIN, ud.INFO, 'computer objects = %s' % computerdict )

			debugmsg( ud.ADMIN, ud.INFO, 'basedn_groups=%s' % basedn_groups )
			try:
				groups = self.ldap_anon.lo.search( filter='objectClass=univentionGroup', base=basedn_groups,
												   scope='sub', attr=[ 'cn', 'uniqueMember', 'description' ] )
			except Exception, e:
				debugmsg( ud.ADMIN, ud.ERROR, 'getting rooms failed: %s' % str(e) )
				import traceback, sys
				info = sys.exc_info()
				lines = traceback.format_exception(*info)
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % ''.join(lines) )
				report = _('An error occured while getting rooms! Please consult local administrator.')
				groups = []

			debugmsg( ud.ADMIN, ud.INFO, 'groups=%s' % groups )
			# iterate over all groups
			for grpdn, grpattrs in groups:
				memberlist = []
				if grpattrs.has_key('uniqueMember'):

					# check all uniqueMembers
					for memberdn in grpattrs['uniqueMember']:
						# is uniqueMember a computer?
						if memberdn in computerdict:
							# mark computer entry as used
							computerflag[memberdn] = 1
							memberlist.append(memberdn)
				groupdict[grpdn] = [ grpattrs, memberlist ]

			debugmsg( ud.ADMIN, ud.INFO, 'got %d group objects' % len(groupdict) )
#			debugmsg( ud.ADMIN, ud.INFO, 'group objects = %s' % groupdict )

		return (groupdict, computerdict)


	def roomadmin_room_list( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadm	in_room_list: options=%s' % object.options )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		groupdict = {}
		computerdict = {}

		for ou in self.ldap_anon.availableOU:
			self.ldap_anon.switch_ou(ou)
			(tmpgroupdict, tmpcomputerdict) = self._get_groups_and_computers( self.ldap_anon.searchbaseComputers, self.ldap_anon.searchbaseRooms )
			groupdict.update(tmpgroupdict)
			computerdict.update(tmpcomputerdict)

		# get all ip addresses blocked for internet access
		computers_blocked4internet = []

		umc.registry.load()
		keylist = umc.registry.keys()
		for key in keylist:
			if key.startswith('proxy/filter/hostgroup/blacklisted/'):
				value = umc.registry[ key ]

				computers_blocked4internet.extend( value.split(' ') )

		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_list: computers_blocked4internet=%s' % computers_blocked4internet )


		cmd = '/usr/bin/smbstatus -b'
		proc = notifier.popen.Shell( cmd, stdout = True )
		cb = notifier.Callback( self._roomadmin_room_list_return, object, computers_blocked4internet, groupdict, computerdict )
		proc.signal_connect( 'finished', cb )
		proc.start()

#root@master30:/root# smbstatus -b
#
#Samba version 3.0.23d
#PID     Username      Group         Machine                        
#-------------------------------------------------------------------
#23355   schueler312   Account Operators  007bondpc    (10.200.18.100)


	def _roomadmin_room_list_return( self, pid, status, buffer, object, computers_blocked4internet, groupdict, computerdict ):
		host2user = {}
		user2realname = {}
		userlist = []
		regex = re.compile( '^\s*?(?P<pid>[0-9]+)\s\s+(?P<username>[^ ]+)\s\s+(?P<group>.+)\s\s+(?P<host>[^ ]+)\s\s+\((?P<ipaddr>[.0-9]+)\)\s*$' )

#		debugmsg( ud.ADMIN, ud.INFO, 'smbstatus -b:\n%s' % '\n'.join(buffer) )

		for line in buffer:
			matches = regex.match(line)
			if matches:
				items = matches.groupdict()
				host2user[ items['host'].strip().lower() ] = items['username'].strip()
				userlist.append( items['username'].strip() )

#		debugmsg( ud.ADMIN, ud.INFO, 'host2user=%s' % host2user )

		if self.ldap_anon.checkConnection(username = self._username, bindpw = self._password):
			while userlist:
				# get only 10 user realnames at a time
				usersubset = userlist[0:10]
				del userlist[0:10]

				filter = '(|'
				for user in usersubset:
					filter += '(uid=%s)' % user
				filter += ')'
				users = self.ldap_anon.lo.search( filter=filter, base=self.configRegistry[ 'ldap/base' ],
												  scope='sub', attr=[ 'cn', 'uid' ] )
				# iterate over all groups
				for userdn, userattrs in users:
					if userattrs.has_key('cn'):
						user2realname[ userattrs['uid'][0] ] = userattrs['cn'][0]

#		debugmsg( ud.ADMIN, ud.INFO, 'user2realname=%s' % user2realname )

		# get ip addresses of current group
		room = object.options.get( 'room', None )

		curgrpmembers = {}
		for grpdn, grpdata in groupdict.items():
			if grpdata[0]['cn'][0] == room:
				curgrpmembers = grpdata[1]

		if room == '::all':
			curgrpmembers = computerdict.keys()

		cmd = '/usr/bin/fping -C1'
		runfping = False
		for memberdn in curgrpmembers:
			computer = computerdict[memberdn]
			if computer.has_key('aRecord') and computer['aRecord']:
				cmd += ' %s' % computer['aRecord'][0]
				runfping = True

		if runfping:
			debugmsg( ud.ADMIN, ud.INFO, 'cmd=%s' % cmd )
			proc = notifier.popen.Shell( cmd, stdout = True, stderr = True )
			cb = notifier.Callback( self._roomadmin_room_list_return2, object, computers_blocked4internet, groupdict, computerdict, host2user, user2realname )
			proc.signal_connect( 'finished', cb )
			proc.start()
		else:
			debugmsg( ud.ADMIN, ud.INFO, 'do not call fping' )
			self.finished( object.id(), ( computers_blocked4internet, groupdict, computerdict, host2user, user2realname, {} ) )


#root@master30:/root# fping -C1 10.200.18.30 10.200.18.31 10.200.18.100 10.200.18.32 > /dev/null
#10.200.18.30  : 0.54
#10.200.18.31  : -
#10.200.18.100 : 0.53
#10.200.18.32  : -

	def _roomadmin_room_list_return2( self, pid, status, bufstdout, bufstderr, object, computers_blocked4internet, groupdict, computerdict, host2user, user2realname ):
		onlinestatus={}

		regex = re.compile( '^(?P<ipaddr>[.0-9]+) +\: (?P<status>[-.0-9]+)$' )

		for line in bufstderr:
			matches = regex.match(line)
			if matches:
				items = matches.groupdict()
				onlinestatus[ items['ipaddr'] ] = (items['status'] != '-')

		debugmsg( ud.ADMIN, ud.INFO, 'onlinestatus=%s' % onlinestatus )

		self.finished( object.id(), ( computers_blocked4internet, groupdict, computerdict, host2user, user2realname, onlinestatus ) )


	def _get_option( self, object, key, default = None ):
		if object.options.has_key( key ):
			return object.options[ key ]
		return default



	def roomadmin_set_access_internet_enable( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_set_access_internet_enable: options=%s' % object.options )

		ipaddrs = object.options.get('ipaddrs', None)

		umc.registry.load()
		keylist = umc.registry.keys()
		for key in keylist:
			if key.startswith('proxy/filter/hostgroup/blacklisted/'):
				blockedlist = umc.registry[ key ].split(' ')

				# remove selected ip addresses from blocklist
				blockedlist = [ x for x in blockedlist if x not in ipaddrs ]

				if not blockedlist:
					univention.config_registry.handler_unset( [ key ] )
					debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_set_access_internet_enable: removed %s' % key )
				else:
					univention.config_registry.handler_set( [ '%s=%s'  % (key.encode(), ' '.join(blockedlist).encode()) ] )

		self.finished( object.id(), () )


	def roomadmin_set_access_internet_disable( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_set_access_internet_disable: options=%s' % object.options )

		ipaddrs = object.options.get('ipaddrs', None)

		if ipaddrs:
			key = 'proxy/filter/hostgroup/blacklisted/global'
			umc.registry.load()
			if umc.registry.has_key(key):
				blockedlist = umc.registry[ key ].split(' ')
				blockedlist = [ x for x in blockedlist if x not in ipaddrs ]
			else:
				blockedlist = []
			blockedlist.extend(ipaddrs)
			univention.config_registry.handler_set( [ '%s=%s'  % (key.encode(), ' '.join(blockedlist).encode()) ] )

		self.finished( object.id(), () )


	def roomadmin_room_search( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_search=%s' % object.options )

		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		# get searchfilter
		sfilter = object.options.get('filter', '*')

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_anon.switch_ou( '438' )
			self.ldap_master.switch_ou( '438' )
		else:
			if object.options.get('ou',None):
				self.ldap_anon.switch_ou( object.options.get('ou') )
				self.ldap_master.switch_ou( object.options.get('ou') )

		roomgroupdict = {}
		computerdict = {}

		if not object.incomplete:
			(tmpgroupdict, tmpcomputerdict) = self._get_groups_and_computers( self.ldap_anon.searchbaseComputers, self.ldap_anon.searchbaseRooms )
			roomgroupdict.update(tmpgroupdict)
			computerdict.update(tmpcomputerdict)

			debugmsg( ud.ADMIN, ud.INFO, 'roomgroupdict=%s' % roomgroupdict )
			# remove nonmatching groups
			for key in roomgroupdict.keys():
				searchkey = 'cn'
				if object.options.get('key','') in [ 'description' ]:
					searchkey = object.options.get('key')
				if roomgroupdict[key][0].has_key(searchkey):
					if not fnmatch.fnmatch( roomgroupdict[key][0][searchkey][0], sfilter ):
						del roomgroupdict[key]
				else:
					del roomgroupdict[key]

		self.finished( object.id(), (self.ldap_anon.availableOU, roomgroupdict) )


	def roomadmin_room_edit( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_edit=%s' % object.options )

		if not self.ldap_master.checkConnection(username = self._username, bindpw = self._password):
			self.finished( object.id(), None,
						   report = _( 'No admin connection to the LDAP database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_master.switch_ou( '438' )
			self.ldap_anon.switch_ou( '438' )
		else:
			if object.options.get('ou',None):
				self.ldap_master.switch_ou( object.options.get('ou') )
				self.ldap_anon.switch_ou( object.options.get('ou') )

		# get room DN and room description
		roomdn = object.options.get( 'roomdn', None )
		description = object.options.get( 'description', None )
		if description == None and roomdn:
			try:
				result = univention.admin.modules.lookup( self.ldap_master.groupmodule, self.ldap_master.co, self.ldap_master.lo,
														  scope = 'sub', superordinate = None,
														  base = roomdn, filter = '')
				if result and result[0]:
					room = result[0]
					room.open()
					description = room['description']
			except Exception, e:
				debugmsg( ud.ADMIN, ud.ERROR, 'getting room description failed (room=%s): %s' % (roomdn, e) )
				import traceback, sys
				info = sys.exc_info()
				lines = traceback.format_exception(*info)
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % ''.join(lines) )
				report = _('An error occured while getting group description! Please consult local administrator.')
		else:
			description = None

		# get computers assigned to selected room
		roommember = self.ldap_master.get_group_member_list( roomdn, filterbase=self.ldap_master.searchbaseComputers, attrib='hosts' )

		roomnamedefault = None
		if self.configRegistry.has_key('umc/schooladmin/groups/defaultgroupprefix') and self.configRegistry['umc/schooladmin/groups/defaultgroupprefix']:
			roomnamedefault = self.configRegistry['umc/schooladmin/groups/defaultgroupprefix']
			roomnamedefault = roomnamedefault % { 'departmentNumber': self.ldap_master.departmentNumber }
			debugmsg( ud.ADMIN, ud.INFO, 'roomnamedefault = %s' % roomnamedefault)

		self.finished( object.id(), ( self.ldap_master.availableOU, self.ldap_master.searchbaseComputers, description, roommember, roomnamedefault ) )


	def roomadmin_room_add( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_add=%s' % object.options )

		if not self.ldap_master.checkConnection(username = self._username, bindpw = self._password):
			self.finished( object.id(), None,
						   report = _( 'No admin connection to the LDAP database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_master.switch_ou( '438' )
			self.ldap_anon.switch_ou( '438' )
		else:
			if object.options.get('ou',None):
				self.ldap_master.switch_ou( object.options.get('ou') )
				self.ldap_anon.switch_ou( object.options.get('ou') )

		description = None
		roommember = []

		roomnamedefault = None
		if self.configRegistry.has_key('umc/schooladmin/groups/defaultgroupprefix') and self.configRegistry['umc/schooladmin/groups/defaultgroupprefix']:
			roomnamedefault = self.configRegistry['umc/schooladmin/groups/defaultgroupprefix']
			roomnamedefault = roomnamedefault % { 'departmentNumber': self.ldap_master.departmentNumber }
			debugmsg( ud.ADMIN, ud.INFO, 'roomnamedefault = %s' % roomnamedefault)

		self.finished( object.id(), ( self.ldap_master.availableOU, self.ldap_master.searchbaseComputers, description, roommember, roomnamedefault ) )


	def roomadmin_room_set( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_set=%s' % object.options )

		# test if user is allowed to execute roomadmin/room/add
		if not object.options.get('roomdn',False) and not self.permitted('roomadmin/room/add', {} ):
			debugmsg( ud.ADMIN, ud.ERROR, _('user is not allowed to execute %s') % 'roomadmin/room/add')
			self.finished( object.id(), None,
						   report = _( 'You are not allowed to execute this action. Please contact local administrator.' ),
						   success = False )
			return

		# test if user is allowed to execute roomadmin/room/edit
		if object.options.get('roomdn',False) and not self.permitted('roomadmin/room/edit', {} ):
			debugmsg( ud.ADMIN, ud.ERROR, _('user is not allowed to execute %s') % 'roomadmin/room/edit')
			self.finished( object.id(), None,
						   report = _( 'You are not allowed to execute this action. Please contact local administrator.' ),
						   success = False )
			return


# {  'roomdn': u'cn=002-Raum017b,cn=raeume,cn=groups,ou=002,dc=schule,dc=bremen,dc=de',
#	 'roommembers': [u'cn=win002-01,cn=computers,ou=002,dc=schule,dc=bremen,dc=de',
#						u'cn=w002pc01,cn=computers,ou=002,dc=schule,dc=bremen,dc=de',
#						u'cn=w002pc02,cn=computers,ou=002,dc=schule,dc=bremen,dc=de',
#						u'cn=w002pc03,cn=computers,ou=002,dc=schule,dc=bremen,dc=de'],
#	 'createroom': False,
#	 'description': u'Beschreibung',
# 	 'room': u'002-Raum017b'
# }

		if not self.ldap_master.checkConnection(username = self._username, bindpw = self._password):
			self.finished( object.id(), None,
						   report = _( 'No admin connection to the LDAP database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_anon.switch_ou('438')
			self.ldap_master.switch_ou('438')
		else:
			if object.options.get('ou',None):
				self.ldap_anon.switch_ou( object.options.get('ou') )
				self.ldap_master.switch_ou( object.options.get('ou') )

		roomdn = object.options.get( 'roomdn', None )
		room = object.options.get( 'room', None )
		roommembers = object.options.get( 'roommembers', None )
		description = object.options.get( 'description', None )

		report = ''

		if roommembers == None:
			debugmsg( ud.ADMIN, ud.ERROR, 'cannot change room members: roommembers == None')
			self.finished( object.id(), None, success = False, report = _( 'Cannot change room members') )
			return

		if roomdn:
			# change room (group) object
			report = ''

			try:
				groupresult = univention.admin.modules.lookup( self.ldap_master.groupmodule, self.ldap_master.co, self.ldap_master.lo,
															   scope = 'sub', superordinate = None,
															   base = roomdn, filter = '')
				if groupresult and groupresult[0]:
					gr = groupresult[0]
					gr.open()
					gr['description'] = description
					gr['hosts'] = roommembers
					dn = gr.modify()
			except Exception, e:
				debugmsg( ud.ADMIN, ud.ERROR, 'change of room members failed (group=%s): %s' % (roomdn, e) )
				import traceback, sys
				info = sys.exc_info()
				lines = traceback.format_exception(*info)
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % ''.join(lines) )
				report = _('An error occured while updating room! Please consult local administrator. (%s)') % ''.join(traceback.format_exception_only(*(info[0:2])))
		else:
			# no roomdn present ==> create new room (group)

			tmpPosition = univention.admin.uldap.position(self.configRegistry['ldap/base'])
			tmpPosition.setDn(self.ldap_master.searchbaseRooms)

			try:
				groupObject=self.ldap_master.groupmodule.object(self.ldap_master.co, self.ldap_master.lo, position=tmpPosition)
				groupObject.open()
				groupObject.options = [ 'posix' ]
				groupObject['name'] = room
				groupObject['description'] = description
				groupObject['hosts'] = roommembers
				dn = groupObject.create()
				debugmsg( ud.ADMIN, ud.INFO, 'created object %s' % dn )

			except univention.admin.uexceptions.objectExists:
				debugmsg( ud.ADMIN, ud.WARN, 'creating room %s failed: objectExists' % room )
				report = _('Cannot create room - object already exists!')
			except univention.admin.uexceptions.groupNameAlreadyUsed:
				debugmsg( ud.ADMIN, ud.WARN, 'creating room %s failed: groupNameAlreadyUsed' % room )
				report = _('Cannot create room - groupname already used!')
			except Exception, e:
				import traceback, sys
				info = sys.exc_info()
				lines = traceback.format_exception(*info)
				debugmsg( ud.ADMIN, ud.ERROR, 'creating room %s at %s failed: %s' % (room, tmpPosition.getDn(), ''.join(traceback.format_exception_only(*(info[0:2])))) )
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % ''.join(lines) )
				report = _('An error occured while creating room! Please consult local administrator.  (%s)') % ''.join(traceback.format_exception_only(*(info[0:2])))

		self.finished( object.id(), ( ), success = (len(report) == 0), report = report )


	def roomadmin_room_remove( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'roomadmin_room_remove=%s' % object.options )

		if not self.ldap_master.checkConnection(username = self._username, bindpw = self._password):
			self.finished( object.id(), None,
						   report = _( 'No admin connection to the LDAP database available, please try again later' ),
						   success = False )
			return

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_master.availableOU:
			self.ldap_anon.switch_ou('438')
			self.ldap_master.switch_ou('438')
		else:
			if object.options.get('ou',None):
				self.ldap_anon.switch_ou( object.options.get('ou') )
				self.ldap_master.switch_ou( object.options.get('ou') )

		roomdnlist = object.options.get( 'roomdn', [] )
		confirmed = object.options.get( 'confirmed', False )

		message = []

		if confirmed:
			for dn in roomdnlist:
				try:
					tmpPosition = univention.admin.uldap.position(self.ldap_master.searchbaseRooms)
					obj = univention.admin.objects.get( self.ldap_master.groupmodule, self.ldap_master.co,
														self.ldap_master.lo, tmpPosition, dn = dn )
					obj.open()
					obj.remove()
					ud.debug( ud.ADMIN, ud.ERROR, 'removed %s' % dn )
				except Exception, e:
					ud.debug( ud.ADMIN, ud.ERROR, 'removal of group %s failed: %s' % (dn, e) )
					message.append( dn )
					import traceback, sys
					info = sys.exc_info()
					lines = traceback.format_exception(*info)
					ud.debug( ud.ADMIN, ud.ERROR, 'TRACEBACK:\n%s' % ''.join(lines) )

		roomdnlist = sorted( roomdnlist )

		ud.debug( ud.ADMIN, ud.INFO, 'confirmed=%s  roomdnlist=%s' % (confirmed, roomdnlist))

		self.finished( object.id(), (self.ldap_master.availableOU, len(message)==0, message) )
