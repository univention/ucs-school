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

from __future__ import unicode_literals
import json
import codecs
from ldap.filter import escape_filter_chars
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from djcelery.models import TaskMeta  # celery >= 4.0: django_celery_results.models.TaskResult
from ucsschool.importer.utils.ldap_connection import get_machine_connection
from ucsschool.http_api.import_api.import_logging import logger


JOB_NEW = 'New'
JOB_SCHEDULED = 'Scheduled'
JOB_STARTED = 'Started'
JOB_ABORTED = 'Aborted'
JOB_FINISHED = 'Finished'
JOB_STATES = (JOB_NEW, JOB_SCHEDULED, JOB_STARTED, JOB_ABORTED, JOB_FINISHED)
JOB_CHOICES = zip(JOB_STATES, JOB_STATES)

USER_STAFF = 'staff'
USER_STUDENT = 'student'
USER_TEACHER = 'teacher'
USER_TEACHER_AND_STAFF = 'teacher_and_staff'
USER_ROLES = (USER_STAFF, USER_STUDENT, USER_TEACHER, USER_TEACHER_AND_STAFF)
USER_ROLES_CHOICES = zip([u.lower().replace(' ', '_') for u in USER_ROLES], USER_ROLES)


class School(models.Model):
	name = models.CharField(max_length=255, primary_key=True)
	displayName = models.CharField(max_length=255, blank=True)

	def __unicode__(self):
		return self.name

	@staticmethod
	def _get_ous_from_ldap(ou=None):
		lo, po = get_machine_connection()
		if ou:
			return lo.search(
				filter='(&(objectClass=ucsschoolOrganizationalUnit)(ou={}))'.format(escape_filter_chars(ou)))
		else:
			return lo.search(filter='objectClass=ucsschoolOrganizationalUnit')

	@classmethod
	def update_from_ldap(cls, ou_str=None):
		"""
		Update one or all School objects from OUs in LDAP.

		:param str ou_str: name of School object to update, all will be updated if None
		:return: None
		"""
		names = list()
		for dn, ou in cls._get_ous_from_ldap(ou_str):
			name = ou['ou'][0]
			display_name = ou['displayName'][0]
			obj, created = cls.objects.get_or_create(
				name=name,
				defaults={'displayName': display_name},
			)
			if not created and obj.displayName != display_name:
				obj.displayName = display_name
				obj.save()
			names.append(name)
		if not ou_str:
			cls.objects.exclude(name__in=names).delete()


class TextArtifact(models.Model):
	path = models.CharField(max_length=255, unique=True)
	text = models.TextField(blank=True)

	class Meta:
		ordering = ('-pk',)

	def __unicode__(self):
		try:
			pk = '#{}'.format(self.get_userimportjob().pk)
		except (AttributeError, ObjectDoesNotExist):
			pk = 'n/a'
		return '{} #{} of importjob {}'.format(self.__class__.__name__, self.pk, pk)

	def get_text(self):
		if not self.text:
			try:
				with codecs.open(self.path, 'rb', encoding='utf-8') as fp:
					self.text = fp.read()
			except IOError as exc:
				logger.error('Could not read %r: %s', self.path, exc)
				return ''
		return self.text

	def get_userimportjob(self):
		return self.userimportjob


class Logfile(TextArtifact):
	def get_userimportjob(self):
		return self.userimportjob_log_file

	class Meta:
		proxy = True


class PasswordsFile(TextArtifact):
	def get_userimportjob(self):
		return self.userimportjob_password_file

	class Meta:
		proxy = True


class SummaryFile(TextArtifact):
	def get_userimportjob(self):
		return self.userimportjob_summary_file

	class Meta:
		proxy = True


class UserImportJob(models.Model):
	dryrun = models.BooleanField(default=True)
	principal = models.ForeignKey(User)
	school = models.ForeignKey(School, blank=True)
	source_uid = models.CharField(max_length=255, blank=True)
	status = models.CharField(max_length=10, default=JOB_NEW, choices=JOB_CHOICES)
	user_role = models.CharField(max_length=20, choices=USER_ROLES_CHOICES, blank=True)

	task_id = models.CharField(max_length=40, blank=True)
	result = models.OneToOneField(TaskMeta, on_delete=models.SET_NULL, null=True, blank=True)
	log_file = models.OneToOneField(Logfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='userimportjob_log_file')
	password_file = models.OneToOneField(PasswordsFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='userimportjob_password_file')
	summary_file = models.OneToOneField(SummaryFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='userimportjob_summary_file')
	basedir = models.CharField(max_length=255)
	date_created = models.DateTimeField(auto_now_add=True)
	input_file = models.FileField(upload_to='uploads/%Y-%m-%d/')

	class Meta:
		ordering = ('pk',)

	def __unicode__(self):
		return 'UserImportJob {} | {} ({})'.format(self.pk, self.school, self.status)
