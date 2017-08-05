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
		self.logfile_path = os.path.join(self.basedir, 'ucs-school-import.log')
		self.password_file = os.path.join(self.basedir, settings.UCSSCHOOL_IMPORT['new_user_passwords_filename'])
		self.summary_file = os.path.join(self.basedir, settings.UCSSCHOOL_IMPORT['user_import_summary_filename'])
		self.task_logger.info('Logging for import job %r will go to %r.', self.import_job.pk, self.logfile_path)
		self.data_path = os.path.join(self.basedir, os.path.basename(self.import_job.input_file.name))
		data_source_path = os.path.join(settings.MEDIA_ROOT, self.import_job.input_file.name)

		try:
			os.makedirs(self.basedir, 0755)
		except os.error as exc:
			raise InitialisationError('Cannot create directory {!r} for import job {!r}: {}'.format(
				self.basedir, self.import_job.pk, str(exc)))

		# copy input (csv) file
		shutil.copy2(data_source_path, self.data_path)
		# copy hooks (to complete isolated and fully documented import job)
		# in the future support per-OU hook configurations?
		shutil.copytree(
			'/usr/share/ucs-school-import/hooks',
			self.hook_dir,
			ignore=shutil.ignore_patterns('computer_*', 'network_*', 'printer_*', 'router_*'))
		shutil.copytree(
			'/usr/share/ucs-school-import/pyhooks',
			self.pyhook_dir,
			ignore=shutil.ignore_patterns('*.py?')
		)
		super(HttpApiImportFrontend, self).__init__()

	def parse_cmdline(self):
		# TODO: support '--no-delete' ?
		self.args = ArgParseFake(
			conffile=None,  # see self.configuration_files
			dry_run=self.import_job.dryrun,
			infile=self.data_path,
			logfile=self.logfile_path,
			school=self.import_job.school.name,
			sourceUID=self.import_job.source_uid,
			user_role=self.import_job.user_role,
			verbose=True)
		self.args.settings = {
			'dry_run': self.import_job.dryrun,
			'hooks_dir_legacy': self.hook_dir,    # TODO: adapt import framework to support hook dirs
			'hooks_dir_pyhook': self.pyhook_dir,  # TODO: adapt import framework to support hook dirs
			'input': {'filename': self.data_path},
			'logfile': self.logfile_path,
			'output': {
				'new_user_passwords': self.password_file,
				'user_import_summary': self.summary_file,
			},
			'school': self.import_job.school.name,
			'sourceUID': self.import_job.source_uid,
			'update_function': self.update_job_state,
			'user_role': self.import_job.user_role,
			'verbose': True,
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
		# TODO: OU specific conf file
		ou_config_file = '/usr/share/ucs-school-import/configs/ucs-school-testuser-import.json'
		dir_, filename_ = os.path.split(ou_config_file)
		numbered_ou_config_file = os.path.join(self.basedir, '{}_{}'.format(num, filename_))
		shutil.copy2(ou_config_file, numbered_ou_config_file)
		conf_files_job.append(numbered_ou_config_file)
		self.logger.info('Copied %r to %r.', ou_config_file, numbered_ou_config_file)
		# TODO: consistency check: is sourceUID in configfile == sourceUID in parameters?
		# TODO: or remove sourceUID from parameters?
		return conf_files_job

	def update_job_state(self, done=0, total=0):
		"""
		Update import job task state.

		:param done: int: number of user currently being imported
		:param total: int: total users to import
		:return: None
		"""
		# TODO: adapt import framework to support this
		self.logger.warn('*** update_job_state()')
		self.task.update_state(meta=dict(
			state=CELERY_STATES_STARTED,
			progress=dict(
				done=done,
				total=total
			)
		))
