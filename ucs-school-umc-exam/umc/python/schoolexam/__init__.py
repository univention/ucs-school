#!/usr/bin/python2.6
#
# Univention Management Console
#  Starts a new exam for a specified computer room
#
# Copyright 2013 Univention GmbH
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

import notifier

from univention.management.console.modules import Base
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, sanitize

from univention.lib.i18n import Translation

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display
import ucsschool.lib.internetrules as internetrules

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions

import univention.management.console.modules.distribution.util as distribution_util

import os
import tempfile
import shutil
import time
import traceback
from httplib import HTTPException
from socket import error as SocketError

from util import UMCConnection

udm_modules.update()

_ = Translation( 'ucs-school-umc-exam' ).translate

class Progress(object):
	def __init__(self, max_steps=100):
		self.reset(max_steps)

	def reset(self, max_steps=100):
		self._max_steps = max_steps
		self._finished = False
		self._steps = 0
		self._component = _('Initializing')
		self._info = ''
		self._errors = []

	def poll(self):
		return dict(
			finished=self._finished,
			steps=100 * float(self._steps) / self._max_steps,
			component=self._component,
			info=self._info,
			errors=self._errors,
		)

	def finish(self):
		self._finished = True

	def component(self, component):
		self._component = component

	def info(self, info):
		MODULE.process('%s - %s' % (self._component, info))
		self._info = info

	def error(self, err):
		MODULE.warn('%s - %s' % (self._component, err))
		self._errors.append(err)

	def add_steps(self, steps = 1):
		self._steps += steps

class Instance( SchoolBaseModule ):
	def __init__( self ):
		SchoolBaseModule.__init__(self)
		self._tmpDir = None
		self.progress_state = Progress()

	def init(self):
		SchoolBaseModule.init(self)
		# initiate paths for data distribution
		distribution_util.initPaths()

	def destroy(self):
		# clean temporary data
		self._cleanTmpDir()

	def _cleanTmpDir(self):
		### copied from distribution module
		# clean up the temporary upload directory
		if self._tmpDir:
			MODULE.info('Clean up temporary directory: %s' % self._tmpDir)
			shutil.rmtree(self._tmpDir, ignore_errors=True)
			self._tmpDir = None

	def upload(self, request):
		### copied from distribution module
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of dicts, but got: %s' % str(request.options) )
		file = request.options[0]
		if not ('tmpfile' in file and 'filename' in file):
			raise UMC_OptionTypeError( 'Invalid upload data, got: %s' % str(file) )

		# create a temporary upload directory, if it does not already exist
		if not self._tmpDir:
			self._tmpDir = tempfile.mkdtemp(prefix='ucsschool-exam-upload-')
			MODULE.info('Created temporary directory: %s' % self._tmpDir)

		# we got an uploaded file with the following properties:
		#   name, filename, tmpfile
		destPath = os.path.join(self._tmpDir, file['filename'])
		MODULE.info('Received file "%s", saving it to "%s"' % (file['tmpfile'], destPath))
		shutil.move(file['tmpfile'], destPath)

		# done
		self.finished( request.id, None )

	def internetrules( self, request ):
		### copied from computerroom module
		"""Returns a list of available internet rules"""
		self.finished( request.id, map( lambda x: x.name, internetrules.list() ) )

	@simple_response
	def progress(self):
		return self.progress_state.poll()

	@LDAP_Connection()
	def start_exam(self, request, ldap_user_read = None, ldap_position = None, search_base = None):
		self.required_options(request, 'recipients', 'room')

		# reset the current progress state
		# steps:
		#   5 -> for preparing exam room
		#   25 -> for cloning users
		#   25 -> for each replicated users + copy of the profile directory
		#   25 -> distribution of exam files
		progress_state = self.progress_state
		progress_state.reset(80)

		def _thread():
			# perform all actions inside a thread...
			# open a new connection to the master UMC
			ucr.load()
			username = '%s$' % ucr.get('hostname')
			password = ''
			try:
				with open('/etc/machine.secret') as machineFile:
					password = machineFile.readline().strip()
			except (OSError, IOError) as e:
				MODULE.error('Could not read /etc/machine.secret: %s' % e)
			try:
				connection = UMCConnection(ucr.get('ldap/master'))
				connection.auth(username, password)
			except (HTTPException, SocketError) as e:
				MODULE.error('Could not connect to UMC on %s: %s' % (ucr.get('ldap/master'), e))

			# read all recipients and fetch all user objects
			recipients = [ientry for ientry in [ distribution_util.openRecipients(idn, ldap_user_read, search_base) for idn in request.options.get('recipients', []) ] if ientry ]
			users = []
			for irecipient in recipients:
				# recipients can in theory be users or groups
				if isinstance(irecipient, distribution_util.User):
					users.append(irecipient)
				elif isinstance(irecipient, distribution_util.Group):
					users.extend(irecipient.members)

			# mark the computer room for exam mode
			progress_state.component(_('Preparing the computer room for exam mode...'))
			ires = connection.request('schoolexam-master/set-computerroom-exammode', dict(
				roomdn=request.options.get('room')
			))
			progress_state.add_steps(5)

			# start to clone users
			progress_state.component(_('Cloning users'))
			percentPerUser = 25.0 / len(users)
			usersCloned = set()
			usersReplicated = set()
			for iuser in users:
				progress_state.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
				try:
					ires = connection.request('schoolexam-master/create-exam-user', dict(
						userdn=iuser.dn
					))
					usersCloned.add(iuser.dn)
				except (HTTPException, SocketError) as e:
					MODULE.warn('Could not clone user: %s' % iuser.dn)

				# indicate the the user has been processed
				progress_state.add_steps(percentPerUser)

			# wait for the replication of all users to be finished
			userModul = udm_modules.get( 'users/user' )
			progress_state.component(_('Preparing home directories'))
			while len(usersCloned) > len(usersReplicated):
				MODULE.info('waiting for replication to be finished, %s objects missing' % (len(usersCloned) - len(usersReplicated)))
				for idn in usersCloned - usersReplicated:
					try:
						# try to open the user
						iobj = userModul.object( None, ldap_user_read, None, idn )
						if iobj.exists():
							MODULE.info('user has been replicated: %s' % idn)

							### TODO: COPY PROFILE DIR

							usersReplicated.add(idn)
							progress_state.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
							progress_state.add_steps(percentPerUser)
					except udm_exceptions.noObject as e:
						# access failed
						pass
					except LDAP_ConnectionError as e:
						MODULE.error('Could not open object DN: %s (%s)' % (entryDN, e))

				# wait a second
				time.sleep(1)

			# distribute exam files
			progress_state.component(_('Distributing exam files'))
			progress_state.info('')
			time.sleep(2)
			progress_state.add_steps(25)

		def _finished(thread, result):
			# mark the progress state as finished
			progress_state.info(_('finished...'))
			progress_state.finish()

			# finish the request at the end in order to force the module to keep
			# running until all actions have been completed
			if isinstance(result, BaseException):
				msg = '%s\n%s: %s\n' % ( ''.join( traceback.format_tb( thread.exc_info[ 2 ] ) ), thread.exc_info[ 0 ].__name__, str( thread.exc_info[ 1 ] ) )
				MODULE.error('Exception during start_exam: %s' % msg)
				self.finished(request.id, dict(success=True))
				progress_state.error_handler(_('An unexpected error occurred during installation: %s') % result)
			else:
				self.finished(request.id, dict(success=False))

		thread = notifier.threads.Simple('start_exam', _thread, _finished)
		thread.run()


