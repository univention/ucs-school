# -*- coding: utf-8 -*-
#
# Univention Management Console
#  Univention Directory Manager Module
#
# Copyright 2019 Univention GmbH
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

>>> username = 'Administrator'
>>> password = 'univention'
>>> uri = 'http://10.200.27.100/univention/udm/'
>>> module = 'mail/domain'
>>> udm = UDM.http(uri, username, password).version(1)
>>> module = udm.get(module)
>>> print('Found {}'.format(module))
>>> print('Now performing {}'.format(action))
>>> for entry in module.search():
>>> 	print(entry)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import copy
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Union
import requests
from requests.compat import urljoin, quote_plus
from ldap.dn import explode_dn

if sys.version_info.major > 2:
	import http.client
	http.client._MAXHEADERS = 1000
else:
	import httplib
	httplib._MAXHEADERS = 1000


logger = logging.getLogger(__name__)


class HTTPError(Exception):

	def __init__(self, code, message, response):
		self.code = code
		self.response = response
		super(HTTPError, self).__init__(message)


class NotFound(HTTPError):
	pass


class Session(object):

	def __init__(self, credentials, language='en-US'):
		self.language = language
		self.credentials = credentials
		self.session = self.create_session()
		self.default_headers = {
			'Accept': 'application/json; q=1; text/html; q=0.2, */*; q=0.1',
			'Accept-Language': self.language,
		}

	def create_session(self):
		sess = requests.session()
		sess.auth = (self.credentials.username, self.credentials.password)
		try:
			from cachecontrol import CacheControl
		except ImportError:
			#print('Cannot cache!')
			pass
		else:
			sess = CacheControl(sess)
		return sess

	def get_method(self, method):
		sess = self.session
		return {
			'GET': sess.get,
			'POST': sess.post,
			'PUT': sess.put,
			'DELETE': sess.delete,
			'PATCH': sess.patch,
			'OPTIONS': sess.options,
		}.get(method.upper(), sess.get)

	def make_request(self, method, uri, data=None, **headers):
		# logger.debug("%s %r (data=%r, headers=%r)", method, uri, data, headers)
		# stack_trace = traceback.format_list(traceback.extract_stack()[-7:-1])
		# pyroot = str(Path(__file__).parent.parent.parent)
		# stack_trace = '\n'.join(line.replace(pyroot, "PYTHON") for line in stack_trace)
		# logger.debug("Call stack:\n%s", stack_trace)
		if method in ('GET', 'HEAD'):
			params = data
			json = None
		else:
			params = None
			json = data
		return self.get_method(method)(uri, params=params, json=json, headers=dict(self.default_headers, **headers))

	def eval_response(self, response):  # type: (requests.Response) -> Dict[str, Any]
		if response.status_code >= 299:
			msg = '{} {}: {}'.format(response.request.method, response.url, response.status_code)
			try:
				json = response.json()
			except ValueError:
				pass
			else:
				if isinstance(json, dict):
					if 'error' in json:
						server_message = json['error'].get('message')
						# traceback = json['error'].get('traceback')
						if server_message:
							msg += '\n{}'.format(server_message)
			cls = HTTPError
			if response.status_code == 404:
				cls = NotFound
			raise cls(response.status_code, msg, response)
		return response.json()


class Client(object):

	def __init__(self, client):  # type: (Session) -> None
		self.client = client


class UDM(Client):

	@classmethod
	def http(cls, uri, username, password):  # type: (str, str, str) -> UDM
		return cls(uri, username, password)

	def __init__(self, uri, username, password, *args, **kwargs):
		# type: (str, str, str, *Any, **Any) -> None
		self.uri = uri
		self.username = username
		self.password = password
		self._api_version = None
		self._modules_cache = {}  # type: Dict[str, Module]
		super(UDM, self).__init__(Session(self), *args, **kwargs)

	@classmethod
	def using_lo(cls, lo):  # type: (...) -> UDM
		url = "http://{}/univention/udm/".format(lo.host)
		username = explode_dn(lo.binddn, True)[0]
		return UDM.http(url, username, lo.bindpw)

	def modules(self):  # type: () -> Iterator[Module]
		# TODO: cache - needs server side support
		resp = self.client.make_request('GET', self.uri)
		prefix_modules = self.client.eval_response(resp)['_links']['udm:object-modules']
		for prefix_module in prefix_modules:
			resp = self.client.make_request('GET', prefix_module['href'])
			module_infos = self.client.eval_response(resp).get('_links', {}).get('udm:object-types', [])
			for module_info in module_infos:
				yield Module(self, module_info['href'], module_info['name'], module_info['title'])

	def version(self, api_version):  # type: (str) -> UDM
		self._api_version = api_version
		return self

	def obj_by_dn(self, dn):  # type: (str) -> Object
		# TODO: Needed?
		raise NotImplementedError()

	def get(self, name):  # type: (str) -> Module
		if name not in self._modules_cache:
			# Add only requested module to cache -> run self.modules() each
			# time a new module is requested.
			# If lots of modules are in use, it may be faster to do this once
			# for all modules. But that seems an unlikely scenario.
			for module in self.modules():
				if module.name == name:
					self._modules_cache[name] = module
					break
		return self._modules_cache[name]

	def __repr__(self):
		return 'UDM(uri={}, username={}, password=****, version={})'.format(self.uri, self.username, self._api_version)


