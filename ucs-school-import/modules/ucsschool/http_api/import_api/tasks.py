# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2019 Univention GmbH
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

"""
Celery tasks
"""

#
# To monitor the celery queue run in an ncurses terminal UI:
#    celery --app=ucsschool.http_api.app.celery:app control enable_events
#    celery --app=ucsschool.http_api.app.celery:app events
#

from __future__ import unicode_literals
import time
import logging
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.exceptions import ObjectDoesNotExist
from djcelery.models import TaskMeta  # celery >= 4.0: django_celery_results.models.TaskResult
from ucsschool.importer.exceptions import InitialisationError, UcsSchoolImportError, UcsSchoolImportFatalError
from ucsschool.http_api.import_api.models import UserImportJob, Logfile, PasswordsFile, SummaryFile
from ucsschool.http_api.import_api.constants import JOB_STARTED, JOB_FINISHED, JOB_ABORTED, JOB_SCHEDULED
from ucsschool.http_api.import_api.http_api_import_frontend import HttpApiImportFrontend


logger = get_task_logger(__name__)
logger.level = logging.DEBUG
logging.root.setLevel(logging.INFO)  # someone sets this to DEBUG, and then we catch all of Djangos SQL queries!


def run_import_job(task, importjob_id):
	try:
		importjob = UserImportJob.objects.get(pk=importjob_id)
	except ObjectDoesNotExist as exc:
		logger.exception(str(exc))
		raise
	timeout = 10
	while importjob.status != JOB_SCHEDULED:
		# possible race condition: we write JOB_STARTED into DB before client
		# (UserImportJobSerializer) writes JOB_SCHEDULED into DB
		time.sleep(1)
		importjob.refresh_from_db()
		timeout -= 1
		if timeout <= 0:
			raise InitialisationError('{} did not reach JOB_SCHEDULED state in 60s.'.format(importjob))
	runner = HttpApiImportFrontend(importjob, task, logger)
	importjob.log_file = Logfile.objects.create(path=runner.logfile_path)
	importjob.password_file = PasswordsFile.objects.create(path=runner.password_file)
	importjob.summary_file = SummaryFile.objects.create(path=runner.summary_file)
	importjob.status = JOB_STARTED
	runner.update_job_state(description='Initializing: 0%.')
	try:
		task_result = TaskMeta.objects.get(task_id=importjob.task_id)
		importjob.result = task_result
	except ObjectDoesNotExist:
		logger.error('Cannot find TaskMeta object after running update_job_state() for import job {!r}.'.format(importjob))

	importjob.save(update_fields=('log_file', 'password_file', 'result', 'status', 'summary_file'))

	logger.info('-- Preparing import job... --')
	success = False
	try:
		runner.prepare_import()
	except Exception as exc:
		logger.exception('An error occurred while preparing the import job: {}'.format(exc))
	else:
		# from here on we can log with the import logger
		runner.logger.info('-- Starting import job... --')
		try:
			runner.do_import()
			success = True
		except UcsSchoolImportError as exc:
			runner.errors.append(exc)
		except Exception as exc:
			runner.errors.append(UcsSchoolImportFatalError('An unknown error terminated the import job: {}'.format(exc)))
		runner.logger.info('-- Finished import. --')

	importjob = UserImportJob.objects.get(pk=importjob_id)
	importjob.status = JOB_FINISHED if success else JOB_ABORTED
	importjob.save(update_fields=('status',))
	return success, runner.user_import_summary_str


@shared_task(bind=True)
def import_users(self, importjob_id):
	logger.info('Starting UserImportJob %d (%r).', importjob_id, self)
	success, summary_str = run_import_job(self, importjob_id)
	logger.info('Finished UserImportJob %d.', importjob_id)
	return HttpApiImportFrontend.make_job_state(
		description='UserImportJob #{} ended {}.\n\n{}'.format(
			importjob_id,
			'successfully' if success else 'with error',
			summary_str
		),
		percentage=100
	)


@shared_task(bind=True)
def dry_run(self, importjob_id):
	logger.info('Starting dry run %d (%r).', importjob_id, self)
	success, summary_str = run_import_job(self, importjob_id)
	logger.info('Finished dry run %d.', importjob_id)
	return HttpApiImportFrontend.make_job_state(
		description='UserImportJob #{} (dry run) ended {}.\n\n{}'.format(
			importjob_id,
			'successfully' if success else 'with error',
			summary_str
		),
		percentage=100
	)
