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
Django Views
"""

from __future__ import unicode_literals
import logging
try:
	from urllib2 import urlparse
except ImportError:
	from urllib import parse as urlparse  # Python3
from ldap.filter import filter_format
import lazy_object_proxy
from django.db.models import Q
from django.http import Http404
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.exceptions import ParseError
from rest_framework.decorators import detail_route
from rest_framework.filters import BaseFilterBackend, OrderingFilter
from rest_framework.permissions import BasePermission, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from django_filters import CharFilter, MultipleChoiceFilter
from ucsschool.importer.utils.ldap_connection import get_unprivileged_connection
from .models import JOB_CHOICES, Role, School, TextArtifact, UserImportJob
from .serializers import (
	UserImportJobCreationValidator,
	UserImportJobSerializer,
	LogFileSerializer,
	PasswordFileSerializer,
	RoleSerializer,
	SummarySerializer,
	SchoolSerializer,
)


logger = lazy_object_proxy.Proxy(lambda: logging.Logger(__name__))  # type: logging.Logger


class UserImportJobFilter(FilterSet):
	"""
	Used to filter the principal field by 'username' (DjangoFilterBackend
	works automatically only on pk).
	"""
	principal = CharFilter(method='principal_filter')
	status = MultipleChoiceFilter(choices=JOB_CHOICES)

	class Meta:
		model = UserImportJob
		fields = ['id', 'dryrun', 'principal', 'school', 'source_uid', 'status', 'user_role']

	@staticmethod
	def principal_filter(queryset, name, value):
		return queryset.filter(principal__username=value)


class RoleFilterBackend(BaseFilterBackend):
	"""
	Used to list only Roles the user has any permissions on.
	"""
	filter_s = '(&(objectClass=ucsschoolImportGroup)(ucsschoolImportRole=*)(ucsschoolImportSchool={})(memberUid=%s))'
	filter_attrs = (str('ucsschoolImportRole'), str('ucsschoolImportSchool'))  # unicode_literals + python-ldap = TypeError

	@classmethod
	def _build_query(cls, username, school):
		lo, po = get_unprivileged_connection()
		if school == '*':
			# prevent filter_format() from escaping '*'
			filter_s = filter_format(cls.filter_s.format('*'), (username,))
		else:
			filter_s = filter_format(cls.filter_s.format('%s'), (school, username))
		ldap_result = lo.search(filter_s, attr=cls.filter_attrs)
		role_names = []
		for _dn, result_dict in ldap_result:
			role_names.extend(result_dict['ucsschoolImportRole'])
		return Q(name__in=role_names)

	def filter_queryset(self, request, queryset, view):
		try:
			school = view._school
		except AttributeError:
			school = '*'
		query = self._build_query(request.user.username, school)
		if not query:
			logger.warn('User %r has no permissions at all.', request.user)
			return queryset.none()
		return queryset.filter(query)


class SchoolFilterBackend(BaseFilterBackend):
	"""
	Used to list only Schools the user has any permissions on.
	"""
	filter_s = '(&(objectClass=ucsschoolImportGroup)(ucsschoolImportRole=*)(ucsschoolImportSchool=*)(memberUid=%s))'
	filter_attrs = (str('ucsschoolImportSchool'),)  # unicode_literals + python-ldap = TypeError

	@classmethod
	def _build_query(cls, username):
		lo, po = get_unprivileged_connection()
		filter_s = filter_format(cls.filter_s, (username,))
		ldap_result = lo.search(filter_s, attr=cls.filter_attrs)
		school_names = []
		for _dn, result_dict in ldap_result:
			school_names.extend(result_dict['ucsschoolImportSchool'])
		return Q(name__in=school_names)

	def filter_queryset(self, request, queryset, view):
		query = self._build_query(request.user.username)
		if not query:
			logger.warn('User %r has no permissions at all.', request.user)
			return queryset.none()
		return queryset.filter(query)


class UserImportJobFilterBackend(BaseFilterBackend):
	"""
	Used to list only ImportJobs the user has any permissions on.
	"""
	filter_s = '(&(objectClass=ucsschoolImportGroup)(ucsschoolImportRole=*)(ucsschoolImportSchool=*)(memberUid=%s))'
	filter_attrs = (str('ucsschoolImportRole'), str('ucsschoolImportSchool'))  # unicode_literals + python-ldap = TypeError

	@classmethod
	def _build_query(cls, username):
		lo, po = get_unprivileged_connection()
		filter_s = filter_format(cls.filter_s, (username,))
		ldap_result = lo.search(filter_s, attr=cls.filter_attrs)
		query = None
		for _dn, result_dict in ldap_result:
			q = Q(
				school__name__in=result_dict['ucsschoolImportSchool'],
				user_role__in=result_dict['ucsschoolImportRole']
			)  # AND
			try:
				query |= q  # OR
			except TypeError:
				query = q   # query was None
		return query

	def filter_queryset(self, request, queryset, view):
		query = self._build_query(request.user.username)
		if not query:
			logger.warn('User %r has no permissions at all.', request.user)
			return queryset.none()
		return queryset.filter(query)


class RoleViewPermission(BasePermission):
	"""
	Used to read only Role objects the user has any permissions on.
	"""
	def has_object_permission(self, request, view, obj):
		# obj is a Role object
		res = UserImportJobCreationValidator.is_user_school_role_combination_allowed(
			username=request.user.username,
			school='*',
			role=obj.name
		)
		if not res:
			logger.warn(
				'Access forbidden for %r to role %r.',
				request.user.username,
				obj.name
			)
		return res


class SchoolViewPermission(BasePermission):
	"""
	Used to read only School objects the user has any permissions on.
	"""
	def has_object_permission(self, request, view, obj):
		# obj is a School object
		res = UserImportJobCreationValidator.is_user_school_role_combination_allowed(
			username=request.user.username,
			school=obj.name,
			role='*'
		)
		if not res:
			logger.warn(
				'Access forbidden for %r to school %r.',
				request.user.username,
				obj.name
			)
		return res


class TextArtifactViewPermission(BasePermission):
	"""
	Used to read only TextArtifact objects (LogFile, PasswordsFile,
	SummaryFile) the user has any permissions on.
	"""
	def has_object_permission(self, request, view, obj):
		# obj is a TextArtifact object (LogFile, PasswordsFile, SummaryFile)
		userimportjob_related_name = getattr(view, 'userimportjob_related_name')
		if not userimportjob_related_name:
			raise RuntimeError('View has no/empty userimportjob_related_name attribute.')

		if not getattr(obj, userimportjob_related_name):
			return False
		userimportjob = getattr(obj, userimportjob_related_name)
		res = UserImportJobCreationValidator.is_user_school_role_combination_allowed(
			username=request.user.username,
			school=userimportjob.school.name,
			role=userimportjob.user_role
		)
		if not res:
			logger.warn(
				'Access forbidden for %r to %r (school=%r role=%r).',
				request.user.username,
				obj,
				userimportjob.school.name,
				userimportjob.user_role
			)
		return res


class UserImportJobViewPermission(BasePermission):
	"""
	Used to read only UserImport objects the user has any permissions on.
	"""

	# not needed: restrict who can use the view
	#
	# def has_permission(self, request, view):
	# 	# view is a UserImportJobViewSet object
	# 	return True

	def has_object_permission(self, request, view, obj):
		# we use this to check GET of resource list and object
		# obj is a UserImportJob object
		res = UserImportJobCreationValidator.is_user_school_role_combination_allowed(
			username=request.user.username,
			school=obj.school.name,
			role=obj.user_role
		)
		if not res:
			logger.warn(
				'Access forbidden for %r to %r (school=%r role=%r).',
				request.user.username,
				obj,
				obj.school.name,
				obj.user_role
			)
		return res


class UserImportJobViewSet(
	mixins.CreateModelMixin,
	mixins.RetrieveModelMixin,
	mixins.ListModelMixin,
	viewsets.GenericViewSet):
	"""
