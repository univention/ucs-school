#!/usr/bin/python2.4
#
# Univention Management Console
#  module: School Lesson Configuration Module
#
# Copyright (C) 2007-2010 Univention GmbH
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

from univention.management.console.handlers.distribution import getProject, saveProject

import univention.debug as ud
import univention.uldap

import notifier
import notifier.popen

import os, re, fnmatch
import urllib
import inspect
import datetime
import time
import copy
import operator
import pickle

import _revamp
import _types
import _schoolldap
import univention.reservation.dbconnector as reservationdb
import pwd, grp

_ = umc.Translation( 'univention.management.console.handlers.reservation' ).translate

DISTRIBUTION_DATA_PATH = '/var/lib/ucs-school-umc-distribution'
DISTRIBUTION_CMD = '/usr/lib/ucs-school-umc-distribution/umc-distribution'

icon = 'reservation/module'
short_description = _( 'Lesson configuration' )
long_description = _( 'School lesson configuration' )
categories = [ 'all' ]

def joineddict(*args):
	tmp = {}
	for item in args:
		tmp.update(item)
	return tmp

command_description = {
	'reservation/list': umch.command(
		short_description = _( 'Reservations' ),
		long_description = _( 'List Reserations' ),
		method = 'reservation_list',
		values = { 'key' : _types.searchkey_reservation,
			   'searchfilter' : _types.sfilter,
	   		   'date_start': _types.date,
				   },
		startup = True,
		#caching = True,
		priority = 90
	),
	'reservation/edit': umch.command(
		short_description = _( 'Edit Reservation' ),
		long_description = _( 'Edit Reservation' ),
		method = 'reservation_edit',
		values = joineddict(
			_types.Reservation.values,
			{ 'key' : _types.searchkey_reservation,
			   'searchfilter' : _types.sfilter,
			   'ou': _types.department,
				   },
			)

	),
#	'reservation/write': umch.command(
#		short_description = _( 'Save Reservation' ),
#		long_description = _( 'Save Reservation' ),
#		method = 'reservation_write',
#		values = joineddict(
#			_types.Reservation.values,
#			{ 'key' : _types.searchkey_reservation,
#			   'searchfilter' : _types.sfilter,
#			   'ou': _types.department,
#				   } ),
#	),
	'reservation/remove': umch.command(
		short_description = _( 'Remove reservation' ),
		long_description = _( 'Remove reservation' ),
		method = 'reservation_remove',
		values = joineddict(
			_types.Reservation.values,
			{ 'ou': _types.department,
				   } ),
	),
	'reservation/profile/list': umch.command(
		short_description = _( 'Reservation profiles' ),
		long_description = _( 'List reservation profiles' ),
		method = 'reservation_profile_list',
		values = { 'key' : _types.searchkey_profile,
			   'searchfilter' : _types.sfilter,
			   'date_start' : _types.date,
				   },
		startup = True,
		#caching = True,
		priority = 80
	),
	'reservation/profile/edit': umch.command(
		short_description = _( 'Edit reservation profile' ),
		long_description = _( 'Edit reservation profile' ),
		method = 'reservation_profile_edit',
		values = joineddict(
			_types.Profile.values,
			{ 'key' : _types.searchkey_profile,
			   'searchfilter' : _types.sfilter,
				   } ),
	),
	'reservation/profile/write': umch.command(
		short_description = _( 'Save reservation profile' ),
		long_description = _( 'Save reservation profile' ),
		method = 'reservation_profile_write',
		values = _types.Profile.values,
	),
	'reservation/profile/remove': umch.command(
		short_description = _( 'Remove reservation profile' ),
		long_description = _( 'Remove Reservation Profile' ),
		method = 'reservation_profile_remove',
		values = _types.Profile.values,
	),
	'reservation/lessontimes/edit': umch.command(
		short_description = _( 'Edit lessontimes' ),
		long_description = _( 'Edit lessontime definitions' ),
		method = 'reservation_lessontimes_edit',
		values = _types.Lessontime.values,
		startup = True,
		priority = 70
	),
}

def debugmsg( component, level, msg ):
	info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
	printInfo = []
	if len(info[0])>20:
		printInfo.append('...'+info[0][-17:])
	else:
		printInfo.append(info[0])
	printInfo.extend(info[1:3])
	ud.debug(component, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))


class handler( umch.simpleHandler, _revamp.Web  ):
	#defaults={}
	date_range = datetime.timedelta(weeks=2)

	def __init__( self ):
		global command_description
		umch.simpleHandler.__init__( self, command_description )
		#_revamp.Web.__init__( self )

		self._uid = None
		self.date_window_end = None
		self.date_window_begin = None

		# get connection to reservation database
		f = open("/etc/reservation-sql.secret")
		password = f.readline().rstrip()
		f.close()
		reservationdb.connect (host = "localhost",
			db = "reservation",
			user = "reservation",
			passwd = password )

		# get UCR
		#umc.registry.load()

		## inititate an anonymous LDAP connection to the local directory
		self.ldap_anon = _schoolldap.SchoolLDAPConnection()
		## inititate an autheticated connection to the master
		#self.ldap_master = _schoolldap.SchoolLDAPConnection( ldapserver = umc.registry['ldap/master'],
		#				username = self._uid, bindpw = self._password )

		# TODO FIXME HARDCODED HACK for SFB
		# set available OU to hardcoded defaults
		if '438' in self.ldap_anon.availableOU:
			defaultOU = '438'
		else:
			defaultOU = self.ldap_anon.availableOU[0]
		debugmsg( ud.ADMIN, ud.INFO, 'registration.__init__: availableOU=%s' % self.ldap_anon.availableOU )

		### defaults
		_types.timetable.update()	# read the lessontimes table
		_types.syntax['time_begin'].set_today(True)
		today = datetime.date.today().strftime("%Y-%m-%d")

		_types.defaults['reservation_list'] = {
			'searchfilter': '*',
			'key': 'roomname',
			'ou': defaultOU,
			'date_start': today,
		}
		reservation = _types.Reservation( { 'date_start': today } )
		_types.defaults['reservation_edit'] = joineddict(
			reservation.defaults, {
			'ou': defaultOU,
			} )
		_types.defaults['reservation_profile_list'] = {
			'searchfilter': '*',
			'key': 'reservation_name',
		}
		profile = _types.Profile
		_types.defaults['reservation_profile_edit'] = profile.defaults
		lessontime = _types.Lessontime
		_types.defaults['reservation_lessontimes_edit'] = lessontime.defaults

	def _escapeUrlList( self, urllist ):
		for i in range(len(urllist)):
			urllist[i] = self._escapeUrl(urllist[i])

	def _escapeUrl( self, url ):
		return urllib.quote(url,':%/?=&')

	def _debug(self, level, msg):
		info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
		printInfo = []
		if len(info[0])>25:
			printInfo.append('...'+info[0][-22:])
		else:
			printInfo.append(info[0])
		printInfo.extend(info[1:3])
		ud.debug(univention.debug.ADMIN, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))

	def _convert_filter_syntax( self, searchfilter ):
		for old, new in [ ( '\\', '\\\\' ),	( '.', '\.' ),
						 ( '*', '.*' ),		( '+', '\+' ),
						 ( '(', '\(' ),     ( ')', '\)' ),
						 ( '[', '\[' ),     ( ']', '\]' ),
						 ( '{', '\{' ),     ( '}', '\}' ),
						 ( '?', '\?' ),		( '^', '\^' ),
						 ( '$', '\$' ),     ( '|', '\|' ) ]:
			searchfilter = searchfilter.replace(old, new)
		return searchfilter

	def _get_groups( self, basedn ):
		"""
		returns ( groupdict )

		groupdict[groupdn] = [ groupattrs, memberlist ]
		groupattrs = { 'attr': [ 'val1', 'val2' ], ... }
		memberlist = [ 'dn1', 'dn2', ... ]
		"""
		groupdict = {}

		if self.ldap_anon.checkConnection():
			try:
				debugmsg( ud.ADMIN, ud.INFO, 'basedn_groups=%s' % basedn )
				groups = self.ldap_anon.lo.search( filter='objectClass=univentionGroup', base=basedn,
												   scope='one', attr=[ 'cn', 'description', 'gidNumber' ] )

				#debugmsg( ud.ADMIN, ud.INFO, 'groups=%s' % groups )
				## iterate over all groups
				for grpdn, grpattrs in groups:
					groupdict[grpdn] = [ grpattrs ]

				debugmsg( ud.ADMIN, ud.INFO, 'got %d group objects' % len(groupdict) )
