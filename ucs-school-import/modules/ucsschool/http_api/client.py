#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2024 Univention GmbH
#
# https://www.univention.de/
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

"""HTTP API Client"""

from __future__ import absolute_import, unicode_literals

import copy
import inspect
import logging
import os.path
from io import IOBase
from typing import Any, Callable, Dict, List  # noqa: F401

import dateutil.parser
import magic
import requests
from six import string_types, with_metaclass
from six.moves.urllib_parse import parse_qs, quote as url_quote, urljoin, urlparse

from ucsschool.lib.models.utils import get_stream_handler
from univention.config_registry import ConfigRegistry

ucr = ConfigRegistry()
ucr.load()
MIME_TYPE = magic.open(magic.MAGIC_MIME_TYPE)
MIME_TYPE.load()
__resource_client_class_registry = []  # type: List[Client._ResourceClient]
__resource_representation_class_registry = (
    {}
)  # type: Dict[str, ResourceRepresentation._ResourceReprBase]


def register_resource_client_class(cls):
    if cls not in __resource_client_class_registry:
        __resource_client_class_registry.append(cls)


def get_resource_client_classes():
    return __resource_client_class_registry


def register_resource_representation_class(resource_name, cls):
    __resource_representation_class_registry[resource_name] = cls


def get_resource_representation_classes(resource_name):
    return __resource_representation_class_registry[resource_name]


class ApiError(Exception):
    def __init__(self, msg, status_code=None):
        super(ApiError, self).__init__(msg)
        self.status_code = status_code


class BadRequest(ApiError):
    """HTTP 400"""

    pass


class PermissionError(ApiError):
    """HTTP 401|403"""

    pass


class ObjectNotFound(ApiError):
    """HTTP 404"""

    pass


class ServerError(ApiError):
    """HTTP 5xx"""

    pass


class ConnectionError(ApiError):
    """Cannot establish / lost connection to server."""

    pass


class IllegalURLError(ApiError):
    """URLs returned from API root do not meet expectation."""

    pass


class _ResourceClientMetaClass(type):
    """Meta class for resource client classes. Registers them."""

    def __new__(cls, clsname, bases, attrs):
        kls = super(_ResourceClientMetaClass, cls).__new__(cls, clsname, bases, attrs)
        register_resource_client_class(kls)
        return kls


class _ResourceRepresentationMetaClass(type):
    """Meta class for resource representation classes. Registers them."""

    def __new__(cls, clsname, bases, attrs):
        kls = super(_ResourceRepresentationMetaClass, cls).__new__(cls, clsname, bases, attrs)
        register_resource_representation_class(kls.resource_name, kls)
        return kls


class ResourceRepresentationIterator(object):
    """Iterator for paginated query results."""

    def __init__(self, resource_client, paginated_resource_list):
        self._resource_client = resource_client
        self._paginated_resource_list = paginated_resource_list
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            resource = self._paginated_resource_list["results"][self.index]
        except IndexError:
            if self._paginated_resource_list["next"] is None:
                raise StopIteration()
            parse_result = urlparse(self._paginated_resource_list["next"])
            url = parse_result._replace(query=None).geturl()
            params = parse_qs(parse_result.query)
            self._paginated_resource_list = self._resource_client._resource_from_url(url, **params)
            self.index = 0
            resource = self._paginated_resource_list["results"][self.index]
        self.index += 1
        return ResourceRepresentation.get_repr(self._resource_client, resource)

    next = __next__  # py2