Manage Import jobs.

* Only GET and POST are allowed.
* In a POST request `source_uid`, `dryrun`, `input_file` and `school` are mandatory.
* `source_uid` is of type string
* `dryrun` is of type boolean
* `input_file` has to be the key for a multipart-encoded file upload
* `school` must be an absolute URI from `/{version}/schools/`
* `user_role` must be one of `staff`, `student`, `teacher`, `teacher_and_staff`
	"""
	queryset = UserImportJob.objects.all()
	serializer_class = UserImportJobSerializer
	filter_backends = (
		UserImportJobFilterBackend,  # used to filter the queryset for allowed school-user_role-combinations
		DjangoFilterBackend,         # used to filter view by attribute
		OrderingFilter,              # used for ordering
	)
	filter_class = UserImportJobFilter  # filter principal by 'username' (DjangoFilterBackend works automatically only on pk)
	permission_classes = (
		IsAuthenticated,              # user must be authenticated to use this view
		UserImportJobViewPermission,  # apply per view and per-object permission checks
	)
	ordering_fields = ('id', 'school', 'source_uid', 'status', 'principal', 'dryrun', 'date_created')

	def perform_create(self, serializer):
		# store user when saving object
		serializer.save(principal=self.request.user)

	@staticmethod
	def _get_subresource_urls(instance_url):
		return {
			'log_file': urlparse.urljoin(instance_url, 'logfile/'),
			'password_file': urlparse.urljoin(instance_url, 'passwords/'),
			'summary_file': urlparse.urljoin(instance_url, 'summary/'),
		}

	def retrieve(self, request, *args, **kwargs):
		instance = self.get_object()
		serializer = self.get_serializer(instance)
		data = serializer.data
		# inject /imports/users/{pk}/(logfile|passwords|summary) URLs
		data.update(self._get_subresource_urls(data['url']))
		# remove 'input_file' from view
		del data['input_file']
		return Response(data)

	def list(self, request, *args, **kwargs):
		queryset = self.filter_queryset(self.get_queryset())

		# coming from GET SchoolViewSet.user_imports()?
		try:
			school = kwargs['school']
			queryset = queryset.filter(school=school)
		except KeyError:
			pass

		page = self.paginate_queryset(queryset)
		if page is not None:
			serializer = self.get_serializer(page, many=True)
			return self.get_paginated_response(serializer.data)

		serializer = self.get_serializer(queryset, many=True)
		data = serializer.data

		for d in data:
			# inject /imports/users/{pk}/(logfile|passwords|summary) URLs
			d.update(self._get_subresource_urls(d['url']))
			# remove 'input_file' from view
			del d['input_file']
		return Response(data)

	@detail_route(methods=['get'], url_path='logfile')
	def logfile(self, request, *args, **kwargs):
		instance = self.get_object()
		serializer = LogFileSerializer(instance.log_file, context={'request': request})
		# fix URL: /imports/users/{summary-pk}/logfile/ -> /imports/users/{import-pk}/logfile/
		data = serializer.data
		data['url'] = reverse('logfile-detail', kwargs=kwargs, request=request)
		return Response(data)

	@detail_route(methods=['get'], url_path='passwords')
	def passwords(self, request, *args, **kwargs):
		instance = self.get_object()
		serializer = PasswordFileSerializer(instance.password_file, context={'request': request})
		# fix URL: /imports/users/{summary-pk}/passwords/ -> /imports/users/{import-pk}/passwords/
		data = serializer.data
		data['url'] = reverse('passwordsfile-detail', kwargs=kwargs, request=request)
		return Response(data)

	@detail_route(methods=['get'], url_path='summary')
	def summary(self, request, *args, **kwargs):
		instance = self.get_object()
		serializer = SummarySerializer(instance.summary_file, context={'request': request})
		# fix URL: /imports/users/{summary-pk}/summary/ -> /imports/users/{import-pk}/summary/
		data = serializer.data
		data['url'] = reverse('summaryfile-detail', kwargs=kwargs, request=request)
		return Response(data)


class SubResourceMixin(object):
	#
	# It is not really necessary to check access permissions, because LogFileViewSet,
	# PasswordsViewSet and SummaryViewSet are used in detail_routes only. The query
	# filter of UserImportJobViewSet removes the forbidden UserImportJobs anyway. BUT
	# if the views were used somehow not from beneath UserImportJobViewSet, it would be
	# necessary. So better safe than sorry.
	#
	permission_classes = (
		IsAuthenticated,             # user must be authenticated to use this view
		TextArtifactViewPermission,  # apply per view and per-object permission checks
	)
	serializer_class = TextArtifact

	def _get_model(self):
		return self.get_serializer_class().Meta.model

	@property
	def userimportjob_related_name(self):
		return self.get_serializer_class().Meta.userimportjob_related_name

	def get_queryset(self):
		# must filter(), because all() would list all TextArtifact objects, not
		# just those of type LogFile/PasswordFile/SummaryFile
		return self._get_model().objects.filter(**{'{}__isnull'.format(self.userimportjob_related_name): False})

	def retrieve(self, request, *args, **kwargs):
		model = self._get_model()
		try:
			instance = self.get_queryset().get(**{'{}__pk'.format(self.userimportjob_related_name): kwargs.get('pk', 0)})
		except model.DoesNotExist:
			raise Http404('No {} matches the given query.'.format(model._meta.object_name))
		# running has_object_permission() here manually, because DRF doesn't seem to do it
		# probably because used from urls.py directly as_view()
		if not TextArtifactViewPermission().has_object_permission(request, self, instance):
			self.permission_denied(request)
		serializer = self.get_serializer(instance)
		# fix URL: /imports/users/{summary-pk}/summary -> /imports/users/{import-pk}/summary
		data = serializer.data
		data['url'] = reverse('{}-detail'.format(model.__name__.lower()), kwargs=kwargs, request=request)
		return Response(data)


class LogFileViewSet(SubResourceMixin, viewsets.ReadOnlyModelViewSet):
	"""
