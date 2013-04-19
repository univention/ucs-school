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

# distribution utils - adjust paths
import univention.management.console.modules.distribution.util as distribution_util
distribution_util.DISTRIBUTION_DATA_PATH = ucr.get('ucsschool/exam/cache', '/var/lib/ucs-school-umc-schoolexam')
distribution_util.POSTFIX_DATADIR_SENDER = ucr.get('ucsschool/exam/datadir/sender', 'Klassenarbeiten')
distribution_util.POSTFIX_DATADIR_RECIPIENT = ucr.get('ucsschool/exam/datadir/recipient', 'Klassenarbeiten')

import os
import tempfile
import shutil
import time
import traceback
from httplib import HTTPException
from socket import error as SocketError

from util import UMCConnection, Progress

udm_modules.update()

_ = Translation( 'ucs-school-umc-exam' ).translate

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
		progress_state.component(_('Initializing'))
		project = None

		def _thread():
			# perform all actions inside a thread...
			# create a User object for the teacher
			sender = distribution_util.openRecipients(self._user_dn, ldap_user_read, search_base)
			if not sender:
				MODULE.error('Could not find user DN: %s' % self._user_dn)
				raise RuntimeError( _('Could not authenticate user "%s"!') % self._user_dn )

			# validate the project data and save project
			opts = request.options
			project = distribution_util.Project(dict(
				name=opts.get('directory'),
				description=opts.get('name'),
				files=opts.get('files'),
				sender=sender,
			))
			project.validate()
			project.save()

			# copy files into project directory
			if self._tmpDir:
				for ifile in project.files:
					isrc = os.path.join(self._tmpDir, ifile)
					itarget = os.path.join(project.cachedir, ifile)
					if os.path.exists(isrc):
						# copy file to cachedir
						shutil.move( isrc, itarget )
						os.chown( itarget, 0, 0 )

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

			# mark the computer room for exam mode
			progress_state.component(_('Preparing the computer room for exam mode...'))
			ires = connection.request('schoolexam-master/set-computerroom-exammode', dict(
				roomdn=request.options.get('room')
			))
			progress_state.add_steps(5)

			# read all recipients and fetch all user objects
			entries = [ientry for ientry in [ distribution_util.openRecipients(idn, ldap_user_read, search_base) for idn in request.options.get('recipients', []) ] if ientry ]
			users = []
			for ientry in entries:
				# recipients can in theory be users or groups
				if isinstance(ientry, distribution_util.User):
					users.append(ientry)
				elif isinstance(ientry, distribution_util.Group):
					users.extend(ientry.members)

			# start to create exam user accounts
			progress_state.component(_('Preparing exam accounts'))
			percentPerUser = 25.0 / len(users)
			examUsers = set()
			usersReplicated = set()
			for iuser in users:
				progress_state.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
				try:
					ires = connection.request('schoolexam-master/create-exam-user', dict(
						userdn=iuser.dn
					))
					examUsers.add(ires.get('examuserdn'))
					MODULE.info('Exam user has been created: %s' % ires.get('examuserdn'))
				except (HTTPException, SocketError) as e:
					MODULE.warn('Could not create exam user account for: %s' % iuser.dn)

				# indicate the the user has been processed
				progress_state.add_steps(percentPerUser)

			# wait for the replication of all users to be finished
			userModul = udm_modules.get( 'users/user' )
			progress_state.component(_('Preparing user home directories'))
			recipients = []  # list of User objects for all exam users
			while len(examUsers) > len(usersReplicated):
				MODULE.info('waiting for replication to be finished, %s objects missing' % (len(examUsers) - len(usersReplicated)))
				for idn in examUsers - usersReplicated:
					try:
						# try to open the user
						iuser = distribution_util.openRecipients(idn, ldap_user_read, search_base)
						if iuser:
							MODULE.info('user has been replicated: %s' % idn)

							### TODO: COPY PROFILE DIR

							# store User object in list of final recipients
							recipients.append(iuser)

							# mark the user as replicated
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

			# update the final list of recipients
			project.recipients = recipients
			project.save()

			# distribute exam files
			progress_state.component(_('Distributing exam files'))
			progress_state.info('')
			project.distribute()
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
				self.finished(request.id, dict(success=False))
				progress_state.error(_('An unexpected error occurred during installation: %s') % result)

				# in case a distribution project has already be written to disk, purge it
				if project:
					project.purge()
			else:
				self.finished(request.id, dict(success=True))

				# remove uploaded files from cache
				self._cleanTmpDir()

		thread = notifier.threads.Simple('start_exam', _thread, _finished)
		thread.run()


