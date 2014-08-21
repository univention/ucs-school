#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
#
# Copyright 2012-2014 Univention GmbH
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
import re
import shlex
import signal
import subprocess
import fcntl
from random import Random
import urlparse
import psutil
from ipaddr import IPAddress
from ldap.filter import escape_filter_chars

from univention.management.console.config import ucr
ucr.load()

from univention.config_registry import handler_set, handler_unset
from univention.lib.i18n import Translation
import univention.lib.atjobs as atjobs

from univention.management.console.modules.sanitizers import ListSanitizer, Sanitizer
from univention.management.console.modules.decorators import sanitize, simple_response
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
from ucsschool.lib.models import School

#import univention.management.console.modules.schoolexam.util as exam_util

from italc2 import ITALC_Manager, ITALC_Error

from notifier.nf_qt import _exit

_ = Translation('ucs-school-umc-computerroom').translate

ROOMDIR = '/var/cache/ucs-school-umc-computerroom'


def _getRoomFile(roomDN):
	if roomDN.startswith('cn='):
		dnParts = explodeDn(roomDN, True)
		if not dnParts:
			MODULE.warn('Could not split room DN: %s' % roomDN)
			raise UMC_CommandError(_('Invalid room DN: %s') % roomDN)
		return os.path.join(ROOMDIR, dnParts[0])
	return os.path.join(ROOMDIR, roomDN)


def _isUmcProcess(pid):
	if not psutil.pid_exists(pid):
		# process is not running anymore
		return False
	else:
		# process is running
		cmdline = psutil.Process(pid).cmdline
		if 'computerroom' not in cmdline or not any('univention-management-console-module' in l for l in cmdline):
			# the process is not the computerroom UMC module
			return False
	return True


def _readRoomInfo(roomDN):
	'''returns a dict of properties for the current room.'''
	roomFile = _getRoomFile(roomDN)
	info = None
	if os.path.exists(roomFile):
		try:
			with open(roomFile) as f:
				# the room file contains key-value pairs, separated by '='
				# ... parse the file as dict
				lines = f.readlines()
				info = dict([iline.strip().split('=', 1) for iline in lines if '=' in iline])
		except (OSError, IOError, ValueError) as exc:
			MODULE.warn('Failed to read file %s: %s' % (roomFile, exc))

	# special handling for the PID
	if isinstance(info, dict) and 'pid' in info:
		try:
			# translate PID to int and verify that it is a UMC process
			pid = int(info.pop('pid'))
			if _isUmcProcess(pid):
				info['pid'] = pid

		except (ValueError, OverflowError):
			# invalid format, do nothing
			pass

	return info


def _updateRoomInfo(roomDN, **kwargs):
	'''Update infos for a room, i.e., leave unspecified values untouched.'''
	info = _readRoomInfo(roomDN) or dict()
	newKwargs = dict()
	for key in ('user', 'cmd', 'exam', 'examDescription', 'examEndTime'):
		if key in kwargs:
			# set the specified value (can also be None for deleting the attribute)
			newKwargs[key] = kwargs[key]
		else:
			# leave the original value
			newKwargs[key] = info.get(key)
	_writeRoomInfo(roomDN, **newKwargs)


def _writeRoomInfo(roomDN, user=None, cmd=None, exam=None, examDescription=None, examEndTime=None):
	'''Set infos for a room and lock the room.'''
	info = dict(room=roomDN, user=user, cmd=cmd, exam=exam, examDescription=examDescription, examEndTime=examEndTime, pid=os.getpid())
	MODULE.info('Writing info file for room "%s": %s' % (roomDN, info))
	fd = None
	try:
		# write user DN in the room file
		fd = open(_getRoomFile(roomDN), 'w')
		fcntl.lockf(fd, fcntl.LOCK_EX)
		for key, val in info.iteritems():
			if val is not None:
				fd.write('%s=%s\n' % (key, val))
	except (OSError, IOError):
		MODULE.warn('Failed to write file: %s' % _getRoomFile(roomDN))
	finally:
		# make sure that the file is unlocked
		if fd:
			fcntl.lockf(fd, fcntl.LOCK_UN)
			fd.close()


