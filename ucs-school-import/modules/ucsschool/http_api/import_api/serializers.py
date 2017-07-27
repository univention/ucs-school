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
from django.conf import settings
from rest_framework import serializers
from djcelery.models import TaskMeta  # celery >= 4.0: django_celery_results.models.TaskResult
from .models import ConfigurationError, ConfigFile, Hook, Logfile, UserImportJob, School, JOB_NEW, JOB_SCHEDULED, USER_STUDENT
from ucsschool.http_api.import_api.import_logging import logger
from ucsschool.http_api.import_api.tasks import dry_run, import_users


class UserImportJobSerializer(serializers.HyperlinkedModelSerializer):
	input_file = serializers.FileField()

	class Meta:
		model = UserImportJob
		# fields = (,)
		exclude = ('task_id', 'basedir', 'config_file')
		read_only_fields = (
			'created', 'status', 'task_id', 'result', 'principal', 'log_file', 'config_file', 'hooks', 'progress', 'basedir', 'input_file', 'input_file_type')  # not really necessary, as the view is Create & Read only

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

		# TODO: get correct config file
		validated_data['config_file'], created = ConfigFile.objects.get_or_create(
			school=validated_data['school'],
			path='/var/lib/ucs-school-import/configs/user_import.json',
			user_role=USER_STUDENT
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


class LogFileSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = Logfile
		fields = ('url', 'text', 'importjob')
		# exclude = ()
		read_only_fields = ('path', 'text')  # not really necessary, as the view is a ReadOnlyModelViewSet


class SchoolSerializer(serializers.HyperlinkedModelSerializer):
	user_import = serializers.URLField(read_only=True)

	class Meta:
		model = School
		# fields = (,)
		# exclude = (,)
		read_only_fields = ('name', 'displayName', 'user_import')  # not really necessary, as the view is a ReadOnlyModelViewSet


class TaskResultSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = TaskMeta
		fields = ('url', 'status', 'result', 'date_done', 'traceback', 'importjob')
		# exclude = ()  # ('hidden',)
		read_only_fields = ('status', 'result', 'date_done', 'traceback')  # not really necessary, as the view is a ReadOnlyModelViewSet
