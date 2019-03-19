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
Database / Resource models
"""

from __future__ import unicode_literals
import codecs
import logging
from ldap.filter import escape_filter_chars
from django.db import models
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from djcelery.models import TaskMeta  # celery >= 4.0: django_celery_results.models.TaskResult
import univention.admin.localization
from ucsschool.importer.utils.ldap_connection import get_unprivileged_connection
from .constants import (
	JOB_ABORTED, JOB_CHOICES, JOB_FINISHED, JOB_NEW, JOB_SCHEDULED, JOB_STARTED, JOB_STATES
)

USER_STAFF = 'staff'
USER_STUDENT = 'student'
USER_TEACHER = 'teacher'
USER_TEACHER_AND_STAFF = 'teacher_and_staff'
USER_ROLES = (USER_STAFF, USER_STUDENT, USER_TEACHER, USER_TEACHER_AND_STAFF)
USER_ROLES_CHOICES = zip([u.lower().replace(' ', '_') for u in USER_ROLES], USER_ROLES)

translation = univention.admin.localization.translation('ucs-school-import-http-api')
_ = translation.translate

USER_ROLE_TRANS = {
	USER_STAFF: _('staff'),
	USER_STUDENT: _('student'),
	USER_TEACHER: _('teacher'),
	USER_TEACHER_AND_STAFF: _('teacher_and_staff'),
}


class Role(models.Model):
	name = models.CharField(max_length=255, primary_key=True)
	displayName = models.CharField(max_length=255, blank=True)

	def __unicode__(self):
		return self.name

	@classmethod
	def update_from_ldap(cls):
		"""
		Update Role objects from LDAP. Currently static values are used and no
		LDAP query is done. This might change in the future.

		:return: None
		"""
		names = list()
		for role in USER_ROLES:
			name = role
			display_name = _(USER_ROLE_TRANS[role])
			obj, created = cls.objects.get_or_create(
				name=name,
				defaults={'displayName': display_name},
			)
			if not created and obj.displayName != display_name:
				obj.displayName = display_name
				obj.save()
			names.append(name)
		# delete unknown roles
		cls.objects.exclude(name__in=names).delete()

	class Meta:
		ordering = ('name',)


#
# AccessRule and Context are currently neither used, not tested. We fetch the
# required information in the FilterBackend and Permission classes (views.py)
# directly from LDAP. This is here to show how a permission representation
# (compatible with the above Role class) could be modeled in Django.
#
# To use this, install the code, and create and activate the required
# migrations with:
# /usr/share/pyshared/ucsschool/http_api/manage.py makemigrations
# /usr/share/pyshared/ucsschool/http_api/manage.py migrate
#

# from django.contrib.auth import get_user_model
# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes.models import ContentType

# CONTEXT_TYPE_SCHOOL = 'school'

# class Context(models.Model):
# 	type = models.CharField(max_length=255, primary_key=True)
#
# 	content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
# 	object_id = models.CharField(max_length=255)
# 	content_object = GenericForeignKey('content_type', 'object_id')
#
# 	def __unicode__(self):
# 		return 'Context(type={!r}, content_object={})'.format(self.type, self.content_object)
#
# 	@classmethod
# 	def update_school_contexts(cls):
# 		School.update_from_ldap()
# 		existing_school_objs = School.objects.all()
# 		ct_school = ContentType.objects.get(app_label='import_api', model='school')
# 		for context in list(cls.objects.filter(type=CONTEXT_TYPE_SCHOOL, content_type=ct_school)):
# 			if context.content_object not in existing_school_objs:
# 				context.delete()
# 		existing_school_objs_in_contexts = cls.objects.filter(type=CONTEXT_TYPE_SCHOOL).values('content_object')
# 		for school_obj in set(existing_school_objs) - set(existing_school_objs_in_contexts):
# 			cls.objects.create(type=CONTEXT_TYPE_SCHOOL, content_object=school_obj)


# class AccessRule(models.Model):
# 	access = models.BooleanField(default=True)
# 	contexts = models.ManyToManyField(Context)
# 	roles = models.ManyToManyField(Role)
# 	users = models.ManyToManyField(settings.AUTH_USER_MODEL)
#
# 	import_group_name = models.CharField(max_length=255)
#
# 	def __unicode__(self):
# 		return 'AccessRule(context={!r}, roles={}, access={!r} import_group={!r})'.format(
# 			self.context,
# 			[r.name for r in self.roles.all()],
# 			self.access,
# 			self.import_group_name
# 		)
#
# 	@classmethod
# 	def update_from_ldap(cls):
# 		"""
# 		Update AccessRule objects from LDAP (reading ucsschoolImportGroup
# 		groups).
#
# 		:return: None
# 		"""
# 		names = []
# 		lo, po = get_unprivileged_connection()
# 		for dn, import_group in lo.search('(objectClass=ucsschoolImportGroup)'):
# 			name = import_group['cn'][0]
# 			try:
# 				obj, _created = cls.objects.get_or_create(import_group_name=name)
# 			except cls.DoesNotExist:
# 				obj = cls.objects.create(import_group_name=name)
# 			users = cls._get_users(import_group['memberUid'])
# 			roles = cls._get_roles(import_group['ucsschoolImportRole'])
# 			contexts = cls._get_school_contexts(import_group['ucsschoolImportSchool'])
# 			if obj.users != users or obj.roles != roles or obj.contexts != contexts:
# 				obj.users = users
# 				obj.roles = roles
# 				obj.contexts = contexts
# 				obj.save()
# 			names.append(name)
# 		cls.objects.exclude(import_group_name__in=names).delete()
#
# 	@classmethod
# 	def _get_users(cls, users):
# 		UserModel = get_user_model()
# 		username_list_filter = '{}__in'.format(UserModel.USERNAME_FIELD)
#
# 		existing_users = UserModel._default_manager.filter(**{username_list_filter: users})
# 		existing_user_names = existing_users.values_list('username', flat=True)
# 		for username in set(users) - set(existing_user_names):
# 			UserModel._default_manager.create_user(username)
# 		return UserModel._default_manager.filter(**{username_list_filter: users})
#
# 	@classmethod
# 	def _get_roles(cls, roles):
# 		Role.update_from_ldap()
# 		existing_roles = Role.objects.filter(name__in=roles)
# 		missing_roles = set(roles) - set(r.name for r in existing_roles)
# 		if missing_roles:
# 			raise RuntimeError('Cannot get unknown role(s): {!r}.'.format(missing_roles))
# 		return existing_roles
#
# 	@classmethod
# 	def _get_school_contexts(cls, schools):
# 		Context.update_school_contexts()  # will also update Schools
# 		existing_schools = School.objects.filter(name__in=schools)
# 		missing_schools = set(schools) - set(s.name for s in existing_schools)
# 		if missing_schools:
# 			raise RuntimeError('Cannot get context for unknown school(s): {!r}.'.format(missing_schools))
# 		ct_school = ContentType.objects.get(app_label='import_api', model='school')
# 		return Context.objects.filter(type=CONTEXT_TYPE_SCHOOL, content_type=ct_school, object_id__in=schools)


