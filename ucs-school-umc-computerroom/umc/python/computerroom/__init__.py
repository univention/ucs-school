#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
#
# Copyright 2012-2013 Univention GmbH
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

import datetime
import os
import shlex
import signal
import subprocess
import fcntl
from random import Random
import urlparse

from univention.management.console.config import ucr

from univention.config_registry import handler_set, handler_unset
from univention.lib.i18n import Translation
import univention.lib.atjobs as atjobs

from univention.management.console.modules import UMC_OptionTypeError, UMC_CommandError
from univention.management.console.log import MODULE
from univention.management.console.protocol import MIMETYPE_JPEG, Response

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions

from univention.uldap import explodeDn

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule, Display
from ucsschool.lib.schoollessons import SchoolLessons
from ucsschool.lib.smbstatus import SMB_Status
import ucsschool.lib.internetrules as internetrules

from italc2 import ITALC_Manager, ITALC_Error

from notifier.nf_qt import _exit

_ = Translation( 'ucs-school-umc-computerroom' ).translate

ROOMDIR = '/var/cache/ucs-school-umc-computerroom'

def _getRoomFile(roomDN):
	if roomDN.startswith( 'cn=' ):
		dnParts = explodeDn(roomDN, True)
		if not dnParts:
			MODULE.warn('Could not split room DN: %s' % roomDN)
			raise UMC_CommandError( _('Invalid room DN: %s') % roomDN )
		return os.path.join(ROOMDIR, dnParts[0])
	return os.path.join( ROOMDIR, roomDN )

def _getRoomOwner(roomDN):
	'''Read the room lock file and return the saved user DN. If it does not exist, return None.'''
	roomFile = _getRoomFile(roomDN)
	result = None
	if os.path.exists(roomFile):
		try:
			f = open(roomFile)
			result = f.readline().strip()
			f.close()
		except (OSError, IOError):
			MODULE.warn( 'Failed to acquire room lock file: %s' % roomFile )
	return result

def _setRoomOwner(roomDN, userDN):
	'''Set the owner for a room and lock the room.'''
	MODULE.info( 'Updating owner for room "%s": %s' % (roomDN, userDN) )
	fd = None
	try:
		# write user DN in the room file
		fd = open(_getRoomFile(roomDN), 'w')
		fcntl.lockf(fd, fcntl.LOCK_EX)
		fd.write(userDN)
	except (OSError, IOError):
		MODULE.warn( 'Failed to write file: %s' % _getRoomFile(roomDN) )
	finally:
		# make sure that the file is unlocked
		if fd:
			fcntl.lockf(fd, fcntl.LOCK_UN)
			fd.close()

def _freeRoom(roomDN, userDN):
	'''Remove the lock file if the room is locked by the given user'''
	roomFile = _getRoomFile(roomDN)
	MODULE.warn( 'lockDN: %s, userDN: %s' % ( _getRoomOwner( roomDN ), userDN ) )
	if _getRoomOwner( roomDN ) == userDN:
		try:
			os.unlink(roomFile)
		except (OSError, IOError):
			MODULE.warn( 'Failed to remove room lock file: %s' % roomFile )