Log file of import job.

* Only GET is allowed.
	"""
	serializer_class = LogFileSerializer


class PasswordsViewSet(SubResourceMixin, viewsets.ReadOnlyModelViewSet):
	"""
New users password file of import job.

* Only GET is allowed.
	"""
	serializer_class = PasswordFileSerializer


class SummaryViewSet(SubResourceMixin, viewsets.ReadOnlyModelViewSet):
	"""
Summary file of import job.

* Only GET is allowed.
	"""
	serializer_class = SummarySerializer


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
	"""
Read-only list of Roles.
	"""
	queryset = Role.objects.all()
	serializer_class = RoleSerializer
	filter_backends = (RoleFilterBackend, DjangoFilterBackend, OrderingFilter)
	filter_fields = ('name', 'displayName')
	ordering_fields = ('name', 'displayName')
	permission_classes = (IsAuthenticated, RoleViewPermission)

	def retrieve(self, request, *args, **kwargs):
		Role.update_from_ldap()
		try:
			self._school = kwargs.pop('school')
		except KeyError:
			pass
		return super(RoleViewSet, self).retrieve(request, *args, **kwargs)

	def list(self, request, *args, **kwargs):
		Role.update_from_ldap()
		try:
			self._school = kwargs.pop('school')
		except KeyError:
			pass
		return super(RoleViewSet, self).list(request, *args, **kwargs)


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
	"""
