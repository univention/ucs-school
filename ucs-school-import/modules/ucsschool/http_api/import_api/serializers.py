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
Model/HTTP-API Serializers
"""

from __future__ import unicode_literals
import os
import datetime
import collections
from ldap.filter import filter_format
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ParseError, PermissionDenied
from djcelery.models import TaskMeta  # celery >= 4.0: django_celery_results.models.TaskResult
from ucsschool.lib.models.utils import ucr
from ucsschool.importer.utils.ldap_connection import get_unprivileged_connection
from ucsschool.http_api.import_api.models import (
	JOB_NEW, JOB_SCHEDULED, Logfile, PasswordsFile, Role, School, SummaryFile, TextArtifact, UserImportJob)
from ucsschool.http_api.import_api.import_logging import logger
from ucsschool.http_api.import_api.tasks import dry_run, import_users
try:
	from typing import Tuple
except ImportError:
	pass


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
		# TODO: check if .result->status and .status match
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


class UserImportJobCreationValidator(object):
	def __init__(self, request):
		self.request = request

	def __call__(self, data):
		if not data.get('school'):
			raise ParseError('Either a school must be submitted or the request be run at "<school-URL>/imports/users".')
		if not data.get('user_role'):
			raise ParseError('NotYetImplemented: Import jobs can currently only be run for one user role at a time.')
		if not self.is_user_school_role_combination_allowed(
			username=self.request.user.username,
			school=data['school'].name,
			role=data['user_role']
		):
			msg = 'User {!r} is not allowed to start an import job for school {!r} and role {!r}.'.format(
				self.request.user.username, data['school'].name, data['user_role']
				)
			logger.error(msg)
			raise PermissionDenied(msg)

	@classmethod
	def is_user_school_role_combination_allowed(cls, username, school, role):
		lo, po = get_unprivileged_connection()

		# filter_format() will escape '*' as argument
		filter_s = '(&(objectClass=ucsschoolImportGroup)(ucsschoolImportRole={role})(ucsschoolImportSchool={school})(memberUid=%s))'.format(
			role='*' if role == '*' else '%s',
			school='*' if school == '*' else '%s',
		)
		args = []
		if role != '*':
			args.append(role)
		if school != '*':
			args.append(school)
		args.append(username)
		args = tuple(args)
		res = lo.searchDn(filter_format(filter_s, args))
		if not res:
			logger.error('Not allowed: username: %r school: %r role: %r', username, school, role)
		return bool(res)


class UserImportJobSerializer(serializers.HyperlinkedModelSerializer):
	input_file = serializers.FileField()
	log_file = serializers.URLField(read_only=True)
	password_file = serializers.URLField(read_only=True)
	summary_file = serializers.URLField(read_only=True)
	result = TaskResultSerializer(read_only=True)
	principal = UsernameField(read_only=True)

	class Meta:
		model = UserImportJob
		fields = ('id', 'url', 'date_created', 'dryrun', 'input_file', 'principal', 'result', 'school', 'status', 'user_role', 'log_file', 'password_file', 'summary_file')
		read_only_fields = ('id', 'created', 'status', 'result', 'principal', 'source_uid')

	def get_validators(self):
		validators = super(UserImportJobSerializer, self).get_validators()
		validators.append(UserImportJobCreationValidator(self.context['request']))
		return validators

	def create(self, validated_data):
		"""
		Create UserImportJob object with correct values (ignore most user input)
		and queue a task.
		"""
		logger.debug('validated_data=%r', validated_data)

		validated_data['task_id'] = ''
		validated_data['status'] = JOB_NEW
		validated_data['result'] = None
		validated_data['log_file'] = None
		validated_data['basedir'] = ''
		if ucr.is_true('ucsschool/import/http_api/set_source_uid', True):
			validated_data['source_uid'] = '{}-{}'.format(validated_data['school'].name, validated_data['user_role']).lower()
			logger.info('Settings source_uid to %r.', validated_data['source_uid'])
		else:
			logger.info('Keeping source_uid from configuration.')
		instance = super(UserImportJobSerializer, self).create(validated_data)
		instance.basedir = os.path.join(
			settings.UCSSCHOOL_IMPORT['import_jobs_basedir'],
			str(datetime.datetime.now().year),
			str(instance.pk))
		instance.save(update_fields=('basedir',))
		if instance.dryrun:
			logger.info('Scheduling dry-run for ImportJob with ID %r.', instance.pk)
			result = dry_run.delay(instance.pk)
		else:
			logger.info('Scheduling real ImportJob with ID %r.', instance.pk)
			result = import_users.delay(instance.pk)
		instance.task_id = result.task_id
		instance.status = JOB_SCHEDULED
		instance.save(update_fields=('task_id', 'status'))
		return instance


class TextArtifactSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = TextArtifact
		fields = ('url', 'text')  # type: Tuple
		# exclude = ()
		read_only_fields = ('text',)  # not really necessary, as the view is a ReadOnlyModelViewSet

	def to_representation(self, instance):
		# when reading an item, read logfile from disk, when listing all LogFiles don't
		res = super(TextArtifactSerializer, self).to_representation(instance)
		if not isinstance(self.instance, collections.Iterable):
			res['text'] = instance.get_text()
		return res


class LogFileSerializer(TextArtifactSerializer):
	userimportjob_log_file = serializers.HyperlinkedRelatedField(read_only=True, view_name='userimportjob-detail')

	class Meta(TextArtifactSerializer.Meta):
		model = Logfile
		userimportjob_related_name = 'userimportjob_log_file'
		fields = ('url', 'text', userimportjob_related_name)


class PasswordFileSerializer(TextArtifactSerializer):
	userimportjob_password_file = serializers.HyperlinkedRelatedField(read_only=True, view_name='userimportjob-detail')

	class Meta(TextArtifactSerializer.Meta):
		model = PasswordsFile
		userimportjob_related_name = 'userimportjob_password_file'
		fields = ('url', 'text', userimportjob_related_name)


class SummarySerializer(TextArtifactSerializer):
	userimportjob_summary_file = serializers.HyperlinkedRelatedField(read_only=True, view_name='userimportjob-detail')

	class Meta(TextArtifactSerializer.Meta):
		model = SummaryFile
		userimportjob_related_name = 'userimportjob_summary_file'
		fields = ('url', 'text', userimportjob_related_name)


class RoleSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = Role
		fields = ('name', 'displayName', 'url')
		read_only_fields = ('name', 'displayName')


class SchoolSerializer(serializers.HyperlinkedModelSerializer):
	roles = serializers.URLField(read_only=True)
	user_imports = serializers.URLField(read_only=True)

	class Meta:
		model = School
		fields = ('name', 'displayName', 'url', 'roles', 'user_imports')
		read_only_fields = ('name', 'displayName', 'roles', 'user_imports')
