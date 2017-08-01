# -*- coding: utf-8 -*-
"""
UCS@school import frontent class
"""
#
# Univention UCS@school
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

from __future__ import unicode_literals
import os
import errno
import shutil
import pprint
from django.conf import settings
from celery.states import STARTED as CELERY_STATES_STARTED
from ucsschool.importer.frontend.user_import_cmdline import UserImportCommandLine
from ucsschool.importer.exceptions import InitialisationError
from ucsschool.http_api.import_api.models import Hook, HOOK_TYPE_LEGACY, HOOK_TYPE_PYHOOK


class ArgParseFake(object):
	def __init__(self, **kwargs):
		for k, v in kwargs.items():
			setattr(self, k, v)


class HttpApiImportFrontend(UserImportCommandLine):
	"""
	Fake cmdline import frontend class. Simulates argparse results and starts import.
	"""
	# TODO: replace this with a class with an interface appropriate for remote API calls.
	# Especially we have to (not) catch the exceptions here, so they end up in the TaskResult.

	def __init__(self, import_job, task, logger):
		self.import_job = import_job
		self.task = task
		self.task_logger = logger
		self.basedir = self.import_job.basedir
		self.hook_dir = os.path.join(self.basedir, 'hooks')
		self.pyhook_dir = os.path.join(self.basedir, 'pyhooks')
		for dir_ in (self.basedir, self.hook_dir, self.pyhook_dir):
			try:
				os.makedirs(dir_, 0755)
			except os.error as exc:
				raise InitialisationError(
					'Cannot create directory "{}" for import job {}: {}'.format(dir_, self.import_job.pk, str(exc)))
		self.logfile_path = os.path.join(self.basedir, 'ucs-school-import.log')
		self.password_file = os.path.join(
			self.basedir,
			settings.UCSSCHOOL_IMPORT['new_user_passwords_filename']
		)
		self.summary_file = os.path.join(
					self.basedir,
					settings.UCSSCHOOL_IMPORT['user_import_summary_filename'])
		self.task_logger.info('Logging for import job %r will go to %r.', self.import_job.pk, self.logfile_path)
		# task_handler = logging.FileHandler(os.path.join(self.basedir, 'task.log'), encoding='utf-8')
		# task_handler.setLevel(logging.DEBUG)
		# task_handler.setFormatter(logging.Formatter(
		# 	datefmt=settings.UCSSCHOOL_IMPORT['logging']['api_datefmt'],
		# 	fmt=settings.CELERYD_TASK_LOG_FORMAT))
		# task_handler.name = 'import job {}'.format(self.import_job.pk)
		# self.logger.info('Adding logging handler for UserImportJob %r.', self.import_job.pk)
		# self.logger.addHandler(task_handler)
		self.data_path = os.path.join(self.basedir, os.path.basename(self.import_job.input_file.name))
		data_source_path = os.path.join(settings.MEDIA_ROOT, self.import_job.input_file.name)
		shutil.copy2(data_source_path, self.data_path)
		for hook in self.import_job.hooks.all():
			dir_, filename_ = os.path.split(hook.create_path())
			dir_ = {
				HOOK_TYPE_LEGACY: self.hook_dir,
				HOOK_TYPE_PYHOOK: self.pyhook_dir,
			}[hook.type]
			if hook.type == HOOK_TYPE_LEGACY:
				dir_ = os.path.join(dir_, '{}_{}_{}.d'.format(hook.object, hook.action, hook.time))
			path = os.path.join(dir_, filename_)
			hook.dump(path)
			self.logger.info('Wrote %s %r to %r.', hook.type, hook, path)
		super(HttpApiImportFrontend, self).__init__()

	def parse_cmdline(self):
		# TODO: support '--no-delete' ?
		self.args = ArgParseFake(
			conffile=None,  # see self.configuration_files
			dry_run=self.import_job.dryrun,
			infile=self.data_path,
			logfile=self.logfile_path,
			school=self.import_job.config_file.school.name,
			sourceUID=self.import_job.source_uid,
			user_role=self.import_job.config_file.user_role,
			verbose=True)  # TODO: read verbose from self.import_job.config_file['verbose']
		self.args.settings = {
			'dry_run': self.import_job.dryrun,
			'hooks_dir_legacy': self.hook_dir,
			'hooks_dir_pyhook': self.pyhook_dir,
			'input': {'filename': self.data_path, 'type': self.import_job.input_file_type.lower()},
			'logfile': self.logfile_path,
			'output': {
				'new_user_passwords': self.password_file,
				'user_import_summary': self.summary_file,
			},
			'school': self.import_job.config_file.school.name,
			'sourceUID': self.import_job.source_uid,
			'update_function': self.update_job_state,
			'user_role': self.import_job.config_file.user_role,
			'verbose': True  # TODO: read verbose from self.import_job.config_file['verbose']
		}
		self.task_logger.info('HttpApiImportFrontend: Set up import job with args:\n%s', pprint.pformat(self.args.__dict__))
		return self.args

	@property
	def configuration_files(self):
		conf_files = super(HttpApiImportFrontend, self).configuration_files
		conf_files_job = list()
		# prefix all file names, so they never clash
		num = 0
		for num, cf in enumerate(conf_files):
			try:
				target = os.path.join(self.basedir, '{}_{}'.format(num, os.path.basename(cf)))
				shutil.copy2(cf, target)
				conf_files_job.append(target)
				self.logger.info('Copied %r to %r.', cf, target)
			except IOError as exc:
				if exc.errno == errno.ENOENT:
					# probably /var/lib/..
					self.logger.warn('Ignoring not existing configuration file %r.', cf)
				else:
					raise
		num += 1
		dir_, filename_ = os.path.split(self.import_job.config_file.create_path())
		importjob_config_path = os.path.join(self.basedir, '{}_{}'.format(num, filename_))
		self.import_job.config_file.dump(importjob_config_path)
		conf_files_job.append(importjob_config_path)
		self.logger.info('Stored %r in %r.', self.import_job.config_file, importjob_config_path)
		return conf_files_job

	def update_job_state(self, done=0, total=0):
		"""
		Update import job task state.

		:param done: int: number of user currently being imported
		:param total: int: total users to import
		:return: None
		"""
		self.task.update_state(meta=dict(
			state=CELERY_STATES_STARTED,
			progress=dict(
				done=done,
				total=total
			)
		))
