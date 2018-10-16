# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2018 Univention GmbH
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
UCS@school import frontend class
"""

from __future__ import unicode_literals
import os
import stat
import errno
import shutil
import pprint
from django.conf import settings
from celery.states import STARTED as CELERY_STATES_STARTED
from ucsschool.importer.factory import load_class
from ucsschool.importer.frontend.user_import_cmdline import UserImportCommandLine
from ucsschool.importer.exceptions import InitialisationError
from ucsschool.http_api.import_api.utils import get_wsgi_uid_gid


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

	http_api_specific_config = 'user_import_http-api.json'
	reader_class = 'ucsschool.importer.reader.http_api_csv_reader.HttpApiCsvReader'

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
		self.wsgi_uid, self.wsgi_gid = get_wsgi_uid_gid()
		data_source_path = os.path.join(settings.MEDIA_ROOT, self.import_job.input_file.name)

		try:
			os.makedirs(
				self.basedir,
				stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXOTH
			)  # 751: higher directories may be owned by root, but will be traversable
			os.chown(self.basedir, self.wsgi_uid, self.wsgi_gid)
			os.chmod(self.basedir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)  # secure mode for our directory
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

		# set owner of password and summary files, so the WSGI user will be able to read them later
		for path in (self.password_file, self.summary_file):
			with open(path, 'ab') as fp:
				os.fchown(fp.fileno(), self.wsgi_uid, self.wsgi_gid)
				os.fchmod(fp.fileno(), stat.S_IRUSR | stat.S_IWUSR)

		super(HttpApiImportFrontend, self).__init__()

	def parse_cmdline(self):
		self.args = ArgParseFake(
			conffile=None,  # see self.configuration_files
			dry_run=self.import_job.dryrun,
			infile=self.data_path,
			logfile=self.logfile_path,
			school=self.import_job.school.name,
			user_role=self.import_job.user_role,
			verbose=True)
		if self.import_job.source_uid:
			self.args.sourceUID = self.import_job.source_uid
		self.args.settings = {
			'dry_run': self.import_job.dryrun,
			'hooks_dir_legacy': self.hook_dir,
			'hooks_dir_pyhook': self.pyhook_dir,
			'input': {'filename': self.data_path},
			'logfile': self.logfile_path,
			'output': {
				'new_user_passwords': self.password_file,
				'user_import_summary': self.summary_file,
			},
			'school': self.import_job.school.name,
			'progress_notification_function': self.update_job_state,
			'user_role': self.import_job.user_role,
		}
		if self.import_job.source_uid:
			self.args.settings['sourceUID'] = self.import_job.source_uid
		self.task_logger.info('HttpApiImportFrontend: Set up import job with args:\n%s', pprint.pformat(self.args.__dict__))
		return self.args

	def setup_logging(self, stdout=False, filename=None, uid=None, gid=None, mode=None):
		return super(HttpApiImportFrontend, self).setup_logging(
			stdout=stdout,
			filename=filename,
			uid=self.wsgi_uid,
			gid=self.wsgi_gid,
			mode=stat.S_IRUSR | stat.S_IWUSR
		)

	@property
	def configuration_files(self):
		"""
		User import configuration files.

		:return: list of filenames
		:rtype: list(str)
		"""
		conf_files = super(HttpApiImportFrontend, self).configuration_files
		conf_files.append(os.path.join('/usr/share/ucs-school-import/configs', self.http_api_specific_config))
		conf_files.append(os.path.join('/var/lib/ucs-school-import/configs', self.http_api_specific_config))
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
		# use OU specific configuration file
		ou_config_filename = '{}.json'.format(self.import_job.school.name).lower()
		ou_config_source_path = os.path.join('/var/lib/ucs-school-import/configs', ou_config_filename)
		if os.path.exists(ou_config_source_path):
			numbered_ou_config_file = os.path.join(self.basedir, '{}_{}'.format(num, ou_config_filename))
			shutil.copy2(ou_config_source_path, numbered_ou_config_file)
			conf_files_job.append(numbered_ou_config_file)
			self.logger.info('Copied %r to %r.', ou_config_source_path, numbered_ou_config_file)
		else:
			self.logger.info('No school specific configuration found (%r).', ou_config_source_path)
		return conf_files_job

	@staticmethod
	def make_job_state(description, percentage=0, done=0, total=0, celery_task_state=CELERY_STATES_STARTED, **kwargs):
		kwargs.update(dict(
			description=description,
			percentage=percentage,
			done=done,
			total=total,
		))
		return kwargs

	def setup_config(self):
		# Bug #47156: check that the used CSV reader is HttpApiCsvReader or a subclass
		error_msg = (
			'The CSV reader class for the HTTP-API import must be {!r} (or derived from it).'.format(self.reader_class))
		config = super(HttpApiImportFrontend, self).setup_config()
		try:
			reader_class_name = config['classes']['reader']
		except KeyError:
			raise InitialisationError(error_msg)

		if reader_class_name != self.reader_class:
			config_reader_class = load_class(reader_class_name)
			http_reader_class = load_class(self.reader_class)
			if not issubclass(config_reader_class, http_reader_class):
				raise InitialisationError(error_msg)
		return config

	def update_job_state(self, description, percentage=0, done=0, total=0, celery_task_state=CELERY_STATES_STARTED, **kwargs):
		"""
		Update import job task state.

		:param str description: the description
		:param int percentage: progress
		:param int done: if it was done
		:param int total: number of objects
		:param celery.states celery_task_state: one of the states from celery.states
		:param dict kwargs: will be saved into job result.meta together with other arguments
		:return: None
		"""
		state = self.make_job_state(description, percentage, done, total, **kwargs)
		try:
			self.task.update_state(
				state=CELERY_STATES_STARTED,
				meta=state
			)
		except Exception as exc:
			self.task_logger.exception('Exception in update_job_state() state=%r: %r', state, exc)
