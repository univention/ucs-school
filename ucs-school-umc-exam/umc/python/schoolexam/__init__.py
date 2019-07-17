#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  Starts a new exam for a specified computer room
#
# Copyright 2013-2019 Univention GmbH
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

import os
import tempfile
import shutil
import time
import traceback
import subprocess
import datetime
from itertools import chain

import ldap
import notifier

from univention.admin.uexceptions import noObject

from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import simple_response, file_upload, require_password, sanitize
from univention.management.console.modules.sanitizers import (
	StringSanitizer, DictSanitizer, ListSanitizer, DNSanitizer, PatternSanitizer, ChoicesSanitizer)
from univention.management.console.modules.schoolexam import util
from univention.management.console.modules.distribution import compare_dn
import univention.admin.uexceptions as udm_exceptions

from univention.lib.i18n import Translation
from univention.lib.umc import Client, ConnectionError, HTTPError

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule, SchoolSearchBase, SchoolSanitizer, Display
from ucsschool.lib import internetrules
from ucsschool.lib.schoollessons import SchoolLessons
from ucsschool.lib.models import ComputerRoom, Group, User
from ucsschool.lib.models.base import WrongObjectType

try:
	from typing import Any, Dict, List, Optional, Pattern
except ImportError:
	pass

_ = Translation('ucs-school-umc-exam').translate

CREATE_USER_POST_HOOK_DIR = '/usr/share/ucs-school-exam/hooks/create_exam_user_post.d/'


