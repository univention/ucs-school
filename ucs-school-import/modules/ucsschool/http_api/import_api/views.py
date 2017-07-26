# -*- coding: utf-8 -*-
"""
Django Views
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
import codecs
import urlparse
from rest_framework import mixins, viewsets
from rest_framework.response import Response
# from rest_framework.decorators import detail_route
from .models import UserImportJob, Logfile, School, JOB_STARTED
from .serializers import (
	UserImportJobSerializer,
	LogFileSerializer,
	SchoolSerializer,
)
from .logging import logger
from .ldap import get_ous


# TODO: use django-guardian to filter object access?


class UserImportJobViewSet(
	mixins.CreateModelMixin,
	mixins.RetrieveModelMixin,
	mixins.ListModelMixin,
	viewsets.GenericViewSet):
	"""
Manage Import jobs.

* Only GET and POST are allowed.
* The `source_uid` must match `config_file.source_uid`.
* The `school` must match `config_file.school`.
* `result`, `log_file`, `hooks` and `principal` will be set automatically
(data in POST will be ignored).
* In a POST request `source_uid`, `school` and `config_file` are mandatory.
	"""
	queryset = UserImportJob.objects.order_by('-pk')
	serializer_class = UserImportJobSerializer

	def perform_create(self, serializer):
		# store user
		serializer.save(principal=self.request.user.username)

# class UserImportJobGetViewSet(
# 	mixins.RetrieveModelMixin,
# 	mixins.ListModelMixin,
# 	UserImportJobViewSet):
# 	"""
# Manage Import jobs.
#
# * Only GET and POST are allowed.
# * The `source_uid` must match `config_file.source_uid`.
# * The `school` must match `config_file.school`.
# * `result`, `log_file`, `hooks` and `principal` will be set automatically
# (data in POST will be ignored).
# * In a POST request `source_uid`, `school` and `config_file` are mandatory.
# 	"""
	def retrieve(self, request, *args, **kwargs):
		# update progress if job is active
		instance = self.get_object()
		if instance.status == JOB_STARTED:
			instance.update_progress()
		return super(UserImportJobViewSet, self).retrieve(request, *args, **kwargs)

	def list(self, request, *args, **kwargs):
		# update progress of running jobs
		queryset = self.filter_queryset(self.get_queryset())
		for ij in queryset.filter(status=JOB_STARTED):
			ij.update_progress()
		return super(UserImportJobViewSet, self).list(request, *args, **kwargs)

	def redirect_get_from_schools(self, request, *args, **kwargs):
		logger.debug('args=%r kwargs=%r', args, kwargs)
		return

class LogFileViewSet(viewsets.ReadOnlyModelViewSet):
	"""
Readonly representation of import job logfiles in the Web API.
	"""
	queryset = Logfile.objects.all()
	serializer_class = LogFileSerializer

	# def get_queryset(self):
	# 	user = self.request.user
	# 	return LogFileViewSet.objects.filter(importjob__principal=user)

	def retrieve(self, request, *args, **kwargs):
		# read logfile from disk
		instance = self.get_object()
		if not instance.text:
			with codecs.open(instance.path, 'rb', encoding='utf-8') as fp:
				instance.text = fp.read()
		serializer = self.get_serializer(instance)
		return Response(serializer.data)


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = School.objects.order_by('name')
	serializer_class = SchoolSerializer

	@staticmethod
	def _update_sqldb_from_ldap(ou_str=None):
		for dn, ou in get_ous(ou_str):
			name = ou['ou'][0]
			display_name = ou['displayName'][0]
			obj, created = School.objects.get_or_create(
				name=name,
				defaults={'displayName': display_name},
			)
			if not created and obj.displayName != display_name:
				obj.displayName = display_name
				obj.save()

	def retrieve(self, request, *args, **kwargs):
		# update entry from LDAP
		self._update_sqldb_from_ldap(kwargs.get('pk'))
		instance = self.get_object()
		# inject /schools/{ou}/imports/users URL
		instance_url = request.build_absolute_uri()
		instance.user_import = urlparse.urljoin(instance_url, 'imports/users')
		serializer = self.get_serializer(instance)
		logger.info('serializer.data=%r', serializer.data)
		return Response(serializer.data)

	def list(self, request, *args, **kwargs):
		# update list from LDAP
		self._update_sqldb_from_ldap()
		return super(SchoolViewSet, self).list(request, *args, **kwargs)

	# @detail_route(methods=['post'], url_path='imports/users')
	# def create_user_import(self, request, pk=None):
	# 	logger.info('SchoolViewSet.create_user_import() pk=%r', pk)
	# 	pass

class ImportTypeViewSet(viewsets.ReadOnlyModelViewSet):
	# TODO
	pass