#				debugmsg( ud.ADMIN, ud.INFO, 'group objects = %s' % groupdict )
			except Exception, e:
				debugmsg( ud.ADMIN, ud.ERROR, 'getting groups failed: %s' % str(e) )
				import traceback, sys
				lines = traceback.format_exc().replace('%','#')
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )

		return groupdict

	def _get_rooms_and_computers( self, basedn_rooms, basedn_computers ):
		"""
		returns ( roomdict, computerdict )

		roomdict[roomdn] = [ roomattrs, memberlist ]
		roomattrs = { 'attr': [ 'val1', 'val2' ], ... }
		memberlist = [ 'dn1', 'dn2', ... ]

		computerdict[ compdn ] = compattr
		compattr = { 'attr': [ 'val1', 'val2' ], ... }
		"""
		roomdict = {}
		computerdict = {}
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

			debugmsg( ud.ADMIN, ud.INFO, 'basedn_rooms=%s' % basedn_rooms )
			try:
				rooms = self.ldap_anon.lo.search( filter='objectClass=univentionGroup', base=basedn_rooms,
												   scope='sub', attr=[ 'cn', 'uniqueMember', 'description', 'gidNumber' ] )
			except Exception, e:
				debugmsg( ud.ADMIN, ud.ERROR, 'getting rooms failed: %s' % str(e) )
				import traceback, sys
				lines = traceback.format_exc().replace('%','#')
				debugmsg( ud.ADMIN, ud.ERROR, 'TRACEBACK\n%s' % lines )
				rooms = []

			debugmsg( ud.ADMIN, ud.INFO, 'rooms=%s' % rooms )
			# iterate over all rooms
			for roomdn, roomattrs in rooms:
				memberlist = []
				if roomattrs.has_key('uniqueMember'):

					# check all uniqueMembers
					for memberdn in roomattrs['uniqueMember']:
						# is uniqueMember a computer?
						if memberdn in computerdict:
							# mark computer entry as used
							computerflag[memberdn] = 1
							memberlist.append(memberdn)
				roomdict[roomdn] = [ roomattrs, memberlist ]

			debugmsg( ud.ADMIN, ud.INFO, 'got %d room objects' % len(roomdict) )