class Instance(SchoolBaseModule):

	def __init__(self):
		SchoolBaseModule.__init__(self)
		self._tmpDir = None
		self._progress_state = util.Progress()
		self._lessons = SchoolLessons()

	def init(self):
		SchoolBaseModule.init(self)
		# initiate paths for data distribution
		util.distribution.initPaths()

	def destroy(self):
		# clean temporary data
		self._cleanTmpDir()

	def _cleanTmpDir(self):
		# copied from distribution module
		# clean up the temporary upload directory
		if self._tmpDir:
			MODULE.info('Clean up temporary directory: %s' % self._tmpDir)
			shutil.rmtree(self._tmpDir, ignore_errors=True)
			self._tmpDir = None

	@file_upload
	@sanitize(DictSanitizer(dict(
		filename=StringSanitizer(required=True),
		tmpfile=StringSanitizer(required=True),
	), required=True))
	def upload(self, request):
		# copied from distribution module
		# create a temporary upload directory, if it does not already exist
		if not self._tmpDir:
			self._tmpDir = tempfile.mkdtemp(prefix='ucsschool-exam-upload-')
			MODULE.info('Created temporary directory: %s' % self._tmpDir)

		for file in request.options:
			filename = self.__workaround_filename_bug(file)
			destPath = os.path.join(self._tmpDir, filename)
			MODULE.info('Received file %r, saving it to %r' % (file['tmpfile'], destPath))
			shutil.move(file['tmpfile'], destPath)

		self.finished(request.id, None)

	def __workaround_filename_bug(self, file):
		# the following code block is a heuristic to support both: fixed and unfixed Bug #37716
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
		# the code block can be removed and replaced by filename = file['filename'].encode('UTF-8') after Bug #37716
		# Bug 46709/46710: start
		if '\\' in filename:  # filename seems to be a UNC / windows path
			MODULE.info('Filename seems to contain Windows path name or UNC - fixing filename')
			filename = filename.rsplit('\\', 1)[-1] or filename.replace('\\', '_').lstrip('_')
		# Bug 46709/46710: end
		MODULE.info('Detected filename %r as %r' % (file['filename'], filename))
		return filename

	@simple_response
	def internetrules(self):
		# copied from computerroom module
		"""Returns a list of available internet rules"""
		return [x.name for x in internetrules.list()]

	@simple_response
	def lesson_end(self):
		current = self._lessons.current
		if current is not None:
			return current.end.strftime('%H:%M')
		return (datetime.datetime.now() + datetime.timedelta(minutes=45)).strftime('%H:%M')

	@simple_response
	def progress(self):
		return self._progress_state.poll()

	@LDAP_Connection()
	def _user_can_modify(self, user, exam, ldap_user_read=None):
		"""
		Checks whether the given user is allowed to modify the given exam or not.
		Domain Admin: Can always modify
		School Admin: Can modify if exam owner is in own school
		Else: if owner is caller
		:param user: The user school object
		:param exam: The exam to be modified
		:return: True if user can modify else False
		"""
		if user.dn == exam.sender.dn:
			return True
		sender_user = User.from_dn(exam.sender.dn, None, ldap_user_read)
		if user.is_administrator(ldap_user_read) and len(set(sender_user.schools).intersection(user.schools)) != 0:
			return True
		admin_group_dn = 'cn=Domain Admins,cn=groups,' + ucr['ldap/base']
		if admin_group_dn in user.get_udm_object(ldap_user_read)['groups']:
			return True
		return False

	@LDAP_Connection()
	def _save_exam(self, request, update=False, ldap_user_read=None):
		"""
		Creates or updates an exam with the information given in the request object
		:param request: The request containing all information about the exam
		:param update: If True it is expected that an exam with the same name already exists and will be updated
		:return: True if successful, else Exception
		"""
		# create a User object for the teacher
		sender = util.distribution.openRecipients(self.user_dn, ldap_user_read)
		recipients = [util.distribution.openRecipients(i_dn, ldap_user_read) for i_dn in request.options.get('recipients', [])]
		recipients = [recipient for recipient in recipients if recipient]
		new_values = dict(
				name=request.options['directory'],
				description=request.options['name'],
				files=request.options.get('files'),
				sender=sender,
				room=request.options['room'],
				recipients=recipients,
				deadline=request.options['examEndTime']
			)
		if not sender:
			raise UMC_Error(_('Could not authenticate user "%s"!') % self.user_dn)
		project = util.distribution.Project.load(request.options.get('name', ''))
		orig_files = []
		if update:
			if not project:
				raise UMC_Error(_('The specified exam does not exist: %s') % request.options.get('name', ''))
			# make sure that the project owner himself is modifying the project
			if not compare_dn(project.sender.dn, self.user_dn):
				raise UMC_Error(_('The exam can only be modified by the owner himself.'))
			if project.isDistributed:
				raise UMC_Error(_('The exam was already started and can not be modified anymore!'))
			orig_files = project.files
			project.update(new_values)
		else:
			if project:
				raise UMC_Error(_('An exam with the name "%s" already exists. Please choose a different name for the exam.') % new_values['directory'])
			project = util.distribution.Project(new_values)
		project.validate()
		project.save()
		# copy files into project directory
		if self._tmpDir:
			for i_file in project.files:
				i_src = os.path.join(self._tmpDir, i_file)
				i_target = os.path.join(project.cachedir, i_file)
				if os.path.exists(i_src):
					# copy file to cachedir
					shutil.move(i_src, i_target)
					os.chown(i_target, 0, 0)
		if update:
			for i_file in set(orig_files) - set(project.files):
				i_target = os.path.join(project.cachedir, i_file)
				try:
					os.remove(i_target)
				except OSError:
					pass
		return project

	@LDAP_Connection()
	def _delete_exam(self, name, ldap_user_read=None):
		"""
		Deletes an exam project file including the uploaded data if the exam was not started yet and the caller is
		authorized to do so.
		:param name: Name of the exam to delete
		:return: True if exam was deleted, else False
		"""
		exam = util.distribution.Project.load(name)
		if not exam:
			return False
		if exam.isDistributed:
			return False
		if not self._user_can_modify(User.from_dn(ldap_user_read.whoami(), None, ldap_user_read) ,exam):
			return False
		exam.purge()
		return True

	@sanitize(StringSanitizer(required=True))
	@LDAP_Connection()
	def get(self, request, ldap_user_read=None):
		result = []
		for project in [util.distribution.Project.load(iid) for iid in request.options]:
			if not project:
				continue
			# make sure that only the project owner himself (or an admin) is able
			# to see the content of a project
			if not compare_dn(project.sender.dn, self.user_dn):
				raise UMC_Error(_('Exam details are only visible to the exam owner himself.'), status=403)
			props = project.dict
			props['sender'] = props['sender'].username
			recipients = []
			for recip in props['recipients']:
				recipients.append({
					'id': recip.dn,
					'label': recip.type == util.distribution.TYPE_USER and Display.user(recip.dict) or recip.name
				})
			props['recipients'] = recipients
			props['examEndTime'] = props['deadline']
			result.append(props)
		self.finished(request.id, result)

	@sanitize(
		name=StringSanitizer(required=True),
		room=StringSanitizer(required=True),
		school=SchoolSanitizer(required=True),
		directory=StringSanitizer(required=True),
		shareMode=StringSanitizer(required=True),
		internetRule=StringSanitizer(required=True),
		customRule=StringSanitizer(),
		examEndTime=StringSanitizer(required=True),
		recipients=ListSanitizer(StringSanitizer(minimum=1), required=True),
		files=ListSanitizer(StringSanitizer()),
	)
	@require_password
	@LDAP_Connection()
	def add(self, request, ldap_user_read=None):
		self._save_exam(request)
		self.finished(request.id, True)

	@sanitize(
		exams=ListSanitizer(StringSanitizer(minimum=1), required=True)
	)
	@LDAP_Connection()
	def delete(self, request, ldap_user_read=None):
		result = []
		for exam in request.options['exams']:
			result.append(self._delete_exam(exam))
		self.finished(request.id, result)

	@sanitize(
		name=StringSanitizer(required=True),
		room=StringSanitizer(required=True),
		school=SchoolSanitizer(required=True),
		directory=StringSanitizer(required=True),
		shareMode=StringSanitizer(required=True),
		internetRule=StringSanitizer(required=True),
		customRule=StringSanitizer(),
		examEndTime=StringSanitizer(required=True),
		recipients=ListSanitizer(StringSanitizer(minimum=1), required=True),
		files=ListSanitizer(StringSanitizer()),
	)
	@require_password
	@LDAP_Connection()
	def put(self, request, ldap_user_read=None):
		self._save_exam(request, update=True)
		self.finished(request.id, True)

	@sanitize(
		name=StringSanitizer(required=True),
		room=StringSanitizer(required=True),
		school=SchoolSanitizer(required=True),
		directory=StringSanitizer(required=True),
		shareMode=StringSanitizer(required=True),
		internetRule=StringSanitizer(required=True),
		customRule=StringSanitizer(),
		examEndTime=StringSanitizer(required=True),
		recipients=ListSanitizer(StringSanitizer(minimum=1), required=True),
		files=ListSanitizer(StringSanitizer()),
	)
	@require_password
	@LDAP_Connection()
	def start_exam(self, request, ldap_user_read=None, ldap_position=None):
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
		my = type("", (), dict(
			project=None
		))()

		# create a User object for the teacher
		# perform this LDAP operation outside the thread, to avoid tracebacks
		# in case of an LDAP timeout
		sender = util.distribution.openRecipients(self.user_dn, ldap_user_read)
		if not sender:
			raise UMC_Error(_('Could not authenticate user "%s"!') % self.user_dn)

		def _thread():
			project = util.distribution.Project.load(request.options.get('name', ''))
			directory = request.options['directory']
			if project:
				my.project = self._save_exam(request, update=True, ldap_user_read=ldap_user_read)
			else:
				my.project = self._save_exam(request, update=False, ldap_user_read=ldap_user_read)

			# open a new connection to the master UMC
			try:
				master = ucr['ldap/master']
				client = Client(master)
				client.authenticate_with_machine_account()
			except (ConnectionError, HTTPError) as exc:
				MODULE.error('Could not connect to UMC on %s: %s' % (master, exc))
				raise UMC_Error(_('Could not connect to master server %s.') % ucr.get('ldap/master'))

			# mark the computer room for exam mode
			progress.component(_('Preparing the computer room for exam mode...'))
			client.umc_command('schoolexam-master/set-computerroom-exammode', dict(
				school=request.options['school'],
				roomdn=request.options['room'],
			)).result  # FIXME: no error handling
			progress.add_steps(5)

			# read all recipients and fetch all user objects
			users = []
			for idn in request.options['recipients']:
				ientry = util.distribution.openRecipients(idn, ldap_user_read)
				if not ientry:
					continue
				# recipients can in theory be users or groups
				members = []
				if isinstance(ientry, util.distribution.User):
					members = [ientry]
				elif isinstance(ientry, util.distribution.Group):
					members = ientry.members
				for entry in members:
					# ignore exam users
					user = User.from_dn(entry.dn, None, ldap_user_read)
					if not user.is_exam_student(ldap_user_read):
						users.append(entry)

			# start to create exam user accounts
			progress.component(_('Preparing exam accounts'))
			percentPerUser = 25.0 / (1 + len(users))
			examUsers = set()
			student_dns = set()
			usersReplicated = set()
			for iuser in users:
				progress.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
				try:
					ires = client.umc_command('schoolexam-master/create-exam-user', dict(
						school=request.options['school'],
						userdn=iuser.dn,
					)).result
					examuser_dn = ires.get('examuserdn')
					examUsers.add(examuser_dn)
					student_dns.add(iuser.dn)
					MODULE.info('Exam user has been created: %r' % examuser_dn)
				except (ConnectionError, HTTPError) as exc:
					MODULE.warn('Could not create exam user account for %r: %s' % (iuser.dn, exc))

				# indicate the the user has been processed
				progress.add_steps(percentPerUser)

			client.umc_command('schoolexam-master/add-exam-users-to-groups', dict(
				users=list(student_dns),
				school=request.options['school'],
			))

			progress.add_steps(percentPerUser)

			# wait for the replication of all users to be finished
			progress.component(_('Preparing user home directories'))
			recipients = []  # list of User objects for all exam users
			openAttempts = 30*60  # wait max. 30 minutes for replication
			while (len(examUsers) > len(usersReplicated)) and (openAttempts > 0):
				openAttempts -= 1
				MODULE.info('waiting for replication to be finished, %s user objects missing' % (len(examUsers) - len(usersReplicated)))
				for idn in examUsers - usersReplicated:
					try:
						ldap_user_read.get(idn, required=True)
					except ldap.NO_SUCH_OBJECT:
						continue  # not replicated yet
					iuser = util.distribution.openRecipients(idn, ldap_user_read)
					if not iuser:
						continue  # not a users/user object
					MODULE.info('user has been replicated: %s' % idn)

					# call hook scripts
					if 0 != subprocess.call(['/bin/run-parts', CREATE_USER_POST_HOOK_DIR, '--arg', iuser.username, '--arg', iuser.dn, '--arg', iuser.homedir]):
						raise ValueError('failed to run hook scripts for user %r' % (iuser.username))

					# store User object in list of final recipients
					recipients.append(iuser)

					# mark the user as replicated
					usersReplicated.add(idn)
					progress.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
					progress.add_steps(percentPerUser)

				# wait a second
				time.sleep(1)

			progress.add_steps(percentPerUser)

			if openAttempts <= 0:
				MODULE.error('replication timeout - %s user objects missing: %r ' % ((len(examUsers) - len(usersReplicated)), (examUsers - usersReplicated)))
				raise UMC_Error(_('Replication timeout: could not create all exam users'))

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
			try:
				user_client = Client(None, self.username, self.password)
			except (ConnectionError, HTTPError) as exc:
				MODULE.warn('Authentication failed: %s' % (exc,))
				raise UMC_Error(_('Could not connect to local UMC server.'))

			room = request.options['room']
			MODULE.info('Acquire room: %s' % (room,))
			user_client.umc_command('computerroom/room/acquire', dict(
				room=request.options['room'],
			)).result
			progress.add_steps(1)
			MODULE.info('Adjust room settings:\n%s' % '\n'.join(['  %s=%s' % (k, v) for k, v in request.options.iteritems()]))
			user_client.umc_command('computerroom/exam/start', dict(
				room=room,
				examDescription=request.options['name'],
				exam=directory,
				examEndTime=request.options.get('examEndTime'),
			)).result
			progress.add_steps(4)
			user_client.umc_command('computerroom/settings/set', dict(
				room=room,
				internetRule=request.options['internetRule'],
				customRule=request.options.get('customRule'),
				shareMode=request.options['shareMode'],
				printMode='default',
			)).result
			progress.add_steps(5)

		def _finished(thread, result, request):
			my.project.starttime = datetime.datetime.now()
			my.project.save()

			# mark the progress state as finished
			progress.info(_('finished...'))
			progress.finish()

			# finish the request at the end in order to force the module to keep
			# running until all actions have been completed
			success = not isinstance(result, BaseException)
			response = dict(success=success)
			if success:
				# remove uploaded files from cache
				self._cleanTmpDir()
			else:
				msg = str(result)
				if not isinstance(result, UMC_Error):
					response = result
					msg = ''.join(traceback.format_exception(*thread.exc_info))
				progress.error(msg)

				# in case a distribution project has already be written to disk, purge it
				if my.project:
					my.project.purge()

			self.thread_finished_callback(thread, response, request)

		thread = notifier.threads.Simple('start_exam', _thread, notifier.Callback(_finished, request))
		thread.run()

	@sanitize(
		exam=StringSanitizer(required=True),
	)
	@simple_response
	def collect_exam(self, exam):
		project = util.distribution.Project.load(exam)
		if not project:
			raise UMC_Error(_('No files have been distributed'))

		project.collect()
		return True

	@sanitize(
		room=DNSanitizer(required=True),
	)
	@LDAP_Connection()
	def validate_room(self, request, ldap_user_read=None, ldap_position=None):
		error = None
		dn = request.options['room']
		room = ComputerRoom.from_dn(dn, None, ldap_user_read)
		if not room.hosts:
			# FIXME: raise UMC_Error()
			error = _('Room "%s" does not contain any computers. Empty rooms may not be used to start an exam.') % room.get_relative_name()
		self.finished(request.id, error)

	@sanitize(
		room=StringSanitizer(required=True),
		exam=StringSanitizer(required=True),
	)
	def finish_exam(self, request):
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
			master = ucr['ldap/master']
			try:
				client = Client(master)
				client.authenticate_with_machine_account()
			except (ConnectionError, HTTPError) as exc:
				MODULE.error('Could not connect to UMC on %s: %s' % (master, exc))
				raise UMC_Error(_('Could not connect to master server %s.') % (master,))

			school = SchoolSearchBase.getOU(request.options['room'])

			# unset exam mode for the given computer room
			progress.component(_('Configuring the computer room...'))
			client.umc_command('schoolexam-master/unset-computerroom-exammode', dict(
				roomdn=request.options['room'],
				school=school,
			)).result
			progress.add_steps(5)

			# delete exam users accounts
			if project:
				# get a list of user accounts in parallel exams
				parallelUsers = dict([
					(iuser.username, iproject.description)
					for iproject in util.distribution.Project.list(only_distributed=True)
					if iproject.name != project.name
					for iuser in iproject.recipients
				])

				progress.component(_('Removing exam accounts'))
				percentPerUser = 25.0 / (1 + len(project.recipients))
				for iuser in project.recipients:
					progress.info('%s, %s (%s)' % (iuser.lastname, iuser.firstname, iuser.username))
					try:
						if iuser.username not in parallelUsers:
							# remove first the home directory, if enabled
							if ucr.is_true('ucsschool/exam/user/homedir/autoremove', False):
								shutil.rmtree(iuser.unixhome, ignore_errors=True)

							# remove LDAP user entry
							client.umc_command('schoolexam-master/remove-exam-user', dict(
								userdn=iuser.dn,
								school=school,
							)).result
							MODULE.info('Exam user has been removed: %s' % iuser.dn)
						else:
							MODULE.process('Cannot remove the user account %s as it is registered for the running exam "%s", as well' % (iuser.dn, parallelUsers[iuser.username]))
					except (ConnectionError, HTTPError) as e:
						MODULE.warn('Could not remove exam user account %s: %s' % (iuser.dn, e))

					# indicate the user has been processed
					progress.add_steps(percentPerUser)

				progress.add_steps(percentPerUser)

		def _finished(thread, result):
			# mark the progress state as finished
			progress.info(_('finished...'))
			progress.finish()

			# running until all actions have been completed
			if isinstance(result, BaseException):
				msg = ''.join(traceback.format_exception(*thread.exc_info))
				MODULE.error('Exception during exam_finish: %s' % msg)
				self.finished(request.id, dict(success=False))
				progress.error(_('An unexpected error occurred during the preparation: %s') % result)
			else:
				self.finished(request.id, dict(success=True))

				if project:
					# purge project
					project.purge()

				# remove uploaded files from cache
				self._cleanTmpDir()

		thread = notifier.threads.Simple('start_exam', _thread, _finished)
		thread.run()

	@sanitize(
		pattern=PatternSanitizer(required=False, default='.*'),
		filter=ChoicesSanitizer(['all', 'private'], default='private')
	)
	@LDAP_Connection()
	def query(self, request, ldap_user_read=None):
		"""
		Get all exams (both running and planned).

		:param _sre.SRE_Pattern pattern: pattern that the result lists
			project names is matched against, defaults to `.*` (compiled by
			decorator).
		:param str filter: filter result list by project creator ("sender").
			Must be either `all` or `private`, defaults to `private`.
		:return: list of projects
		:rtype: list(dict)
		"""
		pattern = request.options['pattern']
		filter = request.options['filter']
		result = [
			{
				'name': project.name,
				'sender': project.sender.username,  # teacher / admins
				'recipientsGroups': [g.name for g in project.recipients if g.type == util.distribution.TYPE_GROUP],
				'recipientsStudents': self._get_project_students(project, ldap_user_read),
				'starttime': project.starttime.strftime('%Y-%m-%d %H:%M') if project.starttime else '',
				'files': len(project.files) if project.files else 0,
				'isDistributed': project.isDistributed,
				'room': ComputerRoom.get_name_from_dn(project.room) if project.room else '',
			}
			for project in util.distribution.Project.list()
			if pattern.match(project.name) and (filter == 'all' or compare_dn(project.sender.dn, self.user_dn))
		]
		self.finished(request.id, result)   # cannot use @simple_response with @LDAP_Connection :/

	def _get_project_students(self, project, lo):
		students = [s for s in project.recipients if s.type == util.distribution.TYPE_USER]
		students += list(chain.from_iterable(g.members for g in project.recipients if g.type == util.distribution.TYPE_GROUP))
		students = set((s.username, s.dn) for s in students)
		return [s[0] for s in students if User.from_dn(s[1], None, lo).is_student(lo)]

	@sanitize(
		groups=ListSanitizer(DNSanitizer(minimum=1), required=True, min_elements=1)
	)
	@LDAP_Connection()
	def groups2students(self, request, ldap_user_read=None):
		"""
		Get members of passed groups. Only students are returned.

		request.options must contain a key `groups` with a list of DNs (only
		ucsschool.lib WorkGroup and SchoolClass are supported).

		The UMC call will return a list of dicts::

			[{'dn': …, 'firstname': …, 'lastname': …, 'school_classes': …}, …]
		"""
		students = {}
		for group_dn in request.options['groups']:
			try:
				group_obj = Group.from_dn(group_dn, None, ldap_user_read)
			except (WrongObjectType, noObject) as exc:
				MODULE.error('DN {!r} does not exist or is not a work group or school class: {}'.format(group_dn, exc))
				raise UMC_Error(_('Error loading group DN {!r}.').format(group_dn))

			school_class_name = group_obj.name[len(group_obj.school) + 1:]

			for user_dn in group_obj.users:
				try:
					user_obj = User.from_dn(user_dn, None, ldap_user_read)
				except (WrongObjectType, noObject) as exc:
					MODULE.warn('Ignoring DN {!r} - it does not exist or is not a school user: {}'.format(user_dn, exc))
					continue

				if user_obj.is_student(ldap_user_read) and not user_obj.is_exam_student(ldap_user_read):
					if user_dn in students:
						students[user_dn]['school_classes'].append(school_class_name)
					else:
						students[user_dn] = {
							'dn': user_dn,
							'firstname': user_obj.firstname,
							'lastname': user_obj.lastname,
							'school_classes': [school_class_name]
						}
		res = sorted(students.values(), key=lambda x: x['dn'])
		self.finished(request.id, res)   # cannot use @simple_response with @LDAP_Connection :/