def _getRoomOwner(roomDN):
	'''Read the room lock file and return the saved user DN. If it does not exist, return None.'''
	info = _readRoomInfo(roomDN) or dict()
	if not 'pid' in info :
		return None
	return info.get('user')


def _freeRoom(roomDN, userDN):
	'''Remove the lock file if the room is locked by the given user'''
	roomFile = _getRoomFile(roomDN)
	MODULE.warn('lockDN: %s, userDN: %s' % (_getRoomOwner(roomDN), userDN))
	if _getRoomOwner(roomDN) == userDN:
		try:
			os.unlink(roomFile)
		except (OSError, IOError):
			MODULE.warn('Failed to remove room lock file: %s' % roomFile)


def check_room_access(func):
	"""Block access to session from other users"""
	def _decorated(self, request):
		self._checkRoomAccess()
		return func(self, request)
	return _decorated


def get_computer(func):
	"""Adds the ITALC_Computer instance given in request.options['computer'] as parameter"""
	def _decorated(self, request):
		self.required_options(request, 'computer')
		computer = self._italc.get(request.options['computer'], None)
		if not computer:
			raise UMC_CommandError('Unknown computer')
		return func(self, request, computer)
	return _decorated


def prevent_ucc(func):
	"""Prevent method from being called for UCC clients"""
	def _decorated(self, request, computer):
		if computer.objectType == 'computers/ucc':
			MODULE.warn('Requested unavailable action (%s) for UCC client' % (func.__name__))
			raise UMC_CommandError(_('Action unavailable for UCC clients.'))
		return func(self, request, computer)
	return _decorated


class IPAddressSanitizer(Sanitizer):
	def _sanitize(self, value, name, further_fields):
		try:
			return IPAddress(value)
		except ValueError as exc:
			self.raise_validation_error('%s' % (exc,))