class Module(Client):
	def __init__(self, udm, uri, name, title, *args, **kwargs):
		# type: (UDM, str, str, str, *Any, **Any) -> None
		super(Module, self).__init__(udm.client, *args, **kwargs)
		self.uri = uri
		self.username = udm.username
		self.password = udm.password
		self.name = name
		self.title = title
		self._relations = {}
		self._template_cache = {}

	@property
	def relations(self):  # type: () -> Dict[str, Any]
		if not self._relations:
			resp = self.client.make_request('GET', self.uri)
			self._relations = self.client.eval_response(resp).get('_links', {})
		return self._relations

	def __repr__(self):
		return 'Module(uri={}, name={})'.format(self.uri, self.name)

	def new(self, superordinate=None):  # type: (Optional[str]) -> Object
		return Object(self, None, {}, [], {}, None, superordinate, None)

	def get(self, dn, attr=None, required=False, exceptions=False):
		# type: (str, Optional[Iterable[str]], Optional[bool], Optional[bool]) -> Object
		# logger.debug("*** dn=%r", dn)
		uri = urljoin(self.uri, quote_plus(dn))  # not HATEOAS but _much_ faster than searching
		resp = self.client.make_request('GET', uri)
		entry = self.client.eval_response(resp)
		return Object(self, entry['dn'], entry['properties'], entry['options'], entry['policies'], entry['position'], entry.get('superordinate'), entry['uri'])

	def get_by_entry_uuid(self, uuid):  # type: (str) -> Object
		for obj in self.search(filter={'entryUUID': uuid}, scope='base'):
			return obj.open()

	def get_by_id(self, dn):  # type: (str) -> Object
		# TODO: Needed?
		raise NotImplementedError()

	def search(self, filter=None, position=None, scope='sub', hidden=False, superordinate=None, opened=False):
		# type: (...) -> Union[Object, ShallowObject]
		# logger.debug(
		# 	"*** filter=%r position=%r scope=%r hidden=%r superordinate=%r opened=%r",
		# 	filter, position, scope, hidden, superordinate, opened
		# )
		data = {}
		if filter:
			for prop, val in filter.items():
				data['property'] = prop
				data['propertyvalue'] = val
		if superordinate:
			data['superordinate'] = superordinate
		data['position'] = position
		data['scope'] = scope
		data['hidden'] = '1' if hidden else ''
		if opened:
			data['properties'] = '*'
		resp = self.client.make_request('GET', self.relations['search'][0]['href'], data=data)
		entries = self.client.eval_response(resp)['entries']
		for entry in entries:
			# logger.debug("** entry=%r", entry)
			if opened:
				yield Object(self, entry['dn'], entry['properties'], entry['options'], entry['policies'], entry['position'], entry.get('superordinate'), entry['uri'])  # NOTE: this is missing last-modified, therefore no conditional request is done on modification!
			else:
				yield ShallowObject(self, entry['dn'], entry['uri'])

	def create(self, properties, options, policies, position, superordinate=None):
		# type: (Dict[str, Any], Dict[str, str], List[str], univention.admin.uldap.position, Optional[str]) -> Object
		# logger.debug("***** properties=%r options=%r policies=%r position=%r superordinate=%r", properties, options, policies, position, superordinate)
		obj = self.create_template(position=position, superordinate=superordinate, options=options)
		obj.options = options
		obj.properties = properties
		obj.policies = policies
		obj.position = position
		obj.superordinate = superordinate
		obj.create()
		return obj

	def create_template(self, position=None, superordinate=None, options=None):
		# type: (Optional[univention.admin.uldap.position], Optional[str], Optional[Dict[str, str]]) -> Object
		# trasmitting `position` and `options`, but both doen't get added to the response :/
		# I informed the core board via chat.
		data = {'position': str(position), 'superordinate': superordinate, 'options': options}
		# logger.debug("***** data=%r", data)
		key = copy.deepcopy(data)
		key['options'] = tuple(sorted(options.items()))
		key = tuple(key.items())
		if key not in self._template_cache:
			resp = self.client.make_request('GET', self.relations['create-form'][0]['href'], data=data)
			self._template_cache[key] = self.client.eval_response(resp)['entry']
		entry = self._template_cache[key]
		# logger.debug("***** entry=%r", entry)
		return Object(
			module=self,
			dn=None,
			properties=entry['properties'],
			options=entry['options'] or options,  # workaround
			policies=entry['policies'],
			position=entry['position'] or data['position'],  # workaround
			superordinate=entry.get('superordinate'),
			uri=self.uri
		)

	@property
	def property_descriptions(self):  # type: () -> Dict[str, Any]
		return self.create_template().properties

	def object(self, co, lo, position, dn='', superordinate=None, attributes=None, options=None):
		# logger.debug("***** dn=%r position=%r superordinate=%r options=%r", dn, position, superordinate,options)
		return self.create_template(position=position, superordinate=superordinate, options=options)