class ResourceRepresentation(object):
    """
    Python representations of HTTP-API resources.

    To add resources to the Python API create inner classes that
    1. subclass  _ResourceReprBase
    2. use as meta class _ResourceRepresentationMetaClass
    3. set a class attribute `resource_name` that matches the resource path
    in the HTTP-API

    The meta class will register the resource representation class and make it
    available through Client objects.

    client = Client(<username>, <password>, [log level])
    client.school.list()           # <-- from SchoolResource
    client.userimportjob.create()  # <-- from UserImportJobResource
    """

    class _ResourceReprBase(object):
        """Base class of resource representation classes."""

        resource_name = ""
        _attribute_repr = {}  # type: Dict[str, Callable[[str], Any]]

        def __init__(self, resource_client, resource):
            self._resource_client = resource_client
            self._resource = resource
            self._cache = {}
            self._set_attrs(self._resource)

        def __repr__(self):
            return "{}({})".format(self.__class__.__name__, getattr(self, self._resource_client.pk_name))

        def _set_attrs(self, resource):
            for k, v in resource.items():
                if k == "url":
                    continue
                if k not in dir(self):
                    try:
                        val = self._attribute_repr[k](v)
                    except KeyError:
                        val = v
                    setattr(self, k, val)

        def update(self):
            self._cache = {}
            self._resource = self._resource_client._resource_from_url(self._resource["url"])
            self._set_attrs(self._resource)

    class SchoolResource(with_metaclass(_ResourceRepresentationMetaClass, _ResourceReprBase)):
        resource_name = "schools"

        @property
        def roles(self):
            """
            Roles the connected user has in this school.

            :return: RoleResource objects
            :rtype: ResourceRepresentationIterator
            """
            url = urljoin(self._resource["url"], "roles")
            return self._resource_client.client.roles.list(resource_url=url)

        @property
        def user_imports(self):
            """
            UserImportJobs that ran for this school.

            :return: UserImportJobResource objects
            :rtype: ResourceRepresentationIterator
            """
            return self._resource_client.client.userimportjob.list(school=self.name)

    class RoleResource(with_metaclass(_ResourceRepresentationMetaClass, _ResourceReprBase)):
        resource_name = "roles"

    class ResultResource(with_metaclass(_ResourceRepresentationMetaClass, _ResourceReprBase)):
        resource_name = "result"
        _attribute_repr = {"date_done": lambda x: dateutil.parser.parse(x)}

        def __repr__(self):
            return "{}(status={!r})".format(self.__class__.__name__, self.status)

    class UserImportJobResource(with_metaclass(_ResourceRepresentationMetaClass, _ResourceReprBase)):
        """
        Representation of an import job resource.

        `job = client.userimportjob.get(job_id)`

        * job.status
        * job.result
        * job.log_file
        * job.password_file
        * job.school
        * job.summary_file
        """

        resource_name = "imports/users"
        _attribute_repr = {"date_created": lambda x: dateutil.parser.parse(x)}

        def __repr__(self):
            return "{}({}, {}, {}, {}, {})".format(
                self.__class__.__name__,
                getattr(self, self._resource_client.pk_name),
                self._cached_school,  # side effect: this will create a request (the first time) to get
                # the schools name
                self.user_role,
                self.principal,
                self.status,
            )

        @property
        def log_file(self):
            try:
                return self._resource_client._resource_from_url(self._resource["log_file"]).get("text")
            except ObjectNotFound:
                return None

        @property
        def password_file(self):
            try:
                return self._resource_client._resource_from_url(self._resource["password_file"]).get(
                    "text"
                )
            except ObjectNotFound:
                return None

        @property
        def school(self):
            school_r = ResourceRepresentation.SchoolResource(
                self._resource_client, self._resource_client._resource_from_url(self._resource["school"])
            )
            self._cache["school_name"] = school_r.name
            return school_r

        @property
        def summary_file(self):
            try:
                return self._resource_client._resource_from_url(self._resource["summary_file"]).get(
                    "text"
                )
            except ObjectNotFound:
                return None

        @property
        def result(self):
            if self._resource["result"]:
                return ResourceRepresentation.ResultResource(
                    self._resource_client, self._resource["result"]
                )
            else:
                return None

        @property
        def _cached_school(self):
            if "school_name" not in self._cache:
                try:
                    self._cache["school_name"] = self.school.name
                except ApiError as exc:
                    print("Error retrieving school name of UserImportJobResource: {}".format(exc))
                    return "school name n/a"
            return self._cache["school_name"]

    @classmethod
    def get_repr(cls, resource_client, resource):
        return get_resource_representation_classes(resource_client.resource_name)(
            resource_client, resource
        )