class School(models.Model):
	name = models.CharField(max_length=255, primary_key=True)
	displayName = models.CharField(max_length=255, blank=True)

	def __unicode__(self):
		return self.name

	@staticmethod
	def _get_ous_from_ldap(ou=None):
		lo, po = get_unprivileged_connection()
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
		res = cls._get_ous_from_ldap(ou_str)
		if ou_str and not res:
			raise RuntimeError('Unknown school {!r}.'.format(ou_str))
		for dn, ou in res:
			name = ou['ou'][0]
			display_name = ou.get('displayName', [name])[0]
			obj, created = cls.objects.get_or_create(
				name=name,
				defaults={'displayName': display_name},
			)
			if not created and obj.displayName != display_name:
				obj.displayName = display_name
				obj.save()
			names.append(name)
		if not ou_str:
			# delete OUs not in LDAP (anymore)
			cls.objects.exclude(name__in=names).delete()

	class Meta:
		ordering = ('name',)


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
				logger = logging.getLogger(__name__)
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
	principal = models.ForeignKey(settings.AUTH_USER_MODEL)
	school = models.ForeignKey(School, blank=True)
	source_uid = models.CharField(max_length=255, blank=True)
	status = models.CharField(max_length=10, default=JOB_NEW, choices=JOB_CHOICES)
	user_role = models.CharField(max_length=20, choices=USER_ROLES_CHOICES, blank=True)
	# TODO: user_role = models.ForeignKey(Role, blank=True)

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