class ShallowObject(Client):

	def __init__(self, module, dn, uri, *args, **kwargs):
		super(ShallowObject, self).__init__(module.client, *args, **kwargs)
		self.module = module
		self.dn = dn
		self.uri = uri

	def open(self):  # type: () -> Object
		# logger.debug("**** %s.open()", self)
		resp = self.client.make_request('GET', self.uri)
		entry = self.client.eval_response(resp)
		return Object(self.module, entry['dn'], entry['properties'], entry['options'], entry['policies'], entry['position'], entry.get('superordinate'), entry['uri'], etag=resp.headers.get('Etag'), last_modified=resp.headers.get('Last-Modified'))

	def __repr__(self):
		return 'ShallowObject(module={}, dn={})'.format(self.module.name, self.dn)


class Object(Client):

	@property
	def props(self):  # type: () -> Dict[str, Any]
		return self.properties

	@props.setter
	def props(self, props):  # type: (Dict[str, Any]) -> None
		self.properties = props

	def __init__(self, module, dn, properties, options, policies, position, superordinate, uri, etag=None, last_modified=None, *args, **kwargs):
		# type: (Module, Optional[str], Dict[str, Any], Dict[str, bool], Dict[str, Any], str, str, str, Optional[Any], Optional[Any], *Any, **Any) -> None
		super(Object, self).__init__(module.client, *args, **kwargs)
		self.dn = dn
		self.properties = properties
		self.options = options
		self.policies = policies
		self.position = position
		self.superordinate = superordinate
		self.module = module
		self.uri = uri
		self.etag = etag
		self.last_modified = last_modified

	def __repr__(self):
		return 'Object(module={}, dn={}, uri={})'.format(self.module.name, self.dn, self.uri)

	def reload(self):  # type: () -> None
		obj = self.module.get(self.dn)
		self._copy_from_obj(obj)

	def save(self):  # type: () -> None
		# DN is always set in ucsschool objects.
		raise RuntimeError("Don't use this, use create() oder modify() directly.")

	def create(self, *args, **kwargs):
		return self._create()

	def modify(self, *args, **kwargs):
		return self._modify()

	@property
	def info(self):  # type: () -> Dict[str, Any]
		return self.properties

	def delete(self, remove_referring=False):
		return self.client.make_request('DELETE', self.uri)

	def remove(self, *args, **kwargs):
		return self.delete()

	def _modify(self):
		data = {
			'properties': self.props,
			'options': self.options,
			'policies': self.policies,
			'position': self.position,
			'superordinate': self.superordinate,
		}
		headers = dict((key, value) for key, value in {
			# 'If-Unmodified-Since': self.last_modified,  # FIXME: only if one second passed
			'If-Match': self.etag,
		}.items() if value)
		# logger.debug("******* data=%r", data)
		resp = self.client.make_request('PUT', self.uri, data=data, **headers)
		entry = self.client.eval_response(resp)
		if resp.status_code == 201:  # move()
			resp = self.client.make_request('GET', resp.headers['Location'])
			entry = self.client.eval_response(resp)
		self.dn = entry['dn']
		self.reload()

	def _copy_from_obj(self, obj):
		self.dn = obj.dn
		self.props = obj.props
		self.options = obj.options
		self.policies = obj.policies
		self.position = obj.position
		self.superordinate = obj.superordinate
		self.module = obj.module
		self.uri = obj.uri
		self.etag = obj.etag
		self.last_modified = obj.last_modified

	def _create(self):
		data = {
			'properties': self.props,
			'options': self.options,
			'policies': self.policies,
			'position': self.position,
			'superordinate': self.superordinate,
		}
		# logger.debug("******* data=%r", data)
		resp = self.client.make_request('POST', self.module.uri, data=data)
		if resp.status_code in (200, 201):
			uri = resp.headers['Location']
			obj = ShallowObject(self.module, None, uri).open()
			self._copy_from_obj(obj)
		else:
			self.client.eval_response(resp)

	def __getitem__(self, item):
		return self.properties[item]

	def __setitem__(self, key, value):
		self.properties[key] = value

	def __contains__(self, item):
		return item in self.properties