class Client(object):
    """
    HTTP-API import client.

    client = Client(username, password)
    my_schools = client.school.list()
    my_roles_at_school1 = client.school.get('school1').roles
    job_id = client.userimportjob.create()
    client.userimportjob.get(job_id)
    """

    LOG_REQUEST = 5
    LOG_RESPONSE = 4

    def __init__(
        self,
        name,
        password,
        server=None,
        version=1,
        log_level=logging.INFO,
        ssl_verify=True,
        *args,
        **kwargs
    ):
        """
        UCS@school HTTP API client.

        :param str name: username for connecting to HTTP-API
        :param str password: password to use for connecting to HTTP-API
        :param str server: FQDN of server running the HTTP-API
        :param str version: HTTP-API version, omit to use latest version
        :param int log_level: log level, use `logging.{INFO,DEBUG,..}` or
            `Client.LOG_REQUEST` to log API requests, `Client.LOG_RESPONSE` to
            log both requests and responses
        """
        self.username = name
        self.password = password
        self.server = server or "{}.{}".format(ucr["hostname"], ucr["domainname"])
        self.version = version
        self.ssl_verify = ssl_verify
        self.base_url = "https://{}/api/v{}/".format(self.server, self.version)
        self.logger = self._setup_logging(log_level)
        self._resource_urls = None
        self.logger.debug("Registering resources and methods:")
        for kls in get_resource_client_classes():
            cls_name = kls.__name__.lower().strip("_")
            setattr(self, cls_name, kls(self))
            self.logger.debug(
                "  %s: %s",
                cls_name,
                ", ".join(
                    [
                        m[0]
                        for m in inspect.getmembers(kls, predicate=inspect.ismethod)
                        if not m[0].startswith("_")
                    ]
                ),
            )

    @property
    def resource_urls(self):
        if not self._resource_urls:
            self._resource_urls = self.call_api("get", ".")
            for resource, url in self._resource_urls.items():
                if not url.lower().startswith(self.base_url.lower()):
                    raise IllegalURLError(
                        "URL {!r} for resource {!r} from API root does not start with {!r}.".format(
                            url, resource, self.base_url
                        )
                    )
        return self._resource_urls

    @classmethod
    def _setup_logging(cls, log_level):
        if not hasattr(logging, "LOG_REQUEST"):
            logging.addLevelName(cls.LOG_REQUEST, "REQUEST")
        if not hasattr(logging, "LOG_RESPONSE"):
            logging.addLevelName(cls.LOG_RESPONSE, "RESPONSE")

        logger = logging.getLogger(__name__)
        logger.request = lambda msg, *args, **kwargs: logger.log(cls.LOG_REQUEST, msg, *args, **kwargs)
        logger.response = lambda msg, *args, **kwargs: logger.log(cls.LOG_RESPONSE, msg, *args, **kwargs)

        if not logger.handlers:
            logger.addHandler(get_stream_handler(log_level))
        if log_level > logger.level:
            logger.setLevel(log_level)
        return logger

    def call_api(self, method, url_end, data=None, files=None, params=None, **kwargs):
        """
        Call HTTP-API.

        :param str method: `get`, `post` etc
        :param str url_end: URL path after base URL (https://<server>/api/<version>/<url_end>)
        :param dict data: payload
        :param dict files: {'<key>': (<filename>, <open file>, <mime type>)}
        :param dict params: URL parameters
        :param dict kwargs: additional arguments to pass to request
        :return: server response
        :rtype: dict
        :raises: ApiError
        """
        if not url_end.endswith("/"):
            url_end += "/"
        url = urljoin(self.base_url, url_end)
        request_kwargs = dict(
            url=url,
            data=data,
            files=files,
            params=params,
            auth=(self.username, self.password),
            headers={"Accept": "application/json"},
            **kwargs
        )
        # TODO: add language to request for translated displayNames. something like:
        # request_kwargs['headers']['Accept-Language'] ='de_DE'
        if not self.ssl_verify:
            request_kwargs["verify"] = False
        log_request_kwargs = copy.deepcopy(
            dict(request_kwargs, files={k: v[0] for k, v in (request_kwargs["files"] or {}).items()})
        )
        log_request_kwargs["auth"] = (
            log_request_kwargs["auth"][0],
            "*" * len(log_request_kwargs["auth"][1]),
        )
        self.logger.request(
            "%s(%s)", method, ", ".join("{}={!r}".format(k, v) for k, v in log_request_kwargs.items())
        )
        meth = getattr(requests, method)
        try:
            response = meth(**request_kwargs)
        except requests.ConnectionError as exc:
            raise ConnectionError(str(exc))
        self.logger.response(
            "%s -> %s (%r) headers:%r content:%r",
            response.url,
            response.reason,
            response.status_code,
            response.headers,
            response.content,
        )
        if not response.ok:
            msg = "Received status_code={!r} with reason={!r} for requests.{}(**{}).".format(
                response.status_code,
                response.reason,
                method,
                ", ".join("{}={!r}".format(k, v) for k, v in log_request_kwargs.items()),
            )
            if response.status_code == 400:
                exc = BadRequest
            elif response.status_code in (401, 403):
                exc = PermissionError
            elif response.status_code == 404:
                exc = ObjectNotFound
            elif 499 < response.status_code < 600:
                exc = ServerError
            else:
                exc = ApiError
            raise exc(msg, status_code=response.status_code)
        return response.json()

    class _ResourceClient(object):
        resource_name = ""
        pk_name = ""

        def __init__(self, client):
            self.client = client
            self.resource_url = self.client.resource_urls[self.resource_name]

        def _to_python(self, resource):
            if resource is None:
                return None
            elif all(key in resource for key in ("count", "next", "previous", "results")):
                return ResourceRepresentationIterator(self, resource)
            return ResourceRepresentation.get_repr(self, resource)

        def _resource_from_url(self, url, **params):
            return self.client.call_api("get", url, params=params)

        def _get_resource(self, pk, **params):
            url = urljoin(self.resource_url, url_quote(str(pk)))
            return self._resource_from_url(url, **params)

        def _list_resource(self, **params):
            resource_url = params.pop("resource_url", self.resource_url)
            return self._resource_from_url(resource_url, **params)

        def get(self, pk):
            """
            Read Resource.

            :param str pk: primary key (name, id, ..)
            :return: Resource object
            :rtype: _ResourceReprBase
            """
            assert isinstance(pk, string_types) or isinstance(pk, int)

            return self._to_python(self._get_resource(pk))

        def latest(self, **params):
            """
            Get newest Resource this user has access to.

            All arguments will be passed as parameters to the request. Example:
            latest(dryrun=True)

            :param params: arguments to pass as parameters to the request
            :return: Resource object
            :rtype: ResourceRepresentation
            """
            list_kwargs = {"ordering": "-{}".format(self.pk_name), "limit": "1"}
            list_kwargs.update(params)
            for ioj in self.list(**list_kwargs):
                return ioj
            raise ObjectNotFound("No {!r} resources exist.".format(self.resource_name))

        def list(self, **params):
            """
            List all Resource this user has access to.

            All arguments will be passed as parameters to the request. Example:
            list(status=['Aborted', 'Finished'], dryrun=False, ordering='id', limit=1)

            :param params: arguments to pass as parameters to the request
            :return: list of Resource objects
            :rtype: ResourceRepresentationIterator
            """
            return self._to_python(self._list_resource(**params))

    class _School(with_metaclass(_ResourceClientMetaClass, _ResourceClient)):
        resource_name = "schools"
        pk_name = "name"

    class _Roles(with_metaclass(_ResourceClientMetaClass, _ResourceClient)):
        resource_name = "roles"
        pk_name = "name"

    class _UserImportJob(with_metaclass(_ResourceClientMetaClass, _ResourceClient)):
        resource_name = "imports/users"
        pk_name = "id"

        def create(
            self, filename, source_uid=None, school=None, user_role=None, dryrun=True, file_obj=None
        ):
            """
            Create a UserImportJob.

            :param str filename: path to a CSV file, or just a filename and read from 'file_obj'
            :param str source_uid: optional unique ID of school management software database
            :param str school: optional name of a School
            :param str user_role: optional role of user, one of staff, student, teacher,
                teacher_and_staff
            :param bool dryrun: False to start a real import
            :param file file_obj: optional file like object to read CSV data from, instead of opening
                'filename'
            :return: the created UserImportJob resource
            :rtype: _ResourceReprBase
            """
            assert isinstance(filename, string_types)
            assert isinstance(source_uid, string_types) or source_uid is None
            assert isinstance(school, string_types) or school is None
            assert isinstance(user_role, string_types) or user_role is None
            assert isinstance(dryrun, bool)
            assert isinstance(file_obj, IOBase) or file_obj is None

            data = {
                "dryrun": dryrun,
            }
            if school:
                try:
                    school_obj = self.client.school.get(school)
                except ObjectNotFound:
                    raise ObjectNotFound("School {!r} is unknown.".format(school))
                data["school"] = school_obj._resource["url"]
            if source_uid:
                data["source_uid"] = source_uid
            if user_role:
                data["user_role"] = user_role
            filename = filename or "noname"
            if not file_obj:
                file_obj = open(filename, "rb")
            file_data = file_obj.read(32)
            mime_type = self._get_mime_type(file_data)
            file_obj.seek(os.SEEK_SET)
            files = {"input_file": (os.path.basename(filename), file_obj, mime_type)}
            return self._to_python(
                self.client.call_api("post", self.resource_url, data=data, files=files)
            )

        @staticmethod
        def _get_mime_type(data):
            return MIME_TYPE.buffer(data)
