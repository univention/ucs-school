# -*- coding: utf-8 -*-
"""
Model/HTTP-API Serializers
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
import json
import datetime
import collections
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers
from djcelery.models import TaskMeta  # celery >= 4.0: django_celery_results.models.TaskResult
from .models import ConfigurationError, ConfigFile, Hook, Logfile, PasswordsFile, SummaryFile, TextArtifact, UserImportJob, School, JOB_NEW, JOB_SCHEDULED, USER_STUDENT, USER_ROLES_CHOICES
from ucsschool.http_api.import_api.import_logging import logger
from ucsschool.http_api.import_api.tasks import dry_run, import_users


class TaskResultSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = TaskMeta
		fields = ('status', 'result', 'date_done', 'traceback')
		# exclude = (,)
		read_only_fields = ('status', 'result', 'date_done', 'traceback')  # not really necessary, as the view is a ReadOnlyModelViewSet

	def to_representation(self, instance):
		# Internal representation of TaskResult.result isn't getting converted
		# automatically.
		res = super(TaskResultSerializer, self).to_representation(instance)
		res['result'] = instance.result
		return res


class UsernameField(serializers.CharField):
	"""
	Reduce a Django user object to its username string.
	"""
	def run_validation(self, data=serializers.empty):
		if data and isinstance(data, User):
			return super(UsernameField, self).run_validation(data.username)
		else:
			return super(UsernameField, self).run_validation(data)

	def to_internal_value(self, data):
		return super(UsernameField, self).to_internal_value(data.username)

	def to_representation(self, value):
		return super(UsernameField, self).to_representation(value.username)


class UserImportJobSerializer(serializers.HyperlinkedModelSerializer):
	input_file = serializers.FileField()
	log_file = serializers.URLField(read_only=True)
	password_file = serializers.URLField(read_only=True)
	summary_file = serializers.URLField(read_only=True)
	result = TaskResultSerializer(read_only=True)
	principal = UsernameField(read_only=True)
	user_role = serializers.ChoiceField(choices=USER_ROLES_CHOICES, allow_blank=True)

	# TODO: allow not setting school from below OU

	class Meta:
		model = UserImportJob
		fields = ('id', 'url', 'date_created', 'dryrun', 'input_file', 'principal', 'progress', 'result', 'school', 'source_uid', 'status', 'user_role', 'log_file', 'password_file', 'summary_file')
		# exclude = ('basedir', 'config_file', 'hooks', 'input_file', 'input_file_type', 'task_id')
		read_only_fields = ('id', 'created', 'status', 'result', 'principal', 'progress')
		# depth = 1

	def create(self, validated_data):
		"""
		Create UserImportJob object with correct values (ignore most user input)
		and queue a task.
		"""
		logger.debug('validated_data=%r', validated_data)

		# # consistency checks
		# if validated_data['school'] != validated_data['config_file'].school:
		# 	raise ConfigurationError(
		# 		'School of import job ({}) does not match School of configuration file ({}).'.format(
		# 			validated_data['school'],
		# 			validated_data['config_file'].school)
		# 	)
		#
		# if validated_data['source_uid'] != json.loads(validated_data['config_file'].text)['sourceUID']:
		# 	raise ConfigurationError(
		# 		'source_uid of import job ({}) does not match source_uid of configuration file ({}).'.format(
		# 			validated_data['source_uid'],
		# 			json.loads(validated_data['config_file'].text)['sourceUID'])
		# 	)
		#
		# if not validated_data['config_file'].enabled:
		# 	raise ConfigurationError('Configuration file {} is not enabled.'.format(validated_data['config_file']))

		if validated_data['user_role']:
			user_role = validated_data['user_role']
		else:
			# TODO: how should this be handled??
			logger.warn('user_role not set, using %r.', USER_STUDENT)
			user_role = USER_STUDENT
		del validated_data['user_role']

		# TODO: get correct config file
		validated_data['config_file'], created = ConfigFile.objects.get_or_create(
			school=validated_data['school'],
			path='/var/lib/ucs-school-import/configs/user_import.json',
			user_role=user_role
		)

		validated_data['task_id'] = ''
		validated_data['status'] = JOB_NEW
		validated_data['result'] = None
		validated_data['progress'] = json.dumps({})
		validated_data['log_file'] = None
		validated_data['basedir'] = ''
		validated_data['hooks'] = Hook.objects.filter(school=validated_data['school'], approved=True, enabled=True)
		instance = super(UserImportJobSerializer, self).create(validated_data)
		instance.basedir = os.path.join(
			settings.UCSSCHOOL_IMPORT['import_jobs_basedir'],
			str(datetime.datetime.now().year),
			str(instance.pk))
		instance.save(update_fields=('basedir',))
		if instance.dryrun:
			logger.info('Starting dry-run for ImportJob with ID %r.', instance.pk)
			result = dry_run.delay(instance.pk)
		else:
			logger.info('Starting real ImportJob with ID %r.', instance.pk)
			result = import_users.delay(instance.pk)
		instance.task_id = result.task_id
		instance.status = JOB_SCHEDULED
		instance.save(update_fields=('task_id', 'status'))
		return instance

	def to_representation(self, instance):
		instance.user_role = instance.config_file.user_role
		return super(UserImportJobSerializer, self).to_representation(instance)


class TextArtifactSerializer(serializers.HyperlinkedModelSerializer):
	userimportjob = serializers.HyperlinkedRelatedField(read_only=True, view_name='userimportjob-detail')

	class Meta:
		model = TextArtifact
		fields = ('url', 'text', 'userimportjob')
		# exclude = ()
		read_only_fields = ('text',)  # not really necessary, as the view is a ReadOnlyModelViewSet

	def to_representation(self, instance):
		# when reading an item, read logfile from disk, when listing all LogFiles don't
		res = super(TextArtifactSerializer, self).to_representation(instance)
		if not isinstance(self.instance, collections.Iterable):
			res['text'] = instance.get_text()
		return res


class LogFileSerializer(TextArtifactSerializer):
	class Meta(TextArtifactSerializer.Meta):
		model = Logfile


class PasswordFileSerializer(TextArtifactSerializer):
	class Meta(TextArtifactSerializer.Meta):
		model = PasswordsFile


class SummarySerializer(TextArtifactSerializer):
	class Meta(TextArtifactSerializer.Meta):
		model = SummaryFile


class SchoolSerializer(serializers.HyperlinkedModelSerializer):
	user_imports = serializers.URLField(read_only=True)

	class Meta:
		model = School
		fields = ('name', 'displayName', 'url', 'user_imports')
		read_only_fields = ('name', 'displayName', 'user_imports')
