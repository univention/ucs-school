# -*- coding: utf-8 -*-
"""
Database / Resource models
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

from __future__ import absolute_import, unicode_literals
import json
import codecs
import os.path
from django.db import models
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
# from django.contrib.postgres.fields import JSONField  # pgsql >= 9,4, django >= 1.9
from djcelery.models import TaskMeta  # celery >= 4.0: django_celery_results.models.TaskResult
from .logging import logger


JOB_NEW = 'New'
JOB_SCHEDULED = 'Scheduled'
JOB_STARTED = 'Started'
JOB_ABORTED = 'Aborted'
JOB_FINISHED = 'Finished'
JOB_STATES = (JOB_NEW, JOB_SCHEDULED, JOB_STARTED, JOB_ABORTED, JOB_FINISHED)
JOB_CHOICES = zip(JOB_STATES, JOB_STATES)

USER_STAFF = 'Staff'
USER_STUDENT = 'Student'
USER_TEACHER = 'Teacher'
USER_TEACHER_AND_STAFF = 'Teacher and Staff'
USER_ROLES = (USER_STAFF, USER_STUDENT, USER_TEACHER, USER_TEACHER_AND_STAFF)
USER_ROLES_CHOICES = zip([u.lower().replace(' ', '_') for u in USER_ROLES], USER_ROLES)

HOOK_TYPE_LEGACY = 'LegacyHook'
HOOK_TYPE_PYHOOK = 'PyHook'
HOOK_TYPE_TYPES = (HOOK_TYPE_LEGACY, HOOK_TYPE_PYHOOK)
HOOK_TYPE_CHOICES = zip(HOOK_TYPE_TYPES, HOOK_TYPE_TYPES)

INPUT_FILE_CSV = 'csv'
INPUT_FILE_TYPES = (INPUT_FILE_CSV, )
INPUT_FILE_CHOICES = zip(INPUT_FILE_TYPES, INPUT_FILE_TYPES)

HOOK_OBJ_GROUP = 'group'
HOOK_OBJ_OU = 'ou'
HOOK_OBJ_USER = 'user'
HOOK_OBJECT_TYPES = (HOOK_OBJ_GROUP, HOOK_OBJ_OU, HOOK_OBJ_USER)
HOOK_OBJECT_CHOICES = zip(HOOK_OBJECT_TYPES, HOOK_OBJECT_TYPES)

HOOK_ACTION_CREATE = 'create'
HOOK_ACTION_MODIFY = 'modify'
HOOK_ACTION_MOVE = 'move'
HOOK_ACTION_REMOVE = 'remove'
HOOK_ACTION_TYPES = (HOOK_ACTION_CREATE, HOOK_ACTION_MODIFY, HOOK_ACTION_MOVE, HOOK_ACTION_REMOVE)
HOOK_ACTION_CHOICES = zip(HOOK_ACTION_TYPES, HOOK_ACTION_TYPES)

HOOK_TIME_PRE = 'pre'
HOOK_TIME_POST = 'post'
HOOK_TIME_TYPES = (HOOK_TIME_PRE, HOOK_TIME_POST)
HOOK_TIME_CHOICES = zip(HOOK_TIME_TYPES, HOOK_TIME_TYPES)


class ImportHttpApiException(Exception):
	pass


class ConfigurationError(ImportHttpApiException):
	pass


class School(models.Model):
	name = models.CharField(max_length=255, primary_key=True)
	displayName = models.CharField(max_length=255, blank=True)

	def __unicode__(self):
		return self.name


class ConfigFile(models.Model):
	school = models.ForeignKey(School)
	version = models.IntegerField(default=0)
	path = models.CharField(max_length=255, blank=True)
	# text = models.TextField()  # # pgsql >= 9.4 -> JsonField()
	enabled = models.BooleanField(default=True)  # whether this config should be used for new import jobs
	user_role = models.CharField(max_length=20, choices=USER_ROLES_CHOICES)
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('school', 'user_role', '-version', '-pk')
		unique_together = (('school', 'version', 'user_role'),)

	def __unicode__(self):
		return '{} | {} (v{})'.format(self.school.name, self.user_role, self.version)

	def create_path(self, directory=None):
		if not directory:
			directory = settings.UCSSCHOOL_IMPORT['conf_store']
		return os.path.join(
			directory,
			self.school.name,
			self.user_role,
			'config_{:0>4}.json'.format(self.version))

	def dump(self, path=None):
		path = path or self.path
		directory = os.path.dirname(path)
		if not os.path.exists(directory):
			self.mkdir(directory)
		with codecs.open(path, 'wb', encoding='utf-8') as fp:
			# pgsql >= 9.4 -> JsonField
			# fp.write(json.dumps(self.text, sort_keys=True, indent=4, separators=(',', ': ')))
			fp.write(self.text)

	def mkdir(self, path, mode=0755):
		try:
			os.makedirs(path, mode)
		except os.error as exc:
			logger.exception(str(exc))
			raise


class Hook(models.Model):
	name = models.CharField(max_length=255)
	school = models.ForeignKey(School)
	version = models.IntegerField(default=0)
	type = models.CharField(max_length=10, default=HOOK_TYPE_PYHOOK, choices=HOOK_TYPE_CHOICES)
	object = models.CharField(max_length=32, default=HOOK_OBJ_USER, choices=HOOK_OBJECT_CHOICES)
	action = models.CharField(max_length=32, default=HOOK_ACTION_CREATE, choices=HOOK_ACTION_CHOICES)
	time = models.CharField(max_length=32, default=HOOK_TIME_PRE, choices=HOOK_TIME_CHOICES)
	approved = models.BooleanField(default=False)  # whether this hook has been approved by a Domain Administrator
	mandatory = models.BooleanField(default=False)  # when this is on, this hook will be used for new import jobs, can only be set by a Domain Administrator
	enabled = models.BooleanField(default=True)  # whether this hook should be used for new import jobs, can be set by School Admins
	text = models.TextField(blank=True)
	path = models.CharField(max_length=255, blank=True)
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('school', 'name', '-version', '-pk')
		unique_together = (('school', 'version', 'name'),)

	def __unicode__(self):
		return '{} | {} (v{})'.format(self.school.name, self.name, self.version)

	def create_path(self, directory=None):
		if not directory:
			directory = settings.UCSSCHOOL_IMPORT['hook_store']
		return os.path.join(
			directory,
			self.school.name,
			'{}_{}_{}.d'.format(self.object, self.action, self.time),
			'{}_{:0>4}{}'.format(self.name, self.version, '.py' if self.type == HOOK_TYPE_PYHOOK else ''))

	def dump(self, path=None):
		path = path or self.path
		directory = os.path.dirname(path)
		if not os.path.exists(directory):
			self.mkdir(directory)
		with codecs.open(path, 'wb', encoding='utf-8') as fp:
			fp.write(self.text)
		if not self.type == HOOK_TYPE_PYHOOK:
			os.chmod(path, 755)

	def mkdir(self, path, mode=0755):
		try:
			os.makedirs(path, mode)
		except os.error as exc:
			logger.exception(str(exc))
			raise


class Logfile(models.Model):
	path = models.CharField(max_length=255, unique=True)
	text = models.TextField(blank=True)

	def __unicode__(self):
		try:
			return 'Logfile of importjob {}.'.format(self.importjob.pk)
		except ObjectDoesNotExist:
			return 'Logfile of importjob n/a.'


class UserImportJob(models.Model):
	school = models.ForeignKey(School)
	source_uid = models.CharField(max_length=255)
	status = models.CharField(max_length=10, default=JOB_NEW, choices=JOB_CHOICES)
	task_id = models.CharField(max_length=40, blank=True)
	result = models.OneToOneField(TaskMeta, on_delete=models.SET_NULL, null=True, blank=True)
	principal = models.CharField(max_length=255)  # models.ForeignKey(settings.AUTH_USER_MODEL)
	log_file = models.OneToOneField(Logfile, on_delete=models.SET_NULL, null=True, blank=True)
	config_file = models.ForeignKey(ConfigFile)
	hooks = models.ManyToManyField(Hook, blank=True)
	progress = models.TextField(blank=True)  # pgsql >= 9.4 -> JsonField(blank=True)
	dryrun = models.BooleanField(default=True)
	basedir = models.CharField(max_length=255)
	created = models.DateTimeField(auto_now_add=True)
	input_file = models.FileField(upload_to='uploads/%Y-%m-%d/')
	input_file_type = models.CharField(max_length=10, default=INPUT_FILE_CSV, choices=INPUT_FILE_CHOICES)

	class Meta:
		ordering = ('-pk',)

	def __unicode__(self):
		return 'UserImportJob {} | {} ({})'.format(self.pk, self.school, self.status)

	def update_progress(self):
		# find TaskResult
		if self.task_id and not self.result:
			try:
				task = TaskMeta.objects.get(task_id=self.task_id)
				self.result = task
				logger.info('Associated TaskResult %r with UserImportJob %r.', self.task_id, self.pk)
			except ObjectDoesNotExist:
				logger.error('Could not find a TaskResult for task_id %r in UserImportJob %r.', self.task_id, self.pk)

		if not self.result:
			return

		# update progress
		if isinstance(self.result.result, basestring):
			# if JsonField: self.progress = json.loads(self.result.result)
			self.progress = self.result.result
		else:
			# if JsonField: self.progress = self.result.result
			self.progress = json.dumps(self.result.result)

		self.save(update_fields=('result', 'progress'))