#			debugmsg( ud.ADMIN, ud.INFO, 'room objects = %s' % roomdict )

		return (roomdict, computerdict)

	def condition_reservation_date_window(self, reservation):
		#endtime = time.strptime( reservation.endTime , "%Y-%m-%d %H:%M:%S")
		#endtime_obj = datetime.datetime( *endtime[0:6] )
		if reservation.isIterable ():
			if self.date_window_end:
				if reservation.startTime <= self.date_window_end:
					if reservation.iterationEnd:
						if reservation.iterationEnd >= self.date_window_begin:
							return True
						else:
							return False
					return True
				return False
			else:
				return True
		if reservation.endTime >= self.date_window_begin:
			if self.date_window_end:
				if reservation.endTime <= self.date_window_end:
					return True
			else:
				return True
		debugmsg( ud.ADMIN, ud.INFO, 'DEBUG: filter out %s ' % reservation.endTime )
		return False

	def reservation_list( self, object ):
		# this cannot be done in __init__
		self._uid = pwd.getpwnam(self._username)[2]

		debugmsg( ud.ADMIN, ud.INFO, 'reservation_list: options=%s' % object.options )
		## Authenticate the LDAP connection to get access to all information available to us
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)
		currentOU = _types.defaults.get(object.options, 'reservation_list', 'ou')
		debugmsg( ud.ADMIN, ud.INFO, 'reservation_list: currentOU: %s' % currentOU )

		#currentOU=object.options.get('ou')
		#if '438' in self.ldap_anon.availableOU:
		#	currentOU='438'

		if currentOU != self.ldap_anon.departmentNumber:
			#self.ldap_master.switch_ou( currentOU )
			self.ldap_anon.switch_ou( currentOU )

		usergiddict = {}
		for grpdn, grpdata in self._get_groups( self.ldap_anon.searchbaseClasses ).items():
			usergiddict[ int(grpdata[ 0 ][ 'gidNumber' ][ 0 ]) ] = grpdata[ 0 ][ 'cn' ][ 0 ]
		for grpdn, grpdata in self._get_groups( self.ldap_anon.searchbaseExtGroups ).items():
			usergiddict[ int(grpdata[ 0 ][ 'gidNumber' ][ 0 ]) ] = grpdata[ 0 ][ 'cn' ][ 0 ]
		hostgiddict = {}
		(tmproomdict, tmpcomputerdict) = self._get_rooms_and_computers( self.ldap_anon.searchbaseRooms, self.ldap_anon.searchbaseComputers )
		for grpdn, grpdata in tmproomdict.items():
			hostgiddict[ int(grpdata[ 0 ][ 'gidNumber' ][ 0 ]) ] = grpdata[ 0 ][ 'cn' ][ 0 ]

		# preparation done, handle action
		action = object.options.get('action')
		if action:
			if action == 'search':
				key = object.options['key']
				searchfilter = self._convert_filter_syntax( object.options['searchfilter'] )
				#self._debug( ud.INFO, 'searchfilter=%s' % searchfilter )
				regexp = re.compile(searchfilter, re.I)

		#for ou in self.ldap_anon.availableOU:
		#	self.ldap_anon.switch_ou(ou)
		#	(tmpgroupdict, tmpcomputerdict) = self._get_groups_and_computers( self.ldap_anon.searchbaseComputers, self.ldap_anon.searchbaseRooms )
		#	groupdict.update(tmpgroupdict)
		#	computerdict.update(tmpcomputerdict)


		if object.options.get('date_start'):
			date_start = _types.defaults.get(object.options, 'reservation_list', 'date_start')
			self.date_window_begin = datetime.datetime( *time.strptime(date_start, "%Y-%m-%d")[0:6] )
		else:
			self.date_window_begin = datetime.datetime.now()
		if action == 'search' and not ( searchfilter == '*' or object.options.get('date_start') ): # specific or dateless
			self.date_window_end = None
		else:
			self.date_window_end = self.date_window_begin + self.date_range


		# get list of reservations from reservationdb
		reservation_list = reservationdb.getReservationsList()
		# profile_list = reservationdb.getProfilesList()

		currentOU = _types.defaults.get(object.options, 'reservation_list', 'ou')
		searchresult = []
		if action == 'search':
			for reservation in reservation_list:
				#for key in reservationdb.Reservation.ROWS:
				#	self._debug( ud.INFO, 'db.reservation[%s]: %s' % (key, getattr(reservation,key, None)) )
				# ignore reservations marked for deletion
				if reservation.deleteFlag:
					continue
				# get all items matching to regex
				if key == 'groupname':
					groupname = usergiddict.get(reservation.usergroup, currentOU+'-')
					value = groupname.replace(currentOU+'-','')
				elif key == 'roomname':
					value = hostgiddict.get(reservation.hostgroup, '')
				elif key == 'ownername':
					try:
						value = pwd.getpwuid(reservation.owner)[0]
					except KeyError:
						value = 'uidNumber=%s' % reservation.owner
				elif key == 'reservation_name':
					value = reservation.name
				else:
					value = getattr(reservation, key, '')
				if value and regexp.search(value) and self.condition_reservation_date_window(reservation):
					#order = ('reservationID', 'reservation_name', 'description', 'date_start', 'time_begin', 'time_end', 'room', 'group', 'owner')
					date_start = reservation.startTime.strftime("%Y-%m-%d")
					time_begin = reservation.startTime.strftime("%H:%M")
					time_end = reservation.endTime.strftime("%H:%M")
					groupname = usergiddict.get(reservation.usergroup, currentOU+'-')
					roomname = hostgiddict.get(reservation.hostgroup, '')
					try:
						ownername = pwd.getpwuid(reservation.owner)[0]
					except KeyError:
						ownername = 'uidNumber=%s' % reservation.owner
					l = [ str(reservation.id), reservation.name, reservation.description,
						date_start, time_begin,
						time_end,
						roomname, groupname, ownername, reservation.isIterable(), reservation.isError(), reservation.status ]
					p = reservationdb.Profile.get( reservation.resprofileID )
					if p:
						l.append(p.name)
					else:
						l.append(str(reservation.resprofileID))
					searchresult.append(l)
				#self._debug( ud.INFO, 'searchresult_filtered=%s' % searchresult )
		else:
			for reservation in reservation_list:
				# ignore reservations marked for deletion
				if reservation.deleteFlag:
					continue
				if self.condition_reservation_date_window(reservation) \
					and reservation.owner == self._uid:
					#order = ('reservationID', 'reservation_name', 'description', 'date_start', 'time_begin', 'time_end', 'room', 'group', 'owner')
					date_start = reservation.startTime.strftime("%Y-%m-%d")
					time_begin = reservation.startTime.strftime("%H:%M")
					time_end = reservation.endTime.strftime("%H:%M")
					groupname = usergiddict.get(reservation.usergroup, '')
					roomname = hostgiddict.get(reservation.hostgroup, '')
					ownername = pwd.getpwuid(reservation.owner)[0]
					l = [ str(reservation.id), reservation.name, reservation.description,
						date_start, time_begin,
						time_end,
						roomname, groupname, ownername, reservation.isIterable(), reservation.isError(), reservation.status ]
					p = reservationdb.Profile.get( reservation.resprofileID )
					if p:
						l.append(p.name)
					else:
						l.append(str(reservation.resprofileID))
					searchresult.append(l)
				#self._debug( ud.INFO, 'searchresult_filtered=%s' % searchresult )

		self.finished( object.id(), ( searchresult ) )

	def reservation_edit( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'reservation_edit: options=%s' % object.options )

		reservationID = object.options.get('reservationID')
		action = object.options.get('action')
		if not action:
			if reservationID:
				r = reservationdb.Reservation.get( reservationID )
				if r:
					object.options['reservationID'] = str(r.id)
					object.options['reservation_name'] = r.name
					try:
						object.options['roomname'] = grp.getgrgid(r.hostgroup)[0]
					except KeyError:
						object.options['roomname'] = ''
					try:
						object.options['groupname'] = grp.getgrgid(r.usergroup)[0]
					except KeyError:
						object.options['groupname'] = '%s-' % object.options['ou']
					try:
						object.options['ownername'] = pwd.getpwuid(r.owner)[0]
					except KeyError:
						object.options['ownername'] = 'uidNumber=%s' % r.owner
					for key in ['description', 'iterationDays', 'resprofileID']:
						object.options[key] = str(getattr(r, key, '') or '')
					# decode the dates from Iso format
					object.options['date_start'] = r.startTime.strftime("%Y-%m-%d")
					object.options['time_begin'] = r.startTime.strftime("%H:%M")
					object.options['date_end'] = r.endTime.strftime("%Y-%m-%d")
					object.options['time_end'] = r.endTime.strftime("%H:%M")
					if r.iterationDays:
						object.options['iterationEnd'] = r.iterationEnd.strftime("%Y-%m-%d")
					for o in r.options:
						if o.setting.id:	# safty check, db consistent?
							object.options[o.setting.name] = o.value

					# load distribution project info (not used yet)
					#project_name = object.options.get('distributionID')
					#if project_name:
					#	fn_project = os.path.join( DISTRIBUTION_DATA_PATH, project_name )
					#	fd_project = open(fn_project, 'r')
					#	project = pickle.load( fd_project )
					#	fd_project.close()

					#	object.options['files'] = project['files']
					#	object.options['collectfiles'] = project['collectFiles']

		currentOU = _types.defaults.get(object.options, 'reservation_edit', 'ou')
		debugmsg( ud.ADMIN, ud.INFO, 'reservation_edit: currentOU: %s' % currentOU )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		#currentOU=object.options.get('ou')
		#if '438' in self.ldap_anon.availableOU:
		#	currentOU='438'

		if currentOU != self.ldap_anon.departmentNumber:
			#self.ldap_master.switch_ou( currentOU )
			self.ldap_anon.switch_ou( currentOU )

		# Get list of rooms/hostgroups
		roomdict = {}
		classgroupdict = {}
		prjgroupdict = {}

		## rooms
		(tmproomdict, tmpcomputerdict) = self._get_rooms_and_computers( self.ldap_anon.searchbaseRooms, self.ldap_anon.searchbaseComputers )
		roomdict.update(tmproomdict)
		#computerdict.update(tmpcomputerdict)

		## groups
		(tmpusergroupdict) = self._get_groups( self.ldap_anon.searchbaseClasses )
		classgroupdict.update(tmpusergroupdict)
		(tmpusergroupdict) = self._get_groups( self.ldap_anon.searchbaseExtGroups )
		prjgroupdict.update(tmpusergroupdict)

		profileList = []
		profile_list = reservationdb.getProfilesList()
		for p in profile_list:
			if p.owner in (self._uid, _types.AdminUserUID):
				ownername = pwd.getpwuid(p.owner)[0]
				l = [ str(p.resprofileID), p.name, p.description, ownername ]

				profileList.append(l)

		# Commented out: the Widget for date_start does not reload the page, so we cannot update this flag.
		#if object.options['date_start'] == _types.defaults['reservation_list']['date_start']:
		#	_types.syntax['time_begin'].set_today()
		#else:
		#	_types.syntax['time_begin'].set_today(False)

		if action in ( 'write', 'override' ):
			date_start = object.options.get('date_start')
			time_begin = object.options.get('time_begin')
			if date_start and time_begin:
				object.options['date_end'] = date_start	# default
				# Adjust custom values
				now_obj = datetime.datetime.now()
				adhoc = False
				if object.options['time_begin'] == 'now':
					adhoc = True
					object.options['time_begin'] = now_obj.strftime("%H:%M")
				debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: time_begin=%s' % object.options['time_begin'] )
				if object.options['time_end'] in ('endoflesson', 'in45min', 'in1.5h', 'in3h', 'endofday'):
					if object.options['time_end'] == 'endoflesson':
						object.options['time_end'] = _types.endtime_to_lesson(object.options['time_begin'])['end']
						debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: end=%s' % object.options['time_end'] )
					elif object.options['time_end'] == 'in45min':
						time_delta = datetime.timedelta(seconds=2700)
						end_obj = now_obj + time_delta
						object.options['time_end'] = end_obj.strftime("%H:%M")
						object.options['date_end'] = end_obj.strftime("%Y-%m-%d")
					elif object.options['time_end'] == 'in1.5h':
						time_delta = datetime.timedelta(seconds=2*2700)
						end_obj = now_obj + time_delta
						object.options['time_end'] = end_obj.strftime("%H:%M")
						object.options['date_end'] = end_obj.strftime("%Y-%m-%d")
					elif object.options['time_end'] == 'in3h':
						time_delta = datetime.timedelta(seconds=4*2700)
						end_obj = now_obj + time_delta
						object.options['time_end'] = end_obj.strftime("%H:%M")
						object.options['date_end'] = end_obj.strftime("%Y-%m-%d")
					elif object.options['time_end'] == 'endofday':
						object.options['time_end'] = "00:00"
						s = datetime.datetime(*time.strptime( object.options['date_start'], "%Y-%m-%d")[0:3])
						s += datetime.timedelta(days=1)
						object.options['date_end'] = s.strftime("%Y-%m-%d")
					debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: time_end=%s' % object.options['time_end'] )

				startTime = datetime.datetime(*time.strptime( ' '.join((object.options['date_start'], object.options['time_begin'])) , "%Y-%m-%d %H:%M")[0:6])
				endTime = datetime.datetime(*time.strptime( ' '.join((object.options['date_end'], object.options['time_end'])) , "%Y-%m-%d %H:%M")[0:6])
				if int(object.options.get('iterationDays')) != 0:
					iterationEnd = datetime.datetime(*time.strptime( object.options['iterationEnd']+" 23:59:59" , "%Y-%m-%d %H:%M:%S")[0:6])
				else:
					iterationEnd = "0000-00-00 00:00:00"

				if not action == 'override':
					# collision detection
					collision = None
					reservation_list = reservationdb.getReservationsList()

					startDate2 = datetime.date( *time.strptime( object.options['date_start'] , "%Y-%m-%d")[0:3])

					usergroup = grp.getgrnam(object.options['groupname'])[2]
					hostgroup = grp.getgrnam(object.options['roomname'])[2]
					for reservation in reservation_list:
						if reservationID and str(reservation.id) == reservationID:
							#debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: no collision: reservationID reuse')
							# No self-collision, continue checks
							debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: reservationID and str(reservation.id) == reservationID')
							continue
						# no collision with reservations marked for deletion
						if reservation.deleteFlag:
							continue
						#sameroom = False
						#samegroup = False
						#sameday = False
						if reservation.hostgroup != hostgroup and reservation.usergroup != usergroup:
							debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: no collision: groups do not collide')
							continue
						startDate = reservation.startTime.date()
						if reservation.iterationDays != 0:
							debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: reservation.iterationDays != 0')
							iterationEndDate = reservation.iterationEnd.date()
							if startDate2 > iterationEndDate:
								debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: startDate2 > iterationEndDate')
								continue
							runDate = copy.copy(startDate)
							runDate2 = copy.copy(startDate2)
							if runDate2 > runDate:
								debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: runDate2 > runDate')
								iterationDays = datetime.timedelta(days= reservation.iterationDays)
								while runDate2 > runDate:
									runDate += iterationDays
							elif int(object.options['iterationDays']) != 0:
								debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: int(object.options["iterationDays"]) != 0')
								iterationEndDate2 = iterationEnd.date()
								if runDate > iterationEndDate2:
									debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: runDate > iterationEndDate2')
									continue
								iterationDays2 = datetime.timedelta(days= int(object.options['iterationDays']))
								while runDate > runDate2:
									runDate2 += iterationDays2
							if runDate != runDate2:
								debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: runDate != runDate2')
								continue
						elif int(object.options['iterationDays']) != 0:
							debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: int(object.options["iterationDays"]) != 0')
							iterationEndDate2 = iterationEnd.date()
							runDate = startDate
							if runDate > iterationEndDate2:
								debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: runDate > iterationEndDate2')
								continue
							iterationDays2 = datetime.timedelta(days= int(object.options['iterationDays']))
							runDate2 = copy.copy(startDate2)
							while runDate > runDate2:
								runDate2 += iterationDays2
							if runDate != runDate2:
								debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: runDate != runDate2')
								continue
						else:
							if startDate != startDate2:
								debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: startDate != startDate2')
								continue
						if startTime.time() > reservation.endTime.time() or\
						   endTime.time() < reservation.startTime.time():
							debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: startTime > reservation.endTime or endTime < reservation.startTime')
							continue
						### all criteria match: collision
						#order = ('reservationID', 'name', 'description', 'date_start', 'time_begin', 'time_end', 'hostgroup', 'usergroup')

						colliding_date_start = reservation.startTime.strftime("%Y-%m-%d")
						colliding_time_begin = reservation.startTime.strftime("%H:%M")
						colliding_time_end = reservation.endTime.strftime("%H:%M")
						colliding_roomname = grp.getgrgid(reservation.hostgroup)[0]
						colliding_groupname = grp.getgrgid(reservation.usergroup)[0]
						collision = [ str(reservation.id), reservation.name, reservation.description,
							colliding_date_start, colliding_time_begin,
							colliding_time_end,
							colliding_roomname, colliding_groupname ]

						p = reservationdb.Profile.get(reservation.resprofileID)
						if p:
							collision.append(p.name)
						else:
							collision.append(str(reservation.resprofileID))

						#debugmsg( ud.ADMIN, ud.INFO, 'collision: %s' % collision)
						break
					# collision handling
					if collision:
						object.options['collision'] = collision
						if adhoc:
							object.options['action'] = 'override'
							object.options['time_begin'] = 'now'
						else:
							debugmsg( ud.ADMIN, ud.INFO, 'collision: %s' % collision)
							object.options['action'] = 'collisionmessage'
						self.finished( object.id(), (self.ldap_anon.availableOU, roomdict, classgroupdict, prjgroupdict, profileList ) )
						return

				# ok we have the necessary data for a valid reservation
				object.options['ownername'] = self._username

				# handle file distribution
				if object.options.get('files') and not object.options.get('distributionID'):
					collectfiles = object.options.get('collectfiles', False)

					time_start_struct = time.strptime( '%s %s' % (object.options['date_start'], object.options['time_begin']), '%Y-%m-%d %H:%M' )
					time_start = time.mktime( time_start_struct )
					time_end_struct = time.strptime( '%s %s' % (object.options['date_start'], object.options['time_end']), '%Y-%m-%d %H:%M' )
					time_end = time.mktime( time_end_struct )

					project_name = ('R%.3f' % time.time()).replace('.','-')

					project_description = _('Reservation for Room "%s": %s %s-%s') % (
						object.options['roomname'],
						time.strftime( _('%Y-%m-%d'), time_start_struct ),
						object.options['time_begin'],
						object.options['time_end'],
						)


					groups = self.ldap_anon.lo.search( filter='(&(objectClass=univentionGroup)(cn=%s))' % object.options.get('groupname'), base=self.ldap_anon.searchbaseExtGroups,
													   scope='sub', attr=[ 'uniqueMember' ] )

					recipients_dn = []
					if len(groups) != 1:
						debugmsg( ud.ADMIN, ud.ERROR, 'unexpected group length=%s' % groups )
					else:
						grpdn, grpattrs = groups[0]
						recipients_dn = grpattrs.get('uniqueMember', [])

					project = getProject()
					project['name'] = project_name
					project['description'] = project_description
					project['filesnew'] = object.options.get('files', [])
					project['starttime'] = time_start
					# Setting the deadline causes umc-distribution to generate
					# an "at" job to collect.
					#
					# A) This is not necessary as the scheduler will regularly
					# run the cmdStop from the ressettings table at time_end.
					# B) The current scheduler policy for distribution projects
					# in the context of iterating dates is to not collect after
					# every iteration at time_end but only once at iterationEnd.
					#
					# project['deadline'] = time_end
					project['collectFiles'] = collectfiles
					project['sender_uid'] = self._username
					project['recipients_dn'] = recipients_dn

					# save user info
					fn_project = os.path.join( DISTRIBUTION_DATA_PATH, project['name'] )
					saveProject(fn_project, project)

					object.options['distributionID'] = project_name

					debugmsg( ud.ADMIN, ud.ALL, 'DEBUG: options=%s' % object.options )
					debugmsg( ud.ADMIN, ud.ALL, 'DEBUG: project=%s' % project )

				r = reservationdb.Reservation()

				settingsDict = reservationdb.getSettingsDict(filter='reservation')
				for key in object.options:
					## filter out defaults
					if key == 'internetfilter' and object.options['internetfilter'] == 'default':
						continue
					## passthrough values
					if key in reservationdb.Reservation.ROWS and key != 'reservationID':
						setattr(r, key, object.options[key])
					elif key in settingsDict:
						o = r.relateToSetting( settingsDict[key] )
						if o.value != object.options[key]:
							o.value = object.options[key]
				## translated values
				r.name = object.options['reservation_name']
				r.owner =  pwd.getpwnam(object.options['ownername'])[2]
				r.usergroup = grp.getgrnam(object.options['groupname'])[2]
				r.hostgroup = grp.getgrnam(object.options['roomname'])[2]
				# encode the dates into Iso format
				r.startTime = startTime
				debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: r.startTime=%s' % r.startTime )
				r.endTime = endTime
				debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: r.endTime=%s' % r.endTime )
				r.iterationEnd = iterationEnd
				debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: r.iterationEnd=%s' % r.iterationEnd )
				r.save()
				for o in r.options:
					o.save()

				old_r = None
				if action == 'override':
					old_r = reservationdb.Reservation.get( object.options['collision'][0] )
					del object.options['collision']
				elif reservationID:
					old_r = reservationdb.Reservation.get( reservationID )
				if old_r:
					old_r.replacedByID = r.id
					now_obj = datetime.datetime.now()
					delta = datetime.timedelta(seconds= 300)
					old_r.endTime = now_obj - delta
					old_r.save()

				object.options['action'] = 'message'

				if object.options.get('files'):
					finished_args = ( self.ldap_anon.availableOU, roomdict, classgroupdict, prjgroupdict, profileList )
					cmd = '%s --init %s' % (DISTRIBUTION_CMD, os.path.join( DISTRIBUTION_DATA_PATH, project['name'] ) )
					debugmsg( ud.ADMIN, ud.INFO, 'calling "%s"' % cmd )
					proc = notifier.popen.RunIt( cmd, stderr = True )
					cb = notifier.Callback( self._reservation_edit_return, object, finished_args )
					proc.signal_connect( 'finished', cb )
					proc.start()
					return

		self.finished( object.id(), (self.ldap_anon.availableOU, roomdict, classgroupdict, prjgroupdict, profileList ) )


	def _reservation_edit_return( self, pid, status, stdout, stderr, object, finished_args ):
		if status != 0:
			debugmsg( ud.ADMIN, ud.ERROR, 'reservation_edit_return: umc-distribute command returned exitcode %s' % status )
			debugmsg( ud.ADMIN, ud.ERROR, 'reservation_edit_return: umc-distribute command returned (stdout):\n %s' % stdout )
			debugmsg( ud.ADMIN, ud.ERROR, 'reservation_edit_return: umc-distribute command returned (stderr):\n %s' % stderr )
			object.options['message'] = _('Error while setting up reservation (status=%s)') % status

		#del object.options['action']		# clear action flag?
		self.finished( object.id(), finished_args )