class Instance(SchoolBaseModule):
	ATJOB_KEY = 'UMC-computerroom'

	def init(self):
		SchoolBaseModule.init(self)
		self._italc = ITALC_Manager(self._username, self._password)
		self._random = Random()
		self._random.seed()
		self._lessons = SchoolLessons()
		self._ruleEndAt = None

	def destroy(self):
		'''Remove lock file when UMC module exists'''
		MODULE.info('Cleaning up')
		if self._italc.room:
			# do not remove lock file during exam mode
			info = _readRoomInfo(self._italc.roomDN) or dict()
			MODULE.info('room info: %s' % info)
			if info and not info.get('exam'):
				MODULE.info('Removing lock file for room %s (%s)' % (self._italc.room, self._italc.roomDN))
				_freeRoom(self._italc.roomDN, self._user_dn)
		_exit(0)

	def lessons(self, request):
		"""Returns a list of school lessons. Lessons in the past are filtered out"""
		current = self._lessons.current
		if current is None:
			current = self._lessons.previous

		if current:
			lessons = filter(lambda x: x.begin >= current.begin, self._lessons.lessons)
		else:
			lessons = self._lessons.lessons
		self.finished(request.id, map(lambda x: x.name, lessons))

	def internetrules(self, request):
		"""Returns a list of available internet rules"""
		self.finished(request.id, map(lambda x: x.name, internetrules.list()))

	@LDAP_Connection()
	def room_acquire(self, request, ldap_user_read = None, ldap_position = None, search_base = None):
		"""Acquires the specified computerroom:
		requests.options = { 'room': <roomDN> }
		"""
		self.required_options(request, 'room')

		roomDN = request.options.get('room')

		success = True
		message = 'OK'

		def _finished():
			info = dict()
			if success:
				info = _readRoomInfo(roomDN)
			self.finished(request.id, dict(
				success=success,
				message=message,
				info=dict(
					exam=info.get('exam'),
					examDescription=info.get('examDescription'),
					examEndTime=info.get('examEndTime'),
					room=info.get('room'),
					user=info.get('user'),
				)
			))

		# match the corresponding school OU
		school = None
		for ischool in School.get_all(ldap_user_read):
			pattern = re.compile('.*%s$' % (re.escape(ischool.dn)), re.I)
			if pattern.match(roomDN):
				school = ischool.name
				break
		else:
			# no match found
			MODULE.error('Failed to find corresponding school OU for room "%s" in list of schools (%s)' % (roomDN, search_base.availableSchools))
			success = False
			message = 'WRONG_SCHOOL'
			_finished()

		# set room and school
		if self._italc.school != school:
			self._italc.school = school
		if self._italc.room != request.options['room']:
			try:
				self._italc.room = request.options['room']
			except ITALC_Error:
				success = False
				message = 'EMPTY_ROOM'

		# update the room info file
		if success:
			_updateRoomInfo(roomDN, user=self._user_dn)
			if not _getRoomOwner(roomDN) == self._user_dn:
				success = False
				message = 'ALREADY_LOCKED'

		_finished()

	@LDAP_Connection()
	def rooms(self, request, ldap_user_read = None, ldap_position = None, search_base = None):
		"""Returns a list of all available rooms"""
		self.required_options(request, 'school')
		rooms = []
		userModule = udm_modules.get('users/user')
		# create search base for current school
		for iroom in self._groups(ldap_user_read, search_base.school, search_base.rooms):
			# add room status information
			roomInfo = _readRoomInfo(iroom['id']) or dict()
			userDN = roomInfo.get('user')
			if userDN and userDN != self._user_dn and ('pid' in roomInfo or 'exam' in roomInfo):
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
					MODULE.warn('Cannot open LDAP information for user "%s": %s' % (userDN, e))
			else:
				# the room is not locked :)
				iroom['locked'] = False

			# check for exam mode
			iroom['exam'] = roomInfo.get('exam')
			iroom['examDescription'] = roomInfo.get('examDescription')
			iroom['examEndTime'] = roomInfo.get('examEndTime')

			rooms.append(iroom)

		self.finished(request.id, rooms)

	@sanitize(ipaddress=ListSanitizer(required=True, sanitizer=IPAddressSanitizer(), min_elements=1, max_elements=10))
	@LDAP_Connection()
	def guess_room(self, request, ldap_user_read=None, ldap_position=None, search_base=None):
		ipaddress = request.options['ipaddress']
		self.finished(request.id, self._guess_room(ipaddress, ldap_user_read, search_base))

	def _guess_room(self, ipaddress, lo, search_base):
		host_filter = self._get_host_filter(ipaddress)
		computers = lo.searchDn(host_filter)
		if computers:
			room_filter = self._get_room_filter(computers)
			rooms = lo.searchDn(room_filter)

			for school in search_base.allSchoolBases:
				for roomdn in rooms:
					if school.isRoom(roomdn):
						return dict(
							room=roomdn,
							school=school.getOU(roomdn)
						)
		return dict(school=None, room=None)

	def _get_room_filter(self, computers):
		return '(|(%s))' % ')('.join('uniqueMember=%s' % (escape_filter_chars(computer),) for computer in computers)

	def _get_host_filter(self, ipaddresses):
		records = {4: 'aRecord=%s', 6: 'aAAARecord=%s'}
		return '(|(%s))' % ')('.join(records[ipaddress.version] % (ipaddress.exploded,) for ipaddress in ipaddresses)

	def _checkRoomAccess(self):
		if not self._italc.room:
			# no room has been selected so far
			return

		# make sure that we run the current room session
		userDN = _getRoomOwner(self._italc.roomDN)
		if userDN and userDN != self._user_dn:
			raise UMC_CommandError(_('A different user is already running a computerroom session.'))

	@LDAP_Connection()
	def query(self, request, search_base = None, ldap_user_read = None, ldap_position = None):
		"""Searches for entries. This is not allowed if the room could not be acquired.

		requests.options = {}
		  'school'
		  'room' -- DN of the selected room

		return: [{ '$dn$' : <LDAP DN>, 'name': '...', 'description': '...' }, ...]
		"""
		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError('no room selected')

		if request.options.get('reload', False):
			self._italc.room = self._italc.room # believe me that makes sense :)

		result = [computer.dict for computer in self._italc.values()]
		result.sort(key=lambda c: c['id'])

		MODULE.info('computerroom.query: result: %s' % str(result))
		self.finished(request.id, result)

	@LDAP_Connection()
	def update(self, request, search_base = None, ldap_user_read = None, ldap_position = None):
		"""Returns an update for the computers in the selected
		room. Just attributes that have changed since the last call will
		be included in the result

		requests.options = [<ID>, ...]

		return: [{ 'id' : <unique identifier>, 'states' : <display name>, 'color' : <name of favorite color> }, ...]
		"""

		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError('no room selected')

		computers = [computer.dict for computer in self._italc.values() if computer.hasChanged]
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
				MODULE.warn('Cannot open LDAP information for user "%s": %s' % (userDN, e))

		# settings info
		if self._ruleEndAt is not None:
			diff = self._positiveTimeDiff()
			if diff is not None:
				result['settingEndsIn'] = diff.seconds / 60

		MODULE.info('Update: result: %s' % str(result))
		self.finished(request.id, result)

	def _positiveTimeDiff(self):
		now = datetime.datetime.now()
		end = datetime.datetime.now()
		end = end.replace(hour = self._ruleEndAt.hour, minute = self._ruleEndAt.minute)
		if now > end:
			return None
		return end - now

	@check_room_access
	@get_computer
	def lock(self, request, computer):
		"""Returns the objects for the given IDs

		requests.options = { 'computer' : <computer name>, 'device' : (screen|input), 'lock' : <boolean or string> }

		return: { 'success' : True|False, ['details' : <message>] }
		"""

		self.required_options(request, 'device', 'lock')
		device = request.options['device']
		if device not in ('screen', 'input'):
			raise UMC_OptionTypeError('unknown device %s' % device)

		MODULE.warn('Locking device %s' % device)
		if device == 'screen':
			computer.lockScreen(request.options['lock'])
		else:
			computer.lockInput(request.options['lock'])
		self.finished(request.id, { 'success' : True, 'details' : '' })

	@check_room_access
	@get_computer
	@prevent_ucc
	def screenshot(self, request, computer):
		"""Returns a JPEG image containing a screenshot of the given
		computer. The computer must be in the current room

		requests.options = { 'computer' : <computer name>[, 'size' : (thumbnail|...)] }

		return (MIME-type image/jpeg): screenshot
		"""

		tmpfile = computer.screenshot
		if tmpfile is None:
			# vnc has not (yet) received any screenshots from the computer
			# dont worry, try again later
			self.finished(request.id, None)
			return
		response = Response(mime_type = MIMETYPE_JPEG)
		response.id = request.id
		response.command = 'COMMAND'
		with open(tmpfile.name, 'rb') as fd:
			response.body = fd.read()
		os.unlink(tmpfile.name)
		self.finished(request.id, response)

	@check_room_access
	@get_computer
	def vnc(self, request, computer):
		"""
		Returns a ultraVNC file for the given computer. The computer must be in the current room

		requests.options = { 'computer' : <computer name> }

		return  (MIME-type application/x-vnc): vnc
		"""

		# check whether VNC is enabled
		if ucr.is_false('ucsschool/umc/computerroom/ultravnc/enabled', True):
			self.finished(request.id, 'VNC is disabled')

		try:
			with open('/usr/share/ucs-school-umc-computerroom/ultravnc.vnc', 'rb') as fd:
				content = fd.read()
		except (IOError, OSError):
			raise UMC_CommandError('VNC template file does not exists')

		port = ucr.get('ucsschool/umc/computerroom/vnc/port', '11100')
		hostname = computer.ipAddress

		# Insert Hostname and Port
		content = content.replace('@%@HOSTNAME@%@', hostname).replace('@%@PORT@%@', port)

		response = Response(mime_type = 'application/x-vnc')
		response.id = request.id
		response.command = 'COMMAND'
		response.body = content
		self.finished(request.id, response)

	def settings_get(self, request):
		"""return the current settings for a room

		requests.options = { 'server' : <computer> }

		return: [True|False)
		"""
		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError('no room selected')

		ucr.load()
		rule = ucr.get('proxy/filter/room/%s/rule' % self._italc.room, 'none')
		if rule == self._username:
			rule = 'custom'
		shareMode = ucr.get('samba/sharemode/room/%s' % self._italc.room, 'all')
		# load custom rule:
		key_prefix = 'proxy/filter/setting-user/%s/domain/whitelisted/' % self._username
		custom_rules = []
		for key in ucr:
			if key.startswith(key_prefix):
				custom_rules.append(ucr[key])

		printMode = ucr.get('samba/printmode/room/%s' % self._italc.room, 'default')
		# find AT jobs for the room and execute it to remove current settings
		jobs = atjobs.list(extended = True)
		for job in jobs:
			if job.comments.get(Instance.ATJOB_KEY, False) == self._italc.room:
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
				period = datetime.datetime.now() + datetime.timedelta(hours = 1)
				period = period.time()
		else:
			period = period.end

		if self._ruleEndAt:
			time = self._ruleEndAt.time()
			for lesson in self._lessons.lessons:
				if time == lesson.begin:
					period = lesson
					break

		self.finished(request.id, {
			'internetRule' : rule,
			'customRule' : '\n'.join(custom_rules),
			'shareMode' : shareMode,
			'printMode' : printMode,
			'period' : str(period)
			})

	@check_room_access
	def settings_set(self, request):
		"""Defines settings for a room

		requests.options = { 'server' : <computer> }

		return: [True|False]
		"""

		self.required_options(request, 'printMode', 'internetRule', 'shareMode')
		exam = request.options.get('exam')
		if not exam:
			self.required_options(request, 'period')
		if not self._italc.school or not self._italc.room:
			raise UMC_CommandError('no room selected')

		printMode = request.options['printMode']
		shareMode = request.options['shareMode']
		internetRule = request.options['internetRule']

		# if the exam description has not been specified, try to load it from the room info file
		roomInfo = _readRoomInfo(self._italc.roomDN) or dict()
		examDescription = request.options.get('examDescription', roomInfo.get('examDescription', exam))
		examEndTime = request.options.get('examEndTime', roomInfo.get('examEndTime'))

		# find AT jobs for the room and execute it to remove current settings
		jobs = atjobs.list(extended = True)
		for job in jobs:
			if job.comments.get(Instance.ATJOB_KEY, False) == self._italc.room:
				job.rm()
				subprocess.call(shlex.split(job.command))

		# for the exam mode, remove current settings before setting new ones
		if roomInfo.get('exam') and roomInfo.get('cmd'):
			MODULE.info('unsetting room settings for exam (%s): %s' % (roomInfo['exam'], roomInfo['cmd']))
			try:
				subprocess.call(shlex.split(roomInfo['cmd']))
			except (OSError, IOError):
				MODULE.warn('Failed to reinitialize current room settings: %s' %  roomInfo['cmd'])

		# local helper function that writes an exam file
		cmd = ''
		def _finished():
			self.reset_smb_connections()

			self.reload_cups()

			kwargs = dict(cmd=None, exam=None, examDescription=None, examEndTime=None)
			if exam:
				# a new exam has been indicated
				kwargs = dict(cmd=cmd, exam=exam, examDescription=examDescription, examEndTime=examEndTime)

			MODULE.info('updating room info/lock file...')
			
			_updateRoomInfo(self._italc.roomDN, user=self._user_dn, **kwargs)
			self.finished(request.id, True)

		# do we need to setup a new at job with custom settings?
		if internetRule == 'none' and shareMode == 'all' and printMode == 'default':
			self._ruleEndAt = None
			_finished()
			return

		## collect new settings
		vset = {}
		vappend = {}
		vunset = []
		vunset_now = []
		vextract = []
		hosts = self._italc.ipAddresses(students_only = True)

		# print mode
		if printMode in ('none', 'all'):
			vextract.append('samba/printmode/hosts/%s' % printMode)
			vappend[vextract[-1]] = hosts
			vextract.append('cups/printmode/hosts/%s' % printMode)
			vappend[vextract[-1]] = hosts
			vunset.append('samba/printmode/room/%s' % self._italc.room)
			vset[vunset[-1]] = printMode
		else:
			vunset_now.append('samba/printmode/room/%s' % self._italc.room)

		# share mode
		if shareMode == 'home':
			vunset.append('samba/sharemode/room/%s' % self._italc.room)
			vset[vunset[-1]] = shareMode
			vextract.append('samba/othershares/hosts/deny')
			vappend[vextract[-1]] = hosts
			vextract.append('samba/share/Marktplatz/hosts/deny')
			vappend[vextract[-1]] = hosts
		else:
			vunset_now.append('samba/sharemode/room/%s' % self._italc.room)

		# internet rule
		if internetRule != 'none':
			vextract.append('proxy/filter/room/%s/ip' % self._italc.room)
			vappend[vextract[-1]] = hosts
			if internetRule == 'custom' and 'customRule' in request.options:
				# remove old rules
				i = 1
				while True:
					var = 'proxy/filter/setting-user/%s/domain/whitelisted/%d' % (self._username, i)
					if var in ucr:
						vunset_now.append(var)
						i += 1
					else:
						break
				vunset.append('proxy/filter/room/%s/rule' % self._italc.room)
				vset[vunset[-1]] = self._username
				vset['proxy/filter/setting-user/%s/filtertype' % self._username] = 'whitelist-block'
				i = 1
				for domain in request.options.get('customRule').split('\n'):
					MODULE.info('Setting whitelist entry for domain %s' % domain)
					if not domain:
						continue
					parsed = urlparse.urlsplit(domain)
					MODULE.info('Setting whitelist entry for domain %s' % str(parsed))
					if parsed.netloc:
						vset['proxy/filter/setting-user/%s/domain/whitelisted/%d' % (self._username, i)] = parsed.netloc
						i += 1
					elif parsed.path:
						vset['proxy/filter/setting-user/%s/domain/whitelisted/%d' % (self._username, i)] = parsed.path
						i += 1
			else:
				vunset.append('proxy/filter/room/%s/rule' % self._italc.room)
				vset[vunset[-1]] = internetRule
		else:
			vunset_now.append('proxy/filter/room/%s/ip' % self._italc.room)
			vunset_now.append('proxy/filter/room/%s/rule' % self._italc.room)
		## write configuration
		# remove old values
		handler_unset(vunset_now)

		# append values
		ucr.load()
		MODULE.info('Merging UCR variables')
		for key, value in vappend.items():
			if ucr.get(key):
				old = set(ucr[key].split(' '))
				MODULE.info('Old value: %s' % old)
			else:
				old = set()
				MODULE.info('Old value empty')
			new = set(value)
			MODULE.info('New value: %s' % new)
			new = old.union(new)
			MODULE.info('Merged value of %s: %s' % (key, new))
			if not new:
				MODULE.info('Unset variable %s' % key)
				vunset.append(key)
			else:
				vset[key] = ' '.join(new)

		# Workaround for bug 30450:
		# if samba/printmode/hosts/none is not set but samba/printmode/hosts/all then all other hosts
		# are unable to print on samba shares. Solution: set empty value for .../none if no host is on deny list.
		varname = 'samba/printmode/hosts/none'
		if varname not in vset:
			ucr.load()
			if not ucr.get(varname):
				vset[varname] = '""'
		else:
			# remove empty items ('""') in list
			vset[varname] = ' '.join([x for x in vset[varname].split(' ') if x != '""'])
		if varname in vunset:
			del vunset[varname]

		# set values
		ucr_vars = sorted(map(lambda x: '%s=%s' % x, vset.items()))
		MODULE.info('Writing room rules: %s' % '\n'.join(ucr_vars))
		handler_set(ucr_vars)

		# create at job to remove settings
		unset_vars = map(lambda x: '-r "%s"' % x, vunset)
		MODULE.info('Will remove: %s' % ' '.join(unset_vars))
		extract_vars = map(lambda x: '-e "%s"' % x, vextract)
		MODULE.info('Will extract: %s' % ' '.join(extract_vars))

		cmd = '/usr/share/ucs-school-umc-computerroom/ucs-school-deactivate-rules %s %s %s' % (' '.join(unset_vars), ' '.join(extract_vars), ' '.join(hosts))
		MODULE.info('command for reinitialization is: %s' % cmd)

		if not exam:
			# AT job for the normal case
			try:
				endtime = datetime.datetime.strptime(request.options['period'], '%H:%M')
				endtime = endtime.time()
			except ValueError, e:
				raise UMC_CommandError('Failed to read end time: %s' % str(e))

			starttime = datetime.datetime.now()
			MODULE.info('Now: %s' % starttime)
			MODULE.info('Endtime: %s' % endtime)
			starttime = starttime.replace(hour = endtime.hour, minute = endtime.minute)
			MODULE.info('Remove settings at %s' % starttime)
			atjobs.add(cmd, starttime, { Instance.ATJOB_KEY: self._italc.room })
			self._ruleEndAt = starttime

		_finished()

	def reload_cups(self):
		if os.path.exists('/etc/init.d/cups'):
			MODULE.info('Reloading cups')
			if subprocess.call(['/etc/init.d/cups', 'reload']) != 0:
				MODULE.error('Failed to reload cups! Printer settings not applied.')

	def reset_smb_connections(self):
		smbstatus = SMB_Status()
		italc_users = [x.lower() for x in self._italc.users if x]
		MODULE.info('iTALC users: %s' % ', '.join(italc_users))
		for process in smbstatus:
			MODULE.info('SMB process: %s' % str(process))
			if process.username and process.username.lower() in italc_users:
				MODULE.info('Kill SMB process %s' % process.pid)
				os.kill(int(process.pid), signal.SIGTERM)

	@check_room_access
	def demo_start(self, request):
		"""Starts a demo

		requests.options = { 'server' : <computer> }

		return: [True|False)
		"""

		self.required_options(request, 'server')
		self._italc.startDemo(request.options['server'], True)
		self.finished(request.id, True)

	@check_room_access
	def demo_stop(self, request):
		"""Stops a demo

		requests.options = none

		return: [True|False)
		"""

		self._italc.stopDemo()
		self.finished(request.id, True)

	@check_room_access
	@get_computer
	def computer_state(self, request, computer):
		"""Stops, starts or restarts a computer

		requests.options = { 'computer' : <computer', 'state' : (poweroff|poweron|restart) }

		return: [True|False)
		"""

		self.required_options(request, 'state')

		state = request.options['state']
		if not state in ('poweroff', 'poweron', 'restart'):
			raise UMC_OptionTypeError('unkown state %s' % state)

		# prevent UCC
		if state != 'poweron':
			prevent = prevent_ucc(lambda self, request, computer: None)
			prevent(self, request, computer)

		if state == 'poweroff':
			computer.powerOff()
		elif state == 'poweron':
			computer.powerOn()
		elif state == 'restart':
			computer.restart()

		self.finished(request.id, True)

	@check_room_access
	@get_computer
	@prevent_ucc
	def user_logout(self, request, computer):
		"""Log out the user at the given computer

		requests.options = { 'computer' : <computer' }

		return: [True|False)
		"""

		computer.logOut()

		self.finished(request.id, True)