Read-only list of Schools (OUs).

* `roles` provides navigation to a list of roles the connected user has permissions on the respective school.
* `user_imports` provides navigation to start an import for the respective school.
	"""
	queryset = School.objects.all()
	serializer_class = SchoolSerializer
	filter_backends = (SchoolFilterBackend, DjangoFilterBackend, OrderingFilter)
	filter_fields = ('name', 'displayName')
	ordering_fields = ('name', 'displayName')
	permission_classes = (IsAuthenticated, SchoolViewPermission)

	def retrieve(self, request, *args, **kwargs):
		instance = self.get_object()
		# update entry from LDAP
		instance.update_from_ldap(instance.pk)
		# inject /schools/{ou}/roles & /schools/{ou}/imports/users URLs
		instance_url = request.build_absolute_uri()
		instance.roles = urlparse.urljoin(instance_url, 'roles')
		instance.user_imports = urlparse.urljoin(instance_url, 'imports/users')
		serializer = self.get_serializer(instance)
		return Response(serializer.data)

	def list(self, request, *args, **kwargs):
		# update list from LDAP
		School.update_from_ldap()

		# add import URL
		queryset = self.filter_queryset(self.get_queryset())

		page = self.paginate_queryset(queryset)
		if page is not None:
			serializer = self.get_serializer(page, many=True)
			return self.get_paginated_response(serializer.data)

		serializer = self.get_serializer(queryset, many=True)
		data = serializer.data
		for d in data:
			d['roles'] = urlparse.urljoin(d['url'], 'roles')
			d['user_imports'] = urlparse.urljoin(d['url'], 'imports/users')
		return Response(data)

	@detail_route(methods=['get', 'post'], url_path='imports/users')
	def user_imports(self, request, *args, **kwargs):
		"""
		schools/{ou}/imports/users/
		"""
		instance = self.get_object()
		uivs = UserImportJobViewSet(request=request, **kwargs)
		uivs.initial(request=request, *args, **kwargs)
		if request.method == 'GET':
			kwargs['school'] = instance.name
			return uivs.list(request, *args, **kwargs)
		elif request.method == 'POST':
			school_serializer = self.get_serializer(instance=instance, context={'request': request})
			this_school_url = school_serializer.data['url']
			data = request.data.copy()
			if data.get('school') and data['school'] != this_school_url:
				abs_url = request.build_absolute_uri()
				logger.error(
					'User tried to import into %r, while POSTing to URL %r.',
					data['school'],
					abs_url
				)
				raise ParseError(
					'Import into school "{}" not allowed from "{}".'.format(
						data['school'],
						abs_url
					)
				)
			data['school'] = this_school_url
			uij_serializer = UserImportJobSerializer(data=data, context={'request': request})
			uij_serializer.is_valid(raise_exception=True)
			uivs.perform_create(uij_serializer)
			headers = uivs.get_success_headers(uij_serializer.data)
			return Response(uij_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

	@detail_route()
	def roles(self, request, *args, **kwargs):
		"""
		schools/{ou}/roles/

		Roles the connecting user has at this school.
		"""
		instance = self.get_object()
		rvs = RoleViewSet(request=request, **kwargs)
		rvs.initial(request=request, *args, **kwargs)
		kwargs['school'] = instance.name
		return rvs.list(request, *args, **kwargs)
