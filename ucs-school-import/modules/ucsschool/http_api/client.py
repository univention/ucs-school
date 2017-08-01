# -*- coding: utf-8 -*-
"""
HTTP API Client
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
import copy
import os.path
try:
	from urlparse import urljoin
except ImportError:
	# Python 3
	from urllib.parse import urljoin
import logging
import inspect

import requests
import magic
from univention.config_registry import ConfigRegistry


ucr = ConfigRegistry()
ucr.load()
MIME_TYPE = magic.open(magic.MAGIC_MIME_TYPE)
MIME_TYPE.load()
__resource_class_registry = list()


def register_resource_class(cls):
	if cls not in __resource_class_registry:
		__resource_class_registry.append(cls)


def get_resource_classes():
	return __resource_class_registry


class ApiError(Exception):
	def __init__(self, msg, status_code=None):
		super(ApiError, self).__init__(msg)
		self.status_code = status_code


class BadRequest(ApiError):
	"""
	HTTP 400
	"""
	pass

class LoginError(ApiError):
	"""
	HTTP 403
	"""
	pass


class ObjectNotFound(ApiError):
	"""
	HTTP 404
	"""
	pass


class ServerError(ApiError):
	"""
	HTTP 5xx
	"""
	pass

class ConnectionError(ApiError):
	"""
	Cannot establish / lost connection to server.
	"""
	pass


class _ResourceMetaClass(type):
	def __new__(cls, clsname, bases, attrs):
		kls = super(_ResourceMetaClass, cls).__new__(cls, clsname, bases, attrs)
		register_resource_class(kls)
		return kls


class Client(object):
	LOG_REQUEST = 5
	LOG_RESPONSE = 4

	def __init__(self, name, password, server=None, version=1, log_level=logging.INFO, ssl_verify=True, *args, **kwargs):
		"""
		UCS@School HTTP API client.

		:param name:
		:param password:
		:param server:
		:param version:
		:param log_level: int: logging.{INFO,DEBUG,..} or Client.LOG_REQUEST>Client.LOG_RESPONSE to log API requests & responses
		"""
		self.username = name
		self.password = password
		self.server = server or '{}.{}'.format(ucr['hostname'], ucr['domainname'])
		self.version = version
		self.ssl_verify = ssl_verify
		self.base_url = 'https://{}/api/v{}/'.format(self.server, self.version)
		self.logger = self._setup_logging(log_level)
		self.logger.debug('Registering resources and methods:')
		for kls in get_resource_classes():
			setattr(self, kls.__name__.lower(), kls(self))
			self.logger.debug(
				'  %s: %s',
				kls.__name__,
				', '.join([m[0] for m in inspect.getmembers(kls, predicate=inspect.ismethod) if m[0] != '__init__'])
			)

	@classmethod
	def _setup_logging(cls, log_level):
		if not hasattr(logging, 'LOG_REQUEST'):
			logging.addLevelName(cls.LOG_REQUEST, 'REQUEST')
		if not hasattr(logging, 'LOG_RESPONSE'):
			logging.addLevelName(cls.LOG_RESPONSE, 'RESPONSE')

		logger = logging.getLogger('import_http_api_client')
		logger.request = lambda msg, *args, **kwargs: logger.log(cls.LOG_REQUEST, msg, *args, **kwargs)
		logger.response = lambda msg, *args, **kwargs: logger.log(cls.LOG_RESPONSE, msg, *args, **kwargs)

		if not logger.handlers:
			handler = logging.StreamHandler()
			handler.setFormatter(logging.Formatter(
				fmt='%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d  %(message)s',
				datefmt='%Y-%m-%d %H:%M:%S'
			))
			handler.setLevel(log_level)
			logger.addHandler(handler)
		if log_level > logger.level:
			logger.setLevel(log_level)
		return logger

	def call_api(self, method, url_end, data=None, files=None, params=None, **kwargs):
		if not url_end.endswith('/'):
			url_end += '/'
		url = urljoin(self.base_url, url_end)
		request_kwargs = dict(
			url=url,
			data=data,
			files=files,
			params=params,
			auth=(self.username, self.password),
			**kwargs)
		if not self.ssl_verify:
			request_kwargs['verify'] = False
		log_request_kwargs = copy.deepcopy(request_kwargs)
		log_request_kwargs['auth'] = (log_request_kwargs['auth'][0], '*' * len(log_request_kwargs['auth'][1]))
		self.logger.request('%s(%s)', method, ', '.join('{}={!r}'.format(k, v) for k, v in log_request_kwargs.items()))
		meth = getattr(requests, method)
		try:
			response = meth(**request_kwargs)
		except requests.ConnectionError as exc:
			raise ConnectionError(str(exc))
		self.logger.response('%s -> %s (%r): %r', response.url, response.reason, response.status_code, response.content)
		if not response.ok:
			msg = 'Received status_code={!r} with reason={!r} for requests.{}(**{}).'.format(response.status_code, response.reason, method, ', '.join('{}={!r}'.format(k, v) for k, v in log_request_kwargs.items()))
			if response.status_code == 400:
				exc = BadRequest
			elif response.status_code == 403:
				exc = LoginError
			elif response.status_code == 404:
				exc = ObjectNotFound
			elif 499 < response.status_code < 600:
				exc = ServerError
			else:
				exc = ApiError
			raise exc(msg, status_code=response.status_code)
		return response.json()

	class _Resource(object):
		RESOURCE_URL = ''

		def __init__(self, client):
			self.client = client

		def get(self, pk):
			"""
			Read Resource.

			:param pk: str: primary key (name, id, ..)
			:return: dict
			"""
			url = urljoin(self.RESOURCE_URL, str(pk))
			return self.client.call_api('get', url)

		def list(self):
			"""
			List all Resource this user has access to.

			:return: list of dicts
			"""
			return self.client.call_api('get', self.RESOURCE_URL)


	class School(_Resource):
		__metaclass__ = _ResourceMetaClass
		RESOURCE_URL = 'schools/'


	class UserImportJob(_Resource):
		__metaclass__ = _ResourceMetaClass
		RESOURCE_URL = 'imports/users/'

		def create(self, filename, source_uid, school, user_role=None, dryrun=True, file_obj=None):
			"""
			Create a UserImportJob.

			:param filename: str: path to a CSV file, or just a filename and read from 'file_obj'
			:param source_uid: str: unique sourceUID of school management software database
			:param school: str: name of a School
			:param user_role: str: optional role of user, one of staff, student, teacher, teacher_and_staff
			:param dryrun: bool: False to start a real import
			:param file_obj: optional file like object to read CSV data from, instead of opening 'filename'
			:return: dict: the created UserImportJob resource
			"""
			assert isinstance(filename, basestring)
			assert isinstance(source_uid, basestring)
			assert isinstance(school, basestring)
			assert (isinstance(user_role, basestring) or user_role is None)
			assert isinstance(dryrun, bool)
			assert (isinstance(file_obj, file) or file_obj is None)

			try:
				school_resource = self.client.School.get(school)
			except ObjectNotFound:
				raise ObjectNotFound('School {!r} is unknown.'.format(school))

			data = {
				'source_uid': source_uid,
				'dryrun': dryrun,
				'school': school_resource['url'],
				'user_role': user_role,
			}
			filename = filename or 'noname'
			if not file_obj:
				file_obj = open(filename, 'rb')
			file_data = file_obj.read(32)
			mime_type = self._get_mime_type(file_data)
			file_obj.seek(os.SEEK_SET)
			files = {'input_file': (os.path.basename(filename), file_obj, mime_type)}
			return self.client.call_api('post', self.RESOURCE_URL, data=data, files=files)

		@staticmethod
		def _get_mime_type(data):
			return MIME_TYPE.buffer(data)
