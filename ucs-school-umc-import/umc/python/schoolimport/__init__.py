#!/usr/bin/python2.7
#
# Univention Management Console
#  Automatic UCS@school user import
#
# Copyright 2017 Univention GmbH
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

import os.path
import string
import shutil
import random
import time

import notifier.threads

from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import simple_response, file_upload, require_password, sanitize, allow_get_request
from univention.management.console.modules.sanitizers import StringSanitizer
from univention.management.console.modules.mixins import ProgressMixin
import univention.admin.syntax

from ucsschool.lib.schoolldap import SchoolBaseModule
from ucsschool.http_api.client import Client, ConnectionError, ObjectNotFound, ServerError

from univention.lib.i18n import Translation

_ = Translation('ucs-school-umc-import').translate
CACHE_IMPORT_FILES = '/var/cache/ucs-school-umc-import/'


def random_string():
	return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))


class Instance(SchoolBaseModule, ProgressMixin):

	def init(self):
		self._progress_objs = {}
		self.client = Client(self.username, self.password, log_level=Client.LOG_RESPONSE)

	@require_password
	@simple_response
	def schools(self):
		schools = [dict(id=school.name, label=school.displayName) for school in self.client.school.list()]
		if not schools:
			raise UMC_Error(_('No permissions for running an import for any school.'))
		return schools

	@require_password
	@simple_response
	def userroles(self):
		userroles = [dict(id=id, label=label) for id, label in univention.admin.syntax.ucsschoolTypes.choices]
		if not userroles:
			raise UMC_Error(_('No permissions for running an import for any user role.'))
		return userroles

	@require_password
	@file_upload
	def upload_file(self, request):
		filename = request.options[0]['tmpfile']
		destination = os.path.join(CACHE_IMPORT_FILES, random_string())
		shutil.move(filename, destination)
		self.finished(request.id, {'filename': os.path.basename(destination)})

	@sanitize(
		filename=StringSanitizer(required=True),
		userrole=StringSanitizer(required=True),
		school=StringSanitizer(required=True),
	)
	@require_password
	@simple_response
	def dry_run(self, filename, userrole, school):
		progress = self.new_progress(total=100)
		thread = notifier.threads.Simple('dry run', notifier.Callback(self._dry_run, filename, userrole, school, progress), notifier.Callback(self.__thread_error_handling, progress))
		thread.run()
		return dict(progress.poll(), id=progress.id)

	def _dry_run(self, filename, userrole, school, progress):
		progress.progress(True, _('Validating import.'))
		progress.current = 25.0
		progress.job = None
		import_file = os.path.join(CACHE_IMPORT_FILES, os.path.basename(filename))
		try:
			jobid = self.client.userimportjob.create(filename=import_file, school=school, user_role=userrole, dryrun=True).id
		except (ConnectionError, ServerError, ObjectNotFound):
			raise
		progress.progress(True, _('Dry run.'))
		progress.current = 50.0

		SLEEP_TIME = 0.3
		TIMEOUT_AFTER = 120 / SLEEP_TIME  # two minutes
		i = 0
		finished = False
		while not finished:
			time.sleep(SLEEP_TIME)
			job = self.client.userimportjob.get(jobid)
			if job.status == 'Started':
				progress.current = 75.0
			finished = job.status in ('Finished', 'Aborted')
			i += 1
			if i > TIMEOUT_AFTER:
				raise UMC_Error(_('The dry-run timed out.'))

		progress.current = 99.0
		if job.result.status != 'SUCCESS':
			message = _('The tests were not successful. Please consider reading the logfiles for further information.')
			if job.result.traceback:
				message = '%s\n%s' % (message, job.result.traceback)
			raise UMC_Error(message)

		return {'summary': job.result.result}

	def __thread_error_handling(self, thread, result, progress):
		# caution! if an exception happens in this function the module process will die!
		MODULE.error('Thread result: %s' % (result,))
		if isinstance(result, BaseException):
			progress.exception(thread.exc_info)
			return
		progress.finish_with_result(result)

	@sanitize(
		filename=StringSanitizer(required=True),
		userrole=StringSanitizer(required=True),
		school=StringSanitizer(required=True),
	)
	@require_password
	def start_import(self, request):
		thread = notifier.threads.Simple('import', notifier.Callback(self._start_import, request), notifier.Callback(self.thread_finished_callback, request))
		thread.run()

	def _start_import(self, request):
		school = request.options['school']
		filename = request.options['filename']
		userrole = request.options['userrole']
		import_file = os.path.join(CACHE_IMPORT_FILES, os.path.basename(filename))
		try:
			job = self.client.userimportjob.create(filename=import_file, school=school, user_role=userrole, dryrun=False)
		except (ConnectionError, ServerError, ObjectNotFound):
			raise
		os.remove(import_file)
		return {
			'id': job.id,
			'school': job.school.displayName,
			'userrole': self._parse_user_role(job.user_role)
		}

	@require_password
	@simple_response
	def poll_dry_run(self, progress_id):
		progress = self.get_progress(progress_id)
		return progress.poll()

	def get_progress(self, progress_id):
		return self._progress_objs[progress_id]

	@require_password
	@simple_response
	def jobs(self):
		return [{
			'id': job.id,
			'school': job.school.displayName,
			'creator': job.principal,
			'userrole': self._parse_user_role(job.user_role),
			'date': job.date_created.strftime("%A, %d. %B %Y %I:%M"),  # FIXME: locale aware format
			'status': self._parse_status(job.status),
		} for job in self.client.userimportjob.list(limit=20, dryrun=False, ordering='date_created')]

	def _parse_status(self, status):
		return {
			'New': _('New'),
			'Scheduled': _('Scheduled'),
			'Started': _('Started'),
			'Finished': _('Successful'),
			'Aborted': _('Aborted'),
		}.get(status, status)

	def _parse_user_role(self, role):
		return {
			'staff': _('Staff'),
			'student': _('Student'),
			'teacher': _('Teacher'),
			'teacher_and_staff': _('Teacher and Staff'),
		}.get(role, role)

	@allow_get_request
	@sanitize(job=StringSanitizer(required=True))
	def get_password(self, request):
		response = self.client.userimportjob.get(request.options['job']).password_file
		self.finished(request.id, response, mimetype='text/csv')

	@allow_get_request
	@sanitize(job=StringSanitizer(required=True))
	def get_summary(self, request):
		response = self.client.userimportjob.get(request.options['job']).summary_file
		self.finished(request.id, response, mimetype='text/csv')
