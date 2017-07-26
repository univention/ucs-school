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
import os.path
try:
	from urlparse import urljoin
except ImportError:
	# Python 3
	from urllib.parse import urljoin
import logging

import requests
import magic
from univention.config_registry import ConfigRegistry


ucr = ConfigRegistry()
ucr.load()
MIME_TYPE = magic.open(magic.MAGIC_MIME_TYPE)
MIME_TYPE.load()


class ApiError(Exception):
	pass


class Client(object):
	LOG_REQUEST = 5
	LOG_RESPONSE = 4
	SCHOOLS_URL = 'schools/'
	IMPORT_USERS_URL = 'imports/users/'

	def __init__(self, name, password, server=None, version=1, log_level=logging.INFO, *args, **kwargs):
		"""

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
		self.session = None
		self.cookies = None
		self._lo = None
		self.base_url = 'https://{}/api/v{}/'.format(self.server, self.version)
		self.logger = self._setup_logging(log_level)

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

	def _call_api(self, method, url_end, data=None, files=None, params=None, **kwargs):
		if not url_end.endswith('/'):
			url_end += '/'
		url = urljoin(self.base_url, url_end)
		request_kwargs = dict(
			url=url,
			data=data,
			files=files,
			params=params,
			verify=False,
			auth=(self.username, self.password),
			**kwargs)
		self.logger.request('%s(%s)', method, ', '.join('{}={!r}'.format(k, v) for k, v in request_kwargs.items()))
		meth = getattr(requests, method)
		response = meth(**request_kwargs)
		self.logger.response(response.content)
		if not response.ok:
			raise ApiError('Received status_code={!r} with reason={!r} for requests.{}(**{}).'.format(response.status_code, getattr(response, 'reason'), method, ', '.join('{}={!r}'.format(k, v) for k, v in request_kwargs.items())))
		return response.json()

	@staticmethod
	def _get_mime_type(data):
		return MIME_TYPE.buffer(data)

	def create_importjob(self, filename, source_uid, school, dryrun=True, file_obj=None):
		"""
		Create an ImportJob.

		:param filename: str: path to a CSV file
		:param source_uid: str: unique sourceUID of school management software database
		:param school: URL: to one of those returned by get_schools()
		:param dryrun: bool: False to start a real import
		:param file_obj: optional file like object to read CSV data from, instead of opening 'filename'
		:return: dict: the created ImportJob resource
		"""
		assert (isinstance(filename, basestring) or filename is None)
		assert isinstance(source_uid, basestring)
		assert isinstance(school, basestring)
		assert isinstance(dryrun, bool)
		assert (isinstance(file_obj, file) or file_obj is None)

		data = {
			"source_uid": source_uid,
			"dryrun": dryrun,
			"school": school
		}
		filename = filename or 'noname'
		if not file_obj:
			file_obj = open(filename, 'rb')
		file_data = file_obj.read()
		mime_type = self._get_mime_type(file_data[:32])
		files = {'input_file': (os.path.basename(filename), file_data, mime_type)}
		return self._call_api('post', self.IMPORT_USERS_URL, data=data, files=files)

	def get_importjobs(self, importjob_id=None):
		"""
		Read ImportJob(s).

		:param importjob_id: int or None
		:return: list of dicts or dict if importjob_id is given
		"""
		url = self.IMPORT_USERS_URL
		if importjob_id:
			url += '{}/'.format(importjob_id)
		return self._call_api('get', url)

	def get_schools(self, ou_name=None):
		"""
		Read School(s).

		:param ou_name: str: OU
		:return: list of dicts or dict if ou_name is given
		"""
		url = self.SCHOOLS_URL
		if ou_name:
			url += '{}/'.format(ou_name)
		return self._call_api('get', url)