#	def reservation_write( self, object ):
#		debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: options=%s' % object.options )
#
#		date_start = object.options.get('date_start')
#		time_begin = object.options.get('time_begin')
#		if date_start and time_begin:
#			object.options['date_end'] = date_start	# default
#			# Adjust custom values
#			now_obj = datetime.datetime.now()
#			adhoc = False
#			if object.options['time_begin'] == 'now':
#				adhoc = True
#				object.options['time_begin'] = now_obj.strftime("%H:%M")
#			debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: time_begin=%s' % object.options['time_begin'] )
#			if object.options['time_end'] in ('endoflesson', 'in45min', 'in1.5h', 'in3h', 'endofday'):
#				if object.options['time_end'] == 'endoflesson':
#					object.options['time_end'] = _types.endtime_to_lesson(object.options['time_begin'])['end']
#					debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: end=%s' % object.options['time_end'] )
#				elif object.options['time_end'] == 'in45min':
#					time_delta = datetime.timedelta(seconds=2700)
#					end_obj=now_obj + time_delta
#					object.options['time_end'] = end_obj.strftime("%H:%M")
#					object.options['date_end'] = end_obj.strftime("%Y-%m-%d")
#				elif object.options['time_end'] == 'in1.5h':
#					time_delta = datetime.timedelta(seconds=2*2700)
#					end_obj=now_obj + time_delta
#					object.options['time_end'] = end_obj.strftime("%H:%M")
#					object.options['date_end'] = end_obj.strftime("%Y-%m-%d")
#				elif object.options['time_end'] == 'in3h':
#					time_delta = datetime.timedelta(seconds=4*2700)
#					end_obj=now_obj + time_delta
#					object.options['time_end'] = end_obj.strftime("%H:%M")
#					object.options['date_end'] = end_obj.strftime("%Y-%m-%d")
#				elif object.options['time_end'] == 'endofday':
#					object.options['time_end'] = "00:00"
#					s = datetime.datetime(*time.strptime( object.options['date_start'], "%Y-%m-%d")[0:3])
#					s += datetime.timedelta(days=1)
#					object.options['date_end'] = s.strftime("%Y-%m-%d")
#				debugmsg( ud.ADMIN, ud.INFO, 'reservation_write: time_end=%s' % object.options['time_end'] )
#
#			# collision detection
#			collision = None
#			reservationID = object.options.get('reservationID')
#			reservation_list = reservationdb.getReservationsList()
#
#			startDate2 = datetime.date( *time.strptime( object.options['date_start'] , "%Y-%m-%d")[0:3])
#			startTime = datetime.datetime(*time.strptime( ' '.join((object.options['date_start'], object.options['time_begin'])) , "%Y-%m-%d %H:%M")[0:6])
#			endTime = datetime.datetime(*time.strptime( ' '.join((object.options['date_end'], object.options['time_end'])) , "%Y-%m-%d %H:%M")[0:6])
#			if int(object.options.get('iterationDays')) != 0:
#					iterationEnd = datetime.datetime(*time.strptime( object.options['iterationEnd']+" 23:59:59" , "%Y-%m-%d %H:%M:%S")[0:6])
#				else:
#					iterationEnd = "0000-00-00 00:00:00"
#
#			for reservation in reservation_list:
#				if str(reservation.id) == reservationID:
#					break
#				#sameroom = False
#				#samegroup = False
#				#sameday = False
#				usergroup = grp.getgrnam(object.options['groupname'])[2]
#				hostgroup = grp.getgrnam(object.options['roomname'])[2]
#				if reservation.hostgroup != hostgroup and reservation.usergroup != usergroup:
#					continue
#				startDate = reservation.startTime.date()
#				if reservation.iterationDays != 0:
#					iterationEndDate = reservation.iterationEnd.date()
#					if startDate2 > iterationEndDate:
#						continue
#					runDate = copy.copy(startDate)
#					runDate2 = copy.copy(startDate2)
#					if runDate2 > runDate:
#						iterationDays = datetime.timedelta(days= reservation.iterationDays)
#						while startDate2 > runDate:
#							runDate += iterationDays
#					elif int(object.options['iterationDays']) != 0:
#						iterationEndDate2 = iterationEnd.date()
#						if runDate > iterationEndDate2:
#							continue
#						iterationDays2 = datetime.timedelta(days= int(object.options['iterationDays']))
#						while runDate > runDate2:
#							runDate2 += iterationDays2
#					if runDate != runDate2:
#						continue
#				elif int(object.options['iterationDays']) != 0:
#					iterationEndDate2 = iterationEnd.date()
#					if reservation.startTime > iterationEndDate2:
#						continue
#					iterationDays2 = datetime.timedelta(days= int(object.options['iterationDays']))
#					runDate = startDate
#					runDate2 = copy.copy(startDate2)
#					while runDate > runDate2:
#						runDate2 += iterationDays2
#					if runDate != runDate2:
#						continue
#				else:
#					if startDate != startDate2:
#						continue
#				if startTime2 > reservation.endTime or\
#				   endTime2 < reservation.startTime:
#					continue
#				### all criteria match: collision
#				collision = reservation
#				#debugmsg( ud.ADMIN, ud.INFO, 'collision: %s' % collision)
#				break
#			# collision handling
#			if collision:
#				if adhoc:
#					if collision.iterationDays == 0:
#						debugmsg( ud.ADMIN, ud.INFO, 'collision: removing %s' % collision.id)
#						collision.delete()
#					else:
#						debugmsg( ud.ADMIN, ud.INFO, 'collision: overriding %s' % collision.id)
#				else:
#					#order = ('reservationID', 'reservation_name', 'description', 'date_start', 'time_begin', 'time_end', 'hostgroup', 'usergroup')
#					colliding_date_start = reservation.startTime.strftime("%Y-%m-%d")
#					colliding_time_begin = reservation.startTime.strftime("%H:%M")
#					colliding_time_end = reservation.endTime.strftime("%H:%M")
#					collisiondata = [ str(reservation.id), reservation.name, reservation.description,
#						colliding_date_start, colliding_time_begin,
#						colliding_time_end,
#						reservation.hostgroup, reservation.usergroup ]
#					p = reservationdb.Profile.get(reservation.resprofileID)
#					if p:
#						collisiondata.append(p.name)
#					else:
#						collisiondata.append(reservation.resprofileID)
#					debugmsg( ud.ADMIN, ud.INFO, 'collision: %s' % collisiondata)
#					self.finished( object.id(), collisiondata, success = False )
#					return
#
#
#			# ok we have the necessary data for a valid reservation
#			object.options['ownername'] = self._username
#
#			if 'action' in object.options:
#				del object.options['action']		# clear action flag
#			if 'files' in object.options:
#				for entry in object.options['files']:
#					tmpfname = entry.get('tmpfname')
#					if tmpfname:			# A fresh upload
#						del entry['tmpfname']
#						# TODO: save file
#						# TODO: get 'distributionID'
#						# TODO: set object.options['distributionID']
#			r = None
#			if reservationID:
#				r = reservationdb.Reservation.get( reservationID )
#			if not r:
#				r = reservationdb.Reservation()
#
#			settingsDict = reservationdb.getSettingsDict(filter='reservation')
#			for key in object.options:
#				if key == 'internetfilter' and object.options['internetfilter'] == 'default':
#					continue
#				if key in reservationdb.Reservation.ROWS and key != 'reservationID':	# filter
#					setattr(r, key, object.options[key])
#				elif key in settingsDict:		# filter
#					o = r.relateToSetting( settingsDict[key] )
#					if o.value != object.options[key]:
#						o.value = object.options[key]
#			r.name = object.options['reservation_name']
#			# encode the dates into Iso format
#			r.startTime = startTime
#			r.endTime = endTime
#			r.iterationEnd = iterationEnd
#			r.save()
#			for o in r.options:
#				o.save()
#
#		#umc.registry.load()
#		#keylist = umc.registry.keys()
#
#		self.finished( object.id(), None, success = True )

	def reservation_remove( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'reservation_remove: options=%s' % object.options )
		confirmed = object.options.get('confirmed')
		reservationID = object.options.get('reservationID')

		message = []
		reservationdata = []
		if reservationID:
			r = reservationdb.Reservation.get( reservationID )
			if confirmed:
				if r:
					r.deleteFlag = True
					r.updateDeleteFlag()
					self._debug( ud.INFO, 'tagged reservation %s for deletion' % reservationID )
			else:
			#order = ('reservationID', 'description', 'date_start', 'time_begin', 'time_end', 'hostgroup', 'usergroup')
				if r:
					remove_date_start = r.startTime.strftime("%Y-%m-%d")
					remove_time_begin = r.startTime.strftime("%H:%M")
					remove_time_end = r.endTime.strftime("%H:%M")
					try:
						roomname = grp.getgrgid(r.hostgroup)[0]
					except KeyError:
						roomname = ''
					try:
						groupname = grp.getgrgid(r.usergroup)[0]
					except KeyError:
						groupname = '%s-' % object.options['ou']
					reservationdata = [ str(r.id), r.name, r.description,
						remove_date_start, remove_time_begin,
						remove_time_end,
						roomname, groupname ]
					p = reservationdb.Profile.get(r.resprofileID)
					if p:
						reservationdata.append( str(p.name) )
					else:
						reservationdata.append( str(r.resprofileID) )

		self.finished( object.id(), (len(message)==0, message, reservationdata) )

	def reservation_profile_list( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'profile_list: options=%s' % object.options )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)
		#opts = _types.defaults.merge(object.options, 'reservation_profile_list')

		action = object.options.get('action')
		if action:
			if action == 'search':
				key = object.options['key']
				searchfilter = self._convert_filter_syntax( object.options['searchfilter'] )
				self._debug( ud.INFO, 'searchfilter=%s' % searchfilter )
				regex = re.compile(searchfilter, re.I)

		#for ou in self.ldap_anon.availableOU:
		#	self.ldap_anon.switch_ou(ou)
		#	(tmpgroupdict, tmpcomputerdict) = self._get_groups_and_computers( self.ldap_anon.searchbaseComputers, self.ldap_anon.searchbaseRooms )
		#	groupdict.update(tmpgroupdict)
		#	computerdict.update(tmpcomputerdict)

		profile_list = reservationdb.getProfilesList()

		searchresult = []
		if action == 'search':
			# get all items matching to regex
			for profile in profile_list:
				try:
					ownername = pwd.getpwuid(profile.owner)[0]
				except KeyError:
					ownername = 'uidNumber=%s' % profile.owner
					self._debug( ud.WARN, 'cannot find realname for uidNumber=%s' % profile.owner )
				except TypeError:
					self._debug( ud.ERROR, 'DATABASE ERROR: profile.owner=%s is no integer!' % profile.owner )
					ownername = "DATABASE-ERROR"

				if key == 'ownername':
					value = ownername
				elif key == 'profile_name':
					value = profile.name
				else:
					value = str(getattr(profile, key, '') or '')
				if value and regex.search(value):
					l = [ str(profile.resprofileID), profile.name, profile.description, ownername, profile.isglobaldefault ]
					searchresult.append(l)
			#self._debug( ud.INFO, 'searchresult_filtered=%s' % searchresult )
		else:
			# default: get all items owend by user or admin
			for profile in profile_list:
				if profile.owner in ( self._uid, _types.AdminUserUID) :
					ownername = pwd.getpwuid(profile.owner)[0]
					l = [ str(profile.resprofileID), profile.name, profile.description, ownername, profile.isglobaldefault ]
					searchresult.append(l)

		self.finished( object.id(), ( searchresult ) )

	def reservation_profile_edit( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'profile_edit: options=%s' % object.options )

		resprofileID = object.options.get('resprofileID')
		#opts = _types.defaults.merge(object.options, 'reservation_profile_edit')
		if resprofileID:
			p = reservationdb.Profile.get(int(resprofileID))
			if p:
				object.options['resprofileID'] = str(p.id)
				object.options['profile_name'] = p.name
				object.options['ownername'] = pwd.getpwuid(p.owner)[0]
				for key in ['description', 'isglobaldefault']:
					object.options[key] = str( getattr(p, key, '') or '' )
				for o in p.options:
					if o.setting.id:	# safty check, db consistent?
						object.options[o.setting.name] = o.value

		action = object.options.get('action')
		if action:
			del object.options['action']		# clear action flag, otherwise it ends up as an option in the profile
			if action == 'copy':
				del object.options['resprofileID']	# clear ID to flag 'new profile'
				del object.options['isglobaldefault']
				object.options['profile_name'] = _('Copy of')+ ' ' + object.options.get('profile_name')

		self.finished( object.id(), () )


	def reservation_profile_write( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'profile_write: options=%s' % object.options )

		## reset edit defaults, otherwise 'description' ends up with 'None'
		opts = _types.defaults.merge(object.options, 'reservation_profile_edit')

		profile_name = opts.get('profile_name')
		if profile_name:
			resprofileID = opts.get('resprofileID')
			p = None
			if resprofileID:
				p_old = reservationdb.Profile.get(int(resprofileID))
				if p_old.owner != self._uid:	# copy from other user
					resprofileID = None
					del opts['resprofileID']
					p = reservationdb.Profile()
					p.description = p_old.description
					p.owner = self._uid
					p.isglobaldefault = 0
				else:
					p = p_old
			if not p:
				p = reservationdb.Profile()

			# write the object
			if 'action' in object.options:
				del object.options['action']		# clear action flag

			settingsDict = reservationdb.getSettingsDict(filter='profile')
			for key in opts:
				## passthrough values
				if key in reservationdb.Profile.ROWS and key != 'resprofileID':
					setattr(p, key, object.options[key])
				elif key in settingsDict:
					o = p.relateToSetting( settingsDict[key] )
					if o.value != object.options[key]:
						o.value = object.options[key]
			## translated values
			p.name = object.options['profile_name']
			p.owner = self._uid
			p.isglobaldefault = 0
			p.save()
			for o in p.options:
				o.save()

		self.finished( object.id(), () )

	def reservation_profile_remove( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'profile_remove: options=%s' % object.options )
		confirmed = object.options.get('confirmed')
		resprofileID = object.options.get('resprofileID')

		message = []
		profiledata = []
		if resprofileID:
			p = reservationdb.Profile.get(int(resprofileID))
			if confirmed:
				if p:
					if p.isglobaldefault:
						debugmsg( ud.ADMIN, ud.ERROR, 'profile_remove: called on standard profile, refusing operation')
					else:
						p.delete()
						self._debug( ud.INFO, 'removed %s' % resprofileID )
			else:
				if p:
					profiledata = [ p.name, str(getattr(p, 'description', '') or '') ]
					if p.isglobaldefault:
						debugmsg( ud.ADMIN, ud.ERROR, 'profile_remove: called on standard profile, refusing operation')
						# FIXME
						return

		self.finished( object.id(), (len(message)==0, message, profiledata) )

	def reservation_lessontimes_edit( self, object ):
		debugmsg( ud.ADMIN, ud.INFO, 'lessontimes_edit: options=%s' % object.options )
		message = ''
		lessontimes = reservationdb.getLessontimesList()

		#opts = _types.defaults.merge(object.options, 'reservation_lessontimes_edit')
		action = object.options.get('action')
		if not action:
			object.options[ 'lessontimes' ] = []
			for lt in lessontimes:
				startDatetime = _types.baseDatetime + lt.startTime
				endDatetime = _types.baseDatetime + lt.endTime
				object.options[ 'lessontimes' ].append( {
					#'lessonID' = str(lt.id),
					'lessontime_name': lt.name,
					'description': lt.description,
					'startTime': startDatetime.strftime("%H:%M"),
					'endTime': endDatetime.strftime("%H:%M")
					} )
		else:
			del object.options['action']		# clear action flag
			if action == 'write':
				# convert strings to timedelta objects, which are what MySQLdb makes from TIME objects
				new_lessonDatetimes = []
				for line in object.options[ 'lessontimes' ]:
					lessontime_name = line['lessontime_name']
					description = line['description']
					startDatetime = datetime.datetime( *time.strptime( line['startTime'], "%H:%M")[0:5])
					endDatetime = datetime.datetime( *time.strptime( line['endTime'], "%H:%M")[0:5])
					# convert back to timedelta
					startTimedelta = startDatetime - _types.baseDatetime
					endTimedelta = endDatetime - _types.baseDatetime
					new_lessonDatetimes.append( (lessontime_name, description, startTimedelta, endTimedelta) )
				# sort list for overlap-check
				new_lessonDatetimes = sorted( new_lessonDatetimes, key = operator.itemgetter(2) )
				endTimedelta = None
				name1 = ''
				for entry in new_lessonDatetimes:
					if endTimedelta and entry[2] <= endTimedelta:
							message = _("Lesson '%s' and '%s' overlap, please correct") % (name1, entry[0])
							break
					else:
						endTimedelta = entry[3]
						name1 = entry[0]

				if not message:
					# overlap-check fine, save to lessontimes
					for entry in new_lessonDatetimes:
						target_lt = None
						for old_lt in lessontimes:
							if entry[0] == old_lt.name: # look for name
								target_lt = old_lt
								break
							elif entry[2] == old_lt.startTime: # else look for startTime
								target_lt = old_lt
								break
						if not target_lt:
							target_lt = reservationdb.Lessontime()
						else:
							lessontimes.remove(target_lt)	# remove from todo-list
						target_lt.name = entry[0]
						target_lt.description = entry[1]
						target_lt.startTime = entry[2]
						target_lt.endTime = entry[3]
						target_lt.save()
					for old_lt in lessontimes:	# clean up leftovers
						old_lt.delete()

					message = _('Lessontime Definitions Saved')

		self.finished( object.id(), (message) )


