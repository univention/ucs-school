#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  Starts a new exam for a specified computer room
#
# Copyright 2013-2016 Univention GmbH
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

from univention.management.console.modules import UMC_CommandError, UMC_OptionTypeError
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, file_upload, require_password

from univention.lib.i18n import Translation
from univention.lib.umc_connection import UMCConnection

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule
import ucsschool.lib.internetrules as internetrules
from ucsschool.lib.schoollessons import SchoolLessons
from ucsschool.lib.models import ComputerRoom

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions

import os
import tempfile
import shutil
import time
import traceback
import subprocess
import datetime
from httplib import HTTPException
from socket import error as SocketError

import util
from util import Progress

udm_modules.update()

_ = Translation( 'ucs-school-umc-exam' ).translate

CREATE_USER_POST_HOOK_DIR = '/usr/share/ucs-school-exam/hooks/create_exam_user_post.d/'

class Instance( SchoolBaseModule ):
	def __init__( self ):
		SchoolBaseModule.__init__(self)
		self._tmpDir = None
		self._progress_state = Progress()
		self._lessons = SchoolLessons()

	def init(self):
		SchoolBaseModule.init(self)
		# initiate paths for data distribution
		util.distribution.initPaths()

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

	@file_upload
	def upload(self, request):
		### copied from distribution module
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of dicts, but got: %s' % str(request.options) )

		for file in request.options:
			if not ('tmpfile' in file and 'filename' in file):
				raise UMC_OptionTypeError( 'Invalid upload data, got: %s' % str(file) )

			# create a temporary upload directory, if it does not already exist
			if not self._tmpDir:
				self._tmpDir = tempfile.mkdtemp(prefix='ucsschool-exam-upload-')
				MODULE.info('Created temporary directory: %s' % self._tmpDir)

			filename = self.__workaround_filename_bug(file)
			destPath = os.path.join(self._tmpDir, filename)
			MODULE.info('Received file %r, saving it to %r' % (file['tmpfile'], destPath))
			shutil.move(file['tmpfile'], destPath)

		# done
		self.finished( request.id, None )

	def __workaround_filename_bug(self, file):
		### the following code block is a heuristic to support both: fixed and unfixed Bug #37716
		filename = file['filename']
		try:
			# The UMC-Webserver decodes filename in latin-1, need to revert
			filename = filename.encode('ISO8859-1')
		except UnicodeEncodeError:
			# we got non-latin characters, Bug #37716 is fixed and string contains e.g. '→'
			filename = file['filename'].encode('UTF-8')
		else:
			# the string contains at least no non-latin1 characters
			try:
				# try if the bytes could be UTF-8
				# can't fail if Bug #37716 is fixed
				filename.decode('UTF-8')
			except UnicodeDecodeError:
				filename = file['filename'].encode('UTF-8')  # Bug #37716 was fixed
		MODULE.info('Detected filename %r as %r' % (file['filename'], filename))
		### the code block can be removed and replaced by filename = file['filename'].encode('UTF-8') after Bug #37716
		return filename

	def internetrules( self, request ):
		### copied from computerroom module
		"""Returns a list of available internet rules"""
		self.finished( request.id, map( lambda x: x.name, internetrules.list() ) )

	@simple_response
	def lesson_end(self):
		current = self._lessons.current
		if current is not None:
			return current.end.strftime('%H:%M')
		return (datetime.datetime.now() + datetime.timedelta(minutes=45)).strftime('%H:%M')

	@simple_response
	def progress(self):
		return self._progress_state.poll()

	@require_password
	@LDAP_Connection()
	def start_exam(self, request, ldap_user_read = None, ldap_position = None, search_base = None):
		self.required_options(request, 'recipients', 'room', 'internetRule', 'shareMode', 'name', 'directory', 'examEndTime')

		# reset the current progress state
		# steps:
		#   5  -> for preparing exam room
		#   25 -> for cloning users
		#   25 -> for each replicated users + copy of the profile directory
		#   20 -> distribution of exam files
		#   10  -> setting room properties
		progress = self._progress_state
		progress.reset(85)
		progress.component(_('Initializing'))

		# create that holds a reference to project, otherwise _thread() cannot
		# set the project variable in the scope of start_exam:
		# http://stackoverflow.com/questions/7935966/python-overwriting-variables-in-nested-functions
		my = type("", (), dict(
			project=None
		))()

		# create a User object for the teacher
		# perform this LDAP operation outside the thread, to avoid tracebacks
		# in case of an LDAP timeout
		sender = util.distribution.openRecipients(self._user_dn, ldap_user_read, search_base)

		def _thread():
			if not sender:
				MODULE.error('Could not find user DN: %s' % self._user_dn)
				raise RuntimeError( _('Could not authenticate user "%s"!') % self._user_dn )

			# make sure that a project with the same name does not exist
			opts = request.options
			# get absolute path of project file and test for existance
			fn_test_project = util.distribution.Project.sanitize_project_filename(opts.get('directory'))
			if os.path.exists(fn_test_project):
				raise UMC_CommandError(_('An exam with the name "%s" already exists. Please choose a different name for the exam.') % opts.get('directory'))

			# validate the project data and save project
			my.project = util.distribution.Project(dict(
				name=opts.get('directory'),
				description=opts.get('name'),
				files=opts.get('files'),
				sender=sender,
			))
			my.project.validate()
			my.project.save()

			# copy files into project directory
			if self._tmpDir:
				for ifile in my.project.files:
					isrc = os.path.join(self._tmpDir, ifile)
					itarget = os.path.join(my.project.cachedir, ifile)
					if os.path.exists(isrc):
						# copy file to cachedir
						shutil.move( isrc, itarget )
						os.chown( itarget, 0, 0 )

			# open a new connection to the master UMC
			connection = UMCConnection.get_machine_connection()
			if not connection:
				MODULE.error('Could not connect to UMC on %s' % (ucr.get('ldap/master')))
				raise UMC_CommandError(_('Could not connect to master server %s.') % ucr.get('ldap/master'))

			# mark the computer room for exam mode
			progress.component(_('Preparing the computer room for exam mode...'))
			res = connection.request('schoolexam-master/set-computerroom-exammode', dict(
				roomdn=request.options.get('room')
			))
			progress.add_steps(5)

			# read all recipients and fetch all user objects
			entries = [ientry for ientry in [ util.distribution.openRecipients(idn, ldap_user_read, search_base) for idn in request.options.get('recipients', []) ] if ientry ]
			users = []
			for ientry in entries:
				# recipients can in theory be users or groups
				if isinstance(ientry, util.distribution.User):
					users.append(ientry)
				elif isinstance(ientry, util.distribution.Group):
					users.extend(ientry.members)

			# ignore exam users
			users = [ iuser for iuser in users if not search_base.isExamUser(iuser.dn) ]

			# start to create exam user accounts
			progress.component(_('Preparing exam accounts'))
			percentPerUser = 25.0 / (1 + len(users))
			examUsers = set()
			usersReplicated = set()
			for iuser in users:
				progress.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
				try:
					ires = connection.request('schoolexam-master/create-exam-user', dict(
						userdn=iuser.dn
					))
					examUsers.add(ires.get('examuserdn'))
					MODULE.info('Exam user has been created: %s' % ires.get('examuserdn'))
				except (HTTPException, SocketError) as e:
					MODULE.warn('Could not create exam user account for: %s' % iuser.dn)

				# indicate the the user has been processed
				progress.add_steps(percentPerUser)

			progress.add_steps(percentPerUser)

			# wait for the replication of all users to be finished
			progress.component(_('Preparing user home directories'))
			recipients = []  # list of User objects for all exam users
			openAttempts = 300 # wait max. 5 minutes for replication
			while (len(examUsers) > len(usersReplicated)) and (openAttempts > 0):
				openAttempts -= 1
				MODULE.info('waiting for replication to be finished, %s user objects missing' % (len(examUsers) - len(usersReplicated)))
				for idn in examUsers - usersReplicated:
					try:
						# try to open the user
						iuser = util.distribution.openRecipients(idn, ldap_user_read, search_base)
						if iuser:
							MODULE.info('user has been replicated: %s' % idn)

							# call hook scripts
							if 0 != subprocess.call(['/bin/run-parts', CREATE_USER_POST_HOOK_DIR, '--arg', iuser.username, '--arg', iuser.dn, '--arg', iuser.homedir]):
								msg = 'failed to run hook scripts for user %r' % (iuser.username)
								MODULE.error(msg)
								raise ValueError(msg)

							# store User object in list of final recipients
							recipients.append(iuser)

							# mark the user as replicated
							usersReplicated.add(idn)
							progress.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
							progress.add_steps(percentPerUser)
					except udm_exceptions.noObject:
						# access failed
						pass

				# wait a second
				time.sleep(1)

			progress.add_steps(percentPerUser)

			if openAttempts <= 0:
				MODULE.error('replication timeout - %s user objects missing: %r ' % ((len(examUsers) - len(usersReplicated)), (examUsers - usersReplicated)))
				msg = _('Replication timeout: could not create all exam users')
				MODULE.error(msg)
				raise UMC_CommandError(msg)

			# update the final list of recipients
			my.project.recipients = recipients
			my.project.save()

			# update local NSS group cache
			if ucr.is_true('nss/group/cachefile', True):
				cmd = ['/usr/lib/univention-pam/ldap-group-to-file.py']
				if ucr.is_true('nss/group/cachefile/check_member', False):
					cmd.append('--check_member')
				MODULE.info('Updating local nss group cache...')
				if subprocess.call(cmd):
					MODULE.error('Updating local nss group cache failed: %s' % ' '.join(cmd))
				else:
					MODULE.info('Update of local nss group cache finished successfully.')

			# distribute exam files
			progress.component(_('Distributing exam files'))
			progress.info('')
			my.project.distribute()
			progress.add_steps(20)

			# prepare room settings via UMCP...
			#   first step: acquire room
			#   second step: adjust room settings
			progress.component(_('Prepare room settings'))
			userConnection = UMCConnection('localhost', username=self.username, password=self.password)
			if not userConnection:
				MODULE.error('Could not connect to UMC on local server: %s' % e)
				raise UMC_CommandError(_('Could not connect to local UMC server.'))
			MODULE.info('Acquire room: %(room)s' % opts)
			userConnection.request('computerroom/room/acquire', dict(
				room=opts.get('room')
			))
			progress.add_steps(5)
			MODULE.info('Adjust room settings:\n%s' % '\n'.join([ '  %s=%s' % (k, v) for k, v in opts.iteritems() ]))
			userConnection.request('computerroom/settings/set', dict(
				internetRule=opts.get('internetRule'),
				customRule=opts.get('customRule'),
				shareMode=opts.get('shareMode'),
				printMode='default',
				examDescription=opts.get('name'),
				exam=opts.get('directory'),
				examEndTime=opts.get('examEndTime'),
			))
			progress.add_steps(5)

		def _finished(thread, result):
			# mark the progress state as finished
			progress.info(_('finished...'))
			progress.finish()

			# finish the request at the end in order to force the module to keep
			# running until all actions have been completed
			if isinstance(result, BaseException):
				msg = '%s\n%s: %s\n' % ( ''.join( traceback.format_tb( thread.exc_info[ 2 ] ) ), thread.exc_info[ 0 ].__name__, str( thread.exc_info[ 1 ] ) )
				MODULE.error('Exception during start_exam: %s' % msg)
				self.finished(request.id, dict(success=False))
				progress.error(_('An unexpected error occurred during the preparation: %s') % result)

				# in case a distribution project has already be written to disk, purge it
				if my.project:
					my.project.purge()
			else:
				self.finished(request.id, dict(success=True))

				# remove uploaded files from cache
				self._cleanTmpDir()

		thread = notifier.threads.Simple('start_exam', _thread, _finished)
		thread.run()

	def collect_exam(self, request):
		self.required_options(request, 'exam')

		# try to open project file
		project = util.distribution.Project.load(request.options.get('exam'))
		if not project:
			raise UMC_CommandError(_('No files have been distributed'))

		# collect files
		project.collect()

		self.finished(request.id, True)

	@LDAP_Connection()
	def validate_room(self, request, ldap_user_read=None, ldap_position=None, search_base=None):
		self.required_options(request, 'room')
		error = None
		dn = request.options.get('room')
		room = ComputerRoom.from_dn(dn, None, ldap_user_read)
		if not room.hosts:
			error = _('Room "%s" does not contain any computers. Empty rooms may not be used to start an exam.') % room.get_relative_name()
		self.finished(request.id, error)

	def finish_exam(self, request):
		self.required_options(request, 'exam', 'room')

		# reset the current progress state
		# steps:
		#   10 -> collecting exam files
		#   5 -> for preparing exam room
		#   25 -> for cloning users
		progress = self._progress_state
		progress.reset(40)
		progress.component(_('Initializing'))

		# try to open project file
		project = util.distribution.Project.load(request.options.get('exam'))
		if not project:
			# the project file does not exist... ignore problem
			MODULE.warn('The project file for exam %s does not exist. Ignoring and finishing exam mode.' % request.options.get('exam'))

		def _thread():
			# perform all actions inside a thread...
			# collect files
			progress.component(_('Collecting exam files...'))
			if project:
				project.collect()
			progress.add_steps(10)

			# open a new connection to the master UMC
			connection = UMCConnection.get_machine_connection()
			if not connection:
				MODULE.error('Could not connect to UMC on %s' % (ucr.get('ldap/master')))
				raise UMC_CommandError(_('Could not connect to master server %s.') % ucr.get('ldap/master'))

			# unset exam mode for the given computer room
			progress.component(_('Configuring the computer room...'))
			res = connection.request('schoolexam-master/unset-computerroom-exammode', dict(
				roomdn=request.options.get('room')
			))
			progress.add_steps(5)

			# delete exam users accounts
			if project:
				# get a list of user accounts in parallel exams
				parallelUsers = dict([
					(iuser.username, iproject.description)
					for iproject in util.distribution.Project.list()
					if iproject.name != project.name
					for iuser in iproject.recipients
				])

				progress.component(_('Removing exam accounts'))
				percentPerUser = 25.0 / (1 + len(project.recipients))
				for iuser in project.recipients:
					progress.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
					try:
						if iuser.username not in parallelUsers:
							# remove first the home directory
							shutil.rmtree(iuser.unixhome, ignore_errors=True)

							# remove LDAP user entry
							ires = connection.request('schoolexam-master/remove-exam-user', dict(
								userdn=iuser.dn
							))
							MODULE.info('Exam user has been removed: %s' % iuser.dn)
						else:
							MODULE.process('Cannot remove the user account %s as it is registered for the running exam "%s", as well' % (iuser.dn, parallelUsers[iuser.username]))
					except (HTTPException, SocketError) as e:
						MODULE.warn('Could not remove exam user account %s: %s' % (iuser.dn, e))

					# indicate the the user has been processed
					progress.add_steps(percentPerUser)

				progress.add_steps(percentPerUser)

		def _finished(thread, result):
			# mark the progress state as finished
			progress.info(_('finished...'))
			progress.finish()

			# running until all actions have been completed
			if isinstance(result, BaseException):
				msg = '%s\n%s: %s\n' % ( ''.join( traceback.format_tb( thread.exc_info[ 2 ] ) ), thread.exc_info[ 0 ].__name__, str( thread.exc_info[ 1 ] ) )
				MODULE.error('Exception during exam_finish: %s' % msg)
				self.finished(request.id, dict(success=False))
				progress.error(_('An unexpected error occurred during the preparation: %s') % result)
			else:
				self.finished(request.id, dict(success=True))

				if project:
					# pruge project
					project.purge()

				# remove uploaded files from cache
				self._cleanTmpDir()

		thread = notifier.threads.Simple('start_exam', _thread, _finished)
		thread.run()