class Instance( SchoolBaseModule ):
	ATJOB_KEY = 'UMC-computerroom'

	def init( self ):
		SchoolBaseModule.init( self )
		self._italc = ITALC_Manager( self._username, self._password )
		self._random = Random()
		self._random.seed()
		self._lessons = SchoolLessons()
		self._ruleEndAt = None

	def destroy( self ):
		'''Remove lock file when UMC module exists'''
		MODULE.info( 'Cleaning up' )
		if self._italc.room:
			MODULE.info( 'Removing lock file for room %s (%s)' % ( self._italc.room, self._italc.roomDN ) )
			_freeRoom( self._italc.roomDN, self._user_dn )
		_exit( 0 )

	def lessons( self, request ):
		"""Returns a list of school lessons. Lessons in the past are filtered out"""
		current = self._lessons.current
		if current is None:
			current = self._lessons.previous

		if current:
			lessons = filter( lambda x: x.begin >= current.begin, self._lessons.lessons )
		else:
			lessons = self._lessons.lessons
		self.finished( request.id, map( lambda x: x.name, lessons ) )

	def internetrules( self, request ):
		"""Returns a list of available internet rules"""
		self.finished( request.id, map( lambda x: x.name, internetrules.list() ) )

	def room_acquire( self, request ):
		"""Acquires the specified computerroom:
		requests.options = { 'room': <roomDN> }
		"""
		self.required_options( request, 'school', 'room' )

		roomDN = request.options.get('room')

		success = True
		message = 'OK'
		# set room and school
		if self._italc.school != request.options[ 'school' ]:
			self._italc.school = request.options[ 'school' ]
		if self._italc.room != request.options[ 'room' ]:
			try:
				self._italc.room = request.options[ 'room' ]
			except ITALC_Error:
				success = False
				message = 'EMPTY_ROOM'

		if success:
			_setRoomOwner(roomDN, self._user_dn)
			if not _getRoomOwner(roomDN) == self._user_dn:
				success = False
				message = 'ALREADY_LOCKED'
		self.finished( request.id, { 'success' : success, 'message' : message } )

	@LDAP_Connection()
	def rooms( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all available rooms"""
		self.required_options( request, 'school' )
		rooms = []
		userModule = udm_modules.get('users/user')
		# create search base for current school
		for iroom in self._groups( ldap_user_read, search_base.school, search_base.rooms ):
			# add room status information
			userDN = _getRoomOwner(iroom['id'])
			if userDN and userDN != self._user_dn:
				# the room is currently locked by another user
				iroom['locked'] = True
				try:
					# open the corresponding UDM object to get a displayable user name
					userObj = userModule.object(None, ldap_user_read, None, userDN)
					userObj.open()
					iroom['user'] = Display.user(userObj)
				except udm_exceptions.base as e:
					# something went wrong, save the user DN
					iroom['user'] = userDN
					MODULE.warn( 'Cannot open LDAP information for user "%s": %s' % (userDN, e) )
			else:
				# the room is not locked :)
				iroom['locked'] = False
			rooms.append(iroom)

		self.finished( request.id, rooms )

	def _checkRoomAccess( self ):
		if not self._italc.room:
			# no room has been selected so far
			return

		# make sure that we run the current room session
		userDN = _getRoomOwner(self._italc.roomDN)
		if userDN and userDN != self._user_dn:
			raise UMC_CommandError( _('A different user is already running a computerroom session.') )

	@LDAP_Connection()
	def query( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Searches for entries. This is not allowed if the room could not be acquired.

		requests.options = {}
		  'school'
		  'room' -- DN of the selected room

		return: [ { '$dn$' : <LDAP DN>, 'name': '...', 'description': '...' }, ... ]
		"""
		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError( 'no room selected' )

		if request.options.get( 'reload', False ):
			self._italc.room = self._italc.room # believe me that makes sense :)

		result = []
		for computer in self._italc.values():
			item = { 'id' : computer.name,
					 'name' : computer.name,
					 'user' : computer.user.current,
					 'teacher' : computer.isTeacher,
					 'connection' : computer.state.current,
					 'description' : computer.description,
					 'ip' : computer.ipAddress,
					 'mac' : computer.macAddress }
			item.update( computer.flagsDict )
			result.append( item )

		MODULE.info( 'computerroom.query: result: %s' % str( result ) )
		self.finished( request.id, result )

	@LDAP_Connection()
	def update( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Returns an update for the computers in the selected
		room. Just attributes that have changed since the last call will
		be included in the result

		requests.options = [ <ID>, ... ]

		return: [ { 'id' : <unique identifier>, 'states' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""

		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError( 'no room selected' )

		computers = []
		for computer in self._italc.values():
			item = dict( id = computer.name )
			modified = False
			if computer.state.hasChanged:
				item[ 'connection' ] = str( computer.state.current )
				modified = True
			if computer.flags.hasChanged:
				item.update( computer.flagsDict )
				modified = True
			if computer.user.hasChanged:
				item[ 'user' ] = str( computer.user.current )
				modified = True
			if computer.teacher.hasChanged:
				item[ 'teacher' ] = computer.teacher.current
				modified = True
			if modified:
				computers.append( item )
		result = { 'computers' : computers }

		userDN = _getRoomOwner(self._italc.roomDN)
		result['locked'] = False
		result['user'] = self._user_dn
		if userDN and userDN != self._user_dn:
			# somebody else acquired the room, the room is locked
			result['locked'] = True
			try:
				# open the corresponding UDM object to get a displayable user name
				userModule = udm_modules.get('users/user')
				userObj = userModule.object(None, ldap_user_read, None, userDN)
				userObj.open()
				result['user'] = Display.user(userObj)
			except udm_exceptions.base as e:
				# could not oben the LDAP object, show the DN
				result['user'] = userDN
				MODULE.warn( 'Cannot open LDAP information for user "%s": %s' % (userDN, e) )

		# settings info
		if self._ruleEndAt is not None:
			diff = self._positiveTimeDiff()
			if diff is not None:
				result[ 'settingEndsIn' ] = diff.seconds / 60

		MODULE.info( 'Update: result: %s' % str( result ) )
		self.finished( request.id, result )

	def _positiveTimeDiff( self ):
		now = datetime.datetime.now()
		end = datetime.datetime.now()
		end = end.replace( hour = self._ruleEndAt.hour, minute = self._ruleEndAt.minute )
		if now > end:
			return None
		return end - now

	def lock( self, request ):
		"""Returns the objects for the given IDs

		requests.options = { 'computer' : <computer name>, 'device' : (screen|input), 'lock' : <boolean or string> }

		return: { 'success' : True|False, [ 'details' : <message> ] }
		"""
		# block access to session from other users
		self._checkRoomAccess()

		self.required_options( request, 'computer', 'device', 'lock' )
		device = request.options[ 'device' ]
		if not device in ( 'screen', 'input' ):
			raise UMC_OptionTypeError( 'unknown device %s' % device )

		computer = self._italc.get( request.options[ 'computer' ], None )
		if computer is None:
			raise UMC_CommandError( 'Unknown computer %s' % request.options[ 'computer' ] )

		MODULE.warn( 'Locking device %s' % device )
		if device == 'screen':
			computer.lockScreen( request.options[ 'lock' ] )
		else:
			computer.lockInput( request.options[ 'lock' ] )
		self.finished( request.id, { 'success' : True, 'details' : '' } )

	def screenshot( self, request ):
		"""Returns a JPEG image containing a screenshot of the given
		computer. The computer must be in the current room

		requests.options = { 'computer' : <computer name>[, 'size' : (thumbnail|...)] }

		return (MIME-type image/jpeg): screenshot
		"""
		# block access to session from other users
		self._checkRoomAccess()

		self.required_options( request, 'computer' )
		computer = self._italc.get( request.options[ 'computer' ], None )
		if not computer:
			raise UMC_CommandError( 'Unknown computer' )

		tmpfile = computer.screenshot
		if tmpfile is None:
			# vnc has not (yet) received any screenshots from the computer
			# dont worry, try again later
			self.finished( request.id, None )
			return
		response = Response( mime_type = MIMETYPE_JPEG )
		response.id = request.id
		response.command = 'COMMAND'
		response.body = open( tmpfile.name ).read()
		os.unlink( tmpfile.name )
		self.finished( request.id, response )

	def vnc( self, request ):
		"""
		Returns a ultraVNC file for the given computer. The computer must be in the current room

		requests.options = { 'computer' : <computer name> }

		return  (MIME-type application/x-vnc): vnc
		"""
		# block access to session from other users
		self._checkRoomAccess()

		# check whether VNC is enabled
		if ucr.is_false('ucsschool/umc/computerroom/ultravnc/enabled', True):
			self.finished( request.id, 'VNC is disabled' )

		# Check if computer exists
		self.required_options( request, 'computer' )
		computer = self._italc.get( request.options[ 'computer' ], None )
		if not computer:
			raise UMC_CommandError( 'Unknown computer' )

		try:
			template = open('/usr/share/ucs-school-umc-computerroom/ultravnc.vnc')
			content = template.read()
		except:
			raise UMC_CommandError( 'VNC template file does not exists' )

		port = ucr.get('ucsschool/umc/computerroom/vnc/port', '11100')
		hostname = computer.ipAddress

		# Insert Hostname and Port
		content = content.replace('@%@HOSTNAME@%@', hostname).replace('@%@PORT@%@', port)

		response = Response( mime_type = 'application/x-vnc' )
		response.id = request.id
		response.command = 'COMMAND'
		response.body = content
		self.finished( request.id, response )

	def settings_get( self, request ):
		"""return the current settings for a room

		requests.options = { 'server' : <computer> }

		return: [True|False)
		"""
		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError( 'no room selected' )

		rule = ucr.get( 'proxy/filter/room/%s/rule' % self._italc.room, 'none' )
		if rule == self._username:
			rule = 'custom'
		shareMode = ucr.get( 'samba/sharemode/room/%s' % self._italc.room, 'all' )
		# load custom rule:
		key_prefix = 'proxy/filter/setting-user/%s/domain/whitelisted/' % self._username
		custom_rules = []
		for key in ucr:
			if key.startswith( key_prefix ):
				custom_rules.append( ucr[ key ] )

		printMode = ucr.get( 'samba/printmode/room/%s' % self._italc.room, 'default' )
		# find AT jobs for the room and execute it to remove current settings
		jobs = atjobs.list( extended = True )
		for job in jobs:
			if Instance.ATJOB_KEY in job.comments and job.comments[ Instance.ATJOB_KEY ] == self._italc.room:
				if job.execTime >= datetime.datetime.now():
					self._ruleEndAt = job.execTime
				break
		else:
			self._ruleEndAt = None

		if rule == 'none' and shareMode == 'all' and printMode == 'default':
			self._ruleEndAt = None

		# find end of lesson
		period = self._lessons.current
		if period is None:
			if self._lessons.next: # between two lessons
				period = self._lessons.next.end
			else: # school is out ... 1 hour should be good (FIXME: configurable?)
				period = datetime.datetime.now() + datetime.timedelta( hours = 1 )
				period = period.time()
		else:
			period = period.end

		if self._ruleEndAt:
			time = self._ruleEndAt.time()
			for lesson in self._lessons.lessons:
				if time == lesson.begin:
					period = lesson
					break

		self.finished( request.id, {
			'internetRule' : rule,
			'customRule' : '\n'.join( custom_rules ),
			'shareMode' : shareMode,
			'printMode' : printMode,
			'period' : str( period )
			} )

	def settings_set( self, request ):
		"""Defines settings for a room

		requests.options = { 'server' : <computer> }

		return: [True|False)
		"""
		# block access to session from other users
		self._checkRoomAccess()

		self.required_options( request, 'printMode', 'internetRule', 'shareMode', 'period' )
		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError( 'no room selected' )

		# find AT jobs for the room and execute it to remove current settings
		jobs = atjobs.list( extended = True )
		for job in jobs:
			if Instance.ATJOB_KEY in job.comments and job.comments[ Instance.ATJOB_KEY ] == self._italc.room:
				job.rm()
				subprocess.call( shlex.split( job.command ) )
				break

		# do we need to setup a new at job with custom settings?
		if request.options[ 'internetRule' ] == 'none' and request.options[ 'shareMode' ] == 'all' and request.options[ 'printMode' ] == 'default':
			self._ruleEndAt = None
			self.finished( request.id, True )
			return

		## collect new settings
		vset = {}
		vappend = {}
		vunset = []
		vunset_now = []
		vextract = []
		hosts = self._italc.ipAddresses( students_only = True )

		# print mode
		if request.options[ 'printMode' ] in ( 'none', 'all' ):
			vextract.append( 'samba/printmode/hosts/%s' % request.options[ 'printMode' ] )
			vappend[ vextract[ -1 ] ] = hosts
			vunset.append( 'samba/printmode/room/%s' % self._italc.room )
			vset[ vunset[ -1 ] ] = request.options[ 'printMode' ]
		else:
			vunset_now.append( 'samba/printmode/room/%s' % self._italc.room )

		# share mode
		if request.options[ 'shareMode' ] in ( 'none', 'home' ):
			vunset.append( 'samba/sharemode/room/%s' % self._italc.room )
			vset[ vunset[ -1 ] ] = request.options[ 'shareMode' ]
			vextract.append( 'samba/othershares/hosts/deny' )
			vappend[ vextract[ -1 ] ] = hosts
			vextract.append( 'samba/share/Marktplatz/hosts/deny' )
			vappend[ vextract[ -1 ] ] = hosts
			if request.options[ 'shareMode' ] == 'none':
				vextract.append( 'samba/share/homes/hosts/deny' )
				vappend[ vextract[ -1 ] ] = hosts
		else:
			vunset_now.append( 'samba/sharemode/room/%s' % self._italc.room )

		# internet rule
		if request.options[ 'internetRule' ] != 'none':
			vextract.append( 'proxy/filter/room/%s/ip' % self._italc.room )
			vappend[ vextract[ -1 ] ] = hosts
			if request.options[ 'internetRule' ] == 'custom' and 'customRule' in request.options:
				# remove old rules
				i = 1
				while True:
					var = 'proxy/filter/setting-user/%s/domain/whitelisted/%d' % ( self._username, i )
					if ucr.has_key( var ):
						vunset_now.append( var )
						i += 1
					else:
						break
				vunset.append( 'proxy/filter/room/%s/rule' % self._italc.room )
				vset[ vunset[ -1 ] ] = self._username
				vset[ 'proxy/filter/setting-user/%s/filtertype' % self._username ] = 'whitelist-block'
				i = 1
				for domain in request.options.get( 'customRule' ).split( '\n' ):
					MODULE.info( 'Setting whitelist antry for domain %s' % domain )
					if not domain:
						continue
					parsed = urlparse.urlsplit( domain )
					MODULE.info( 'Setting whitelist antry for domain %s' % str( parsed ) )
					if parsed.netloc:
						vset[ 'proxy/filter/setting-user/%s/domain/whitelisted/%d' % ( self._username, i ) ] = parsed.netloc
						i += 1
					elif parsed.path:
						vset[ 'proxy/filter/setting-user/%s/domain/whitelisted/%d' % ( self._username, i ) ] = parsed.path
						i += 1
			else:
				vunset.append( 'proxy/filter/room/%s/rule' % self._italc.room )
				vset[ vunset[ -1 ] ] = request.options[ 'internetRule' ]
		else:
			vunset_now.append( 'proxy/filter/room/%s/ip' % self._italc.room )
			vunset_now.append( 'proxy/filter/room/%s/rule' % self._italc.room )
		## write configuration
		# remove old values
		handler_unset( vunset_now )

		# append values
		ucr.load()
		MODULE.info( 'Merging UCR variables' )
		for key, value in vappend.items():
			if ucr.has_key( key ) and ucr[ key ]:
				old = set( ucr[ key ].split( ' ' ) )
				MODULE.info( 'Old value: %s' % old )
			else:
				old = set()
				MODULE.info( 'Old value empty' )
			new = set( value )
			MODULE.info( 'New value: %s' % new )
			new = old.union( new )
			MODULE.info( 'Merged value of %s: %s' % ( key, new ) )
			if not new:
				MODULE.info( 'Unset variable %s' % key )
				vunset.append( key )
			else:
				vset[ key ] = ' '.join( new )

		# Workaround for bug 30450:
		# if samba/printmode/hosts/none is not set but samba/printmode/hosts/all then all other hosts
		# are unable to print on samba shares. Solution: set empty value for .../none if no host is on deny list.
		varname = 'samba/printmode/hosts/none'
		if not varname in vset:
			vset[varname] = '""'
		else:
			# remove empty items ('""') in list
			vset[varname] = ' '.join([x for x in vset[varname].split(' ') if not x == '""'])
		if varname in vunset:
			del vunset[varname]

		# set values
		ucr_vars = sorted( map( lambda x: '%s=%s' % x, vset.items() ) )
		MODULE.info( 'Writing room rules: %s' % '\n'.join( ucr_vars ) )
		handler_set( ucr_vars )

		# create at job to remove settings
		unset_vars = map( lambda x: '-r "%s"' % x, vunset )
		MODULE.info( 'Will remove: %s' % ' '.join( unset_vars ) )
		extract_vars = map( lambda x: '-e "%s"' % x, vextract )
		MODULE.info( 'Will extract: %s' % ' '.join( extract_vars ) )

		cmd = '/usr/share/ucs-school-umc-computerroom/ucs-school-deactivate-rules %s %s %s' % ( ' '.join( unset_vars ), ' '.join( extract_vars ), ' '.join( hosts ) )
		MODULE.info( 'at job command is: %s' % cmd )
		try:
			endtime = datetime.datetime.strptime( request.options[ 'period' ], '%H:%M' )
			endtime = endtime.time()
		except ValueError, e:
			raise UMC_CommandError( 'Failed to read end time: %s' % str( e ) )

		starttime = datetime.datetime.now()
		MODULE.info( 'Now: %s' % starttime )
		MODULE.info( 'Endtime: %s' % endtime )
		starttime = starttime.replace( hour = endtime.hour, minute = endtime.minute )
		MODULE.info( 'Remove settings at %s' % starttime )
		atjobs.add( cmd, starttime, { Instance.ATJOB_KEY: self._italc.room } )
		self._ruleEndAt = starttime

		# reset SMB connections
		smbstatus = SMB_Status()
		italc_users = self._italc.users
		MODULE.info( 'iTALC users: %s' % ', '.join( italc_users ) )
		for process in smbstatus:
			MODULE.info( 'SMB process: %s' % str( process ) )
			if process.username in italc_users:
				MODULE.info( 'Kill SMB process %s' % process.pid )
				os.kill( int( process.pid ), signal.SIGTERM )
		self.finished( request.id, True )

	def settings_reschedule( self, request ):
		"""Defines settings for a room

		requests.options = { 'server' : <computer> }

		return: [True|False)
		"""
		# block access to session from other users
		self._checkRoomAccess()

		self.required_options( request, 'period' )

		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError( 'no room selected' )

		# find AT jobs for the room and execute it to remove current settings
		jobs = atjobs.list( extended = True )
		for job in jobs:
			if Instance.ATJOB_KEY in job.comments and job.comments[ Instance.ATJOB_KEY ] == self._italc.room:
				current = job.execTime
				try:
					time = datetime.datetime.strptime(  request.options[ 'period' ], '%H:%M' ).time()
					current = current.replace( hour = time.hour, minute = time.minute )
					atjobs.reschedule( job.nr, current )
					MODULE.info( 'Reschedule at job %s for %s' % ( job.nr, current ) )
					self._ruleEndAt = current
				except ValueError, e:
					raise UMC_CommandError( 'Failed to read end time: %s' % str( e ) )
				break
		self.finished( request.id, True )

	def demo_start( self, request ):
		"""Starts a demo

		requests.options = { 'server' : <computer> }

		return: [True|False)
		"""
		# block access to session from other users
		self._checkRoomAccess()

		self.required_options( request, 'server' )
		self._italc.startDemo( request.options[ 'server' ], True )
		self.finished( request.id, True )

	def demo_stop( self, request ):
		"""Stops a demo

		requests.options = none

		return: [True|False)
		"""
		# block access to session from other users
		self._checkRoomAccess()

		self._italc.stopDemo()
		self.finished( request.id, True )

	def computer_state( self, request ):
		"""Stops, starts or restarts a computer

		requests.options = { 'computer' : <computer', 'state' : (poweroff|poweron|restart) }

		return: [True|False)
		"""
		# block access to session from other users
		self._checkRoomAccess()

		self.required_options( request, 'computer', 'state' )

		state = request.options[ 'state' ]
		if not state in ( 'poweroff', 'poweron', 'restart' ):
			raise UMC_OptionTypeError( 'unkown state %s' % state )

		computer = self._italc.get( request.options[ 'computer' ], None )
		if not computer:
			raise UMC_CommandError( 'Unknown computer' )

		if state == 'poweroff':
			computer.powerOff()
		elif state == 'poweron':
			computer.powerOn()
		elif state == 'restart':
			computer.restart()

		self.finished( request.id, True )

	def user_logout( self, request ):
		"""Log out the user at the given computer

		requests.options = { 'computer' : <computer' }

		return: [True|False)
		"""
		# block access to session from other users
		self._checkRoomAccess()

		self.required_options( request, 'computer' )

		computer = self._italc.get( request.options[ 'computer' ], None )
		if not computer:
			raise UMC_CommandError( 'Unknown computer' )

		computer.logOut()

		self.finished( request.id, True )

