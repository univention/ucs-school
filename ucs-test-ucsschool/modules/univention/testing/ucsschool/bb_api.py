# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2019-2021 Univention GmbH
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
Test base code.
"""

from __future__ import unicode_literals

import datetime
import json
import logging
import os
import pprint
import random
import re
import shutil
import subprocess
import sys
import time
from unittest import TestCase

import requests
from six import reraise as raise_

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.importer.configuration import Configuration, setup_configuration as _setup_configuration
from ucsschool.importer.exceptions import UcsSchoolImportError
from ucsschool.importer.factory import setup_factory as _setup_factory
from ucsschool.importer.frontend.user_import_cmdline import (
    UserImportCommandLine as _UserImportCommandLine,
)
from ucsschool.importer.models.import_user import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
    ImportUser,
)
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.utils import exec_cmd, get_stream_handler, ucr
from univention.config_registry import handler_set
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase

try:
    from urlparse import urljoin  # py2
except ImportError:
    from urllib.parse import urljoin  # py3

try:
    from typing import Any, Dict, List, Optional, Text, Tuple
except ImportError:
    pass


IMPORT_CONFIG = {
    "active": "/var/lib/ucs-school-import/configs/user_import.json",
    "bak": "/var/lib/ucs-school-import/configs/user_import.json.bak.{}".format(
        datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    ),
    "default": "/usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json",
}

API_ROOT_URL = "https://{}.{}/api-bb/".format(ucr["hostname"], ucr["domainname"])
print("*** API_ROOT_URL={!r} ***".format(API_ROOT_URL))
RESSOURCE_URLS = {
    "roles": urljoin(API_ROOT_URL, "roles/"),
    "schools": urljoin(API_ROOT_URL, "schools/"),
    "users": urljoin(API_ROOT_URL, "users/"),
}
KELVIN_TOKEN_URL = API_ROOT_URL.replace("/v1/", "/token/")
_ucs_school_import_framework_initialized = False
_ucs_school_import_framework_error = None


def setup_logging():
    # set log level on loggers we're interested in
    for _name in (
        None,
        "requests",
        "univention",
        "ucsschool",
    ):
        logger = logging.getLogger(_name)
        logger.setLevel(logging.DEBUG)
    # capture output of root logger
    logger = logging.getLogger()
    handler = get_stream_handler(logging.DEBUG)
    logger.addHandler(handler)


setup_logging()


class InitialisationError(Exception):
    pass


class HttpApiUserTestBase(TestCase):
    mapped_udm_properties = ["organisation", "phone"]
    ucrvs2set = [
        "bb/http_api/users/wsgi_server_capture_output=true",
        "bb/http_api/users/django_debug=true",
        "bb/http_api/users/wsgi_server_loglevel=debug",
        "bb/http_api/users/wsgi_server_workers=8",
    ]
    should_restart_api_server = True
    logger = logging.getLogger("univention.testing.ucsschool")

    @classmethod
    def setUpClass(cls):
        cls.set_up_import_config()
        cls.import_config = init_ucs_school_import_framework()
        cls.logger.info("*** Initialized import framework.")
        cls.itb = ImportTestbase()
        cls.itb.ou_C = None
        # cls.itb.use_ou_cache = False
        cls.itb.setup_testenv(utu.UCSTestSchool())
        cls.itb.create_ous(cls.itb.schoolenv)
        cls.schoolenv = cls.itb.schoolenv
        cls.lo = cls.itb.lo
        cls.ucr = cls.itb.ucr
        cls.auth_headers = {"Authorization": "{} {}".format(*cls.get_token())}
        print("*** auth_headers={!r}".format(cls.auth_headers))
        handler_set(cls.ucrvs2set)
        if cls.should_restart_api_server:
            # for testing through HTTP (using WSGI directly not affected)
            cls.restart_api_server()
        exec_cmd(["/usr/share/pyshared/bb/http_api/users/manage.py", "updateschools"])

    @classmethod
    def tearDownClass(cls):
        cls.itb.cleanup()
        exec_cmd(["/usr/share/pyshared/bb/http_api/users/manage.py", "updateschools"])
        cls.revert_import_config()
        if cls.should_restart_api_server:
            cls.restart_api_server()

    @classmethod
    def get_token(cls):  # type: () -> Tuple[str, str]
        token = ucr.get("tests/ucsschool/http-api/bb/token")
        if token:
            print("*** Got a token from UCR. ***")
            return "Token", token.strip()
        token_from_django_cmd_local = [
            "/usr/share/pyshared/bb/http_api/users/manage.py",
            "shell",
            "-c",
            "from rest_framework.authtoken.models import Token; print(Token.objects.first().key)",
        ]
        if os.path.exists("/usr/share/pyshared/bb/http_api/users/manage.py"):
            returncode, stdout, stderr = exec_cmd(token_from_django_cmd_local, raise_exc=True)
            print("*** Got a token from local BB-API installation. ***")
            return "Token", stdout.strip()
        else:
            m = re.match(r"https://(.+?)/.+", API_ROOT_URL)
            if m:
                host = m.groups()[0]
                print("Tyring to get BB-API token via SSH...")
                token_from_django_cmd_ssh = token_from_django_cmd_local
                token_from_django_cmd_ssh[-1] = "'{}'".format(token_from_django_cmd_ssh[-1])
                returncode, stdout, stderr = exec_cmd(
                    ["ssh", host, " ".join(token_from_django_cmd_ssh)], raise_exc=True
                )
                print("*** Got a token from remote BB-API installation. ***")
                return "Token", stdout.strip()
        raise RuntimeError("No token available for BB-API.")

    @classmethod
    def set_up_import_config(cls):
        print("*** HttpApiUserTestBase.set_up_import_config()")
        # set_up_import_config()
        # return
        if os.path.exists(IMPORT_CONFIG["active"]):
            print("Moving {!r} to {!r}.".format(IMPORT_CONFIG["active"], IMPORT_CONFIG["bak"]))
            shutil.move(IMPORT_CONFIG["active"], IMPORT_CONFIG["bak"])
            config_file = IMPORT_CONFIG["bak"]
        else:
            config_file = IMPORT_CONFIG["default"]
        with open(config_file, "r") as fp:
            config = json.load(fp)
        config["configuration_checks"] = ["defaults", "mapped_udm_properties"]
        config["mapped_udm_properties"] = cls.mapped_udm_properties
        config["scheme"] = {
            "record_uid": "<firstname>.<lastname>",
            "username": {"default": "<:umlauts><firstname>.<lastname><:lower>[COUNTER2]"},
        }
        config["source_uid"] = "TESTID"
        config["verbose"] = True
        with open(IMPORT_CONFIG["active"], "w") as fp:
            json.dump(config, fp, indent=4)
        print("Wrote config to {!r}: {!r}".format(IMPORT_CONFIG["active"], config))

    @classmethod
    def revert_import_config(cls):
        if os.path.exists(IMPORT_CONFIG["bak"]):
            print("Moving {!r} to {!r}.".format(IMPORT_CONFIG["bak"], IMPORT_CONFIG["active"]))
            shutil.move(IMPORT_CONFIG["bak"], IMPORT_CONFIG["active"])
        else:
            print("Removing {!r}.".format(IMPORT_CONFIG["active"]))
            os.remove(IMPORT_CONFIG["active"])

    def compare_import_user_and_resource(self, import_user, resource, source="LDAP"):
        # type: (ImportUser, Dict[Text, Any], Optional[Text]) -> None
        self.logger.info("*** import_user (%s): %r", source, import_user.to_dict())
        self.logger.info("*** resource: %r", resource)
        dn = import_user.dn
        for k, v in resource.items():
            if k == "url":
                continue
            elif k == "dn":
                self.assertEqual(dn, v, "Expected DN {!r} got {!r}.".format(dn, v))
            elif k == "school":
                response = requests.get(v, headers=self.auth_headers)
                self.assertEqual(
                    response.status_code,
                    200,
                    "response.status_code = {} for URL {!r} -> {!r}".format(
                        response.status_code, response.url, response.text
                    ),
                )
                obj = response.json()
                self.assertEqual(
                    obj.get("name"),
                    import_user.school,
                    "Value of attribute {!r} in {} is {!r} and in resource is {!r} -> {!r} "
                    "({!r}).".format(k, source, import_user.school, v, obj.get("name"), dn),
                )
            elif k == "schools":
                objs = []
                for url in v:
                    response = requests.get(url, headers=self.auth_headers)
                    self.assertEqual(
                        response.status_code,
                        200,
                        "response.status_code = {} for URL {!r} -> {!r}".format(
                            response.status_code, response.url, response.text
                        ),
                    )
                    objs.append(response.json())
                school_names = set(obj.get("name") for obj in objs)
                self.assertEqual(
                    school_names,
                    set(import_user.schools),
                    "Value of attribute {!r} in {} is {!r} and in resource is {!r} -> {!r} "
                    "({!r}).".format(k, source, import_user.schools, v, school_names, dn),
                )
            elif k == "disabled":
                self.assertIn(v, (True, False), "Value of {!r} is {!r}.".format(k, v))
                val = "1" if v is True else "0"
                self.assertEqual(
                    val,
                    import_user.disabled,
                    "Value of attribute {!r} in {} is {!r} and in resource is {!r} -> {!r} "
                    "({!r}).".format(k, source, import_user.disabled, v, val, dn),
                )
            elif k == "roles":
                objs = []
                for url in v:
                    response = requests.get(url, headers=self.auth_headers)
                    self.assertEqual(
                        response.status_code,
                        200,
                        "response.status_code = {} for URL {!r} -> {!r}".format(
                            response.status_code, response.url, response.text
                        ),
                    )
                    objs.append(response.json())
                role_names = set(
                    "pupil" if obj.get("name") == "student" else obj.get("name") for obj in objs
                )
                self.assertEqual(
                    role_names,
                    set(import_user.roles),
                    "Value of attribute {!r} in {} is {!r} and in resource is {!r} -> {!r} "
                    "({!r}).".format(k, source, import_user.roles, v, role_names, dn),
                )
            elif k == "school_classes":
                if source == "LDAP":
                    val = dict(
                        (school, ["{}-{}".format(school, kls) for kls in classes])
                        for school, classes in v.items()
                    )
                else:
                    val = v
                msg = (
                    "Value of attribute {!r} in {} is {!r} and in resource is "
                    "v={!r} -> val={!r} ({!r}).".format(k, source, getattr(import_user, k), v, val, dn)
                )
                self.assertDictEqual(getattr(import_user, k), val, msg)
            elif k == "udm_properties":
                # Could be the same test as for 'school_classes', but lists are not necessarily in order
                # (for example phone, e-mail, etc), so converting them to sets:
                self.assertSetEqual(set(import_user.udm_properties.keys()), set(v.keys()))
                for udm_k, udm_v in import_user.udm_properties.items():
                    msg = (
                        "Value of attribute {!r} in {} is {!r} and in resource is {!r} "
                        "({!r}).".format(k, source, getattr(import_user, k), v, dn)
                    )
                    if isinstance(udm_v, list):
                        self.assertSetEqual(set(udm_v), set(v[udm_k]), msg)
                    else:
                        self.assertEqual(udm_v, v[udm_k], msg)
            elif getattr(import_user, k) is None and v == "":
                continue
            else:
                self.assertEqual(
                    getattr(import_user, k),
                    v,
                    "Value of attribute {!r} in {} is {!r} and in resource is {!r} ({!r}).".format(
                        k, source, getattr(import_user, k), v, dn
                    ),
                )

    def make_user_attrs(self, ous, partial=False, **kwargs):
        # type: (List[Text], Optional[bool], **Any) -> Dict[Text, Any]
        roles = kwargs.pop("roles", None) or random.choice(
            (("staff",), ("staff", "teacher"), ("student",), ("teacher",))
        )
        res = {
            "name": "test{}".format(uts.random_username()),
            "birthday": "19{}-0{}-{}{}".format(
                2 * uts.random_int(), uts.random_int(1, 9), uts.random_int(0, 2), uts.random_int(1, 8)
            ),
            "disabled": random.choice((True, False)),
            "email": "{}@{}".format(uts.random_username(), self.itb.maildomain),
            "firstname": uts.random_username(),
            "lastname": uts.random_username(),
            "password": uts.random_username(16),
            "record_uid": uts.random_username(),
            "roles": [urljoin(RESSOURCE_URLS["roles"], role + "/") for role in roles],
            "school": urljoin(RESSOURCE_URLS["schools"], ous[0] + "/"),
            "school_classes": {}
            if roles == ("staff",)
            else dict((ou, sorted([uts.random_username(4), uts.random_username(4)])) for ou in ous),
            "schools": [urljoin(RESSOURCE_URLS["schools"], ou + "/") for ou in ous],
            "source_uid": self.import_config["source_uid"],
            "udm_properties": {
                "phone": [uts.random_username(), uts.random_username()],
                "organisation": uts.random_username(),
            },
        }
        if partial:
            # remove all but n attributes
            num_attrs = random.randint(1, 5)
            removable_attrs = [
                "birthday",
                "disabled",
                "email",
                "firstname",
                "lastname",
                "password",
                "record_uid",
                "school",
                "school_classes",
                "schools",
                "source_uid",
            ]
            random.shuffle(removable_attrs)
            for k in res.keys():
                if k not in removable_attrs[:num_attrs]:
                    del res[k]
        res.update(kwargs)
        return res

    @classmethod
    def restart_api_server(cls):
        cls.logger.info("*** Restarting ucs-school-http-api-bb...")
        subprocess.call(["service", "ucs-school-http-api-bb", "restart"])
        time.sleep(10)

    @staticmethod
    def get_class_dn(class_name, school, lo):
        # copied from models.user as static version
        school_class = SchoolClass.cache(class_name, school)
        if school_class.get_relative_name() == school_class.name:
            if not school_class.exists(lo):
                class_name = "%s-%s" % (school, class_name)
                school_class = SchoolClass.cache(class_name, school)
        return school_class.dn

    def extract_class_dns(self, attrs):
        school_class_objs = []
        for school, school_classes in attrs.get("school_classes", {}).items():
            school_class_objs.extend(SchoolClass.cache(sc, school) for sc in school_classes)
        return [self.get_class_dn(sc.name, sc.school, self.lo) for sc in school_class_objs]

    def get_import_user(self, dn, school=None):  # type: (str, Optional[str]) -> ImportUser
        user = ImportUser.from_dn(dn, school, self.lo)
        udm_obj = user.get_udm_object(self.lo)
        user.udm_properties = dict((k, udm_obj[k]) for k in self.import_config["mapped_udm_properties"])
        return user

    def create_import_user(self, **kwargs):  # type: (**Any) -> ImportUser
        kls = random.choice((ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff))
        obj = kls(**kwargs)
        res = obj.create(self.lo)
        if not res:
            self.fail("Creating {!r} failed with kwargs {!r}".format(kls, kwargs))
        return obj


def api_call(method, url, auth=None, headers=None, json_data=None):
    # type: (Text, Text, Optional[Any], Optional[Dict[Text, Any]], Optional[Dict[Text, Any]]) -> Dict[Text, Any]  # noqa: E501
    HttpApiUserTestBase.logger.debug(
        "*** [%r] method=%r url=%r json_data=%r", os.getpid(), method, url, json_data
    )
    meth = getattr(requests, method)
    response = meth(url, auth=auth, headers=headers, json=json_data)
    HttpApiUserTestBase.logger.debug(
        "*** [%r] status_code=%r reason=%r", os.getpid(), response.status_code, response.reason
    )
    if hasattr(response, "json"):
        res = response.json() if callable(response.json) else response.json
    else:
        res = response.reason
    HttpApiUserTestBase.logger.debug("*** [%r] res=%r", os.getpid(), res)
    return res


def create_remote_static(attribs):
    # type: (Tuple[Dict[Text, Text], Dict[Text, Any]]) -> Dict[Text, Any]
    auth_headers, attrs = attribs
    return api_call("post", RESSOURCE_URLS["users"], json_data=attrs, headers=auth_headers)


def partial_update_remote_static(old_username_and_new_attrs):
    # type: (Tuple[Dict[Text, Text], Text, Dict[Text, Any]]) -> Dict[Text, Any]
    auth_headers, old_username, new_attrs = old_username_and_new_attrs
    url = urljoin(RESSOURCE_URLS["users"], old_username + "/")
    return api_call("patch", url, json_data=new_attrs, headers=auth_headers)


def init_ucs_school_import_framework(**config_kwargs):
    global _ucs_school_import_framework_initialized, _ucs_school_import_framework_error

    if _ucs_school_import_framework_initialized:
        return Configuration()
    if _ucs_school_import_framework_error:
        # prevent "Changing the configuration is not allowed." error if we
        # return here after raising an InitialisationError
        etype, exc, etraceback = sys.exc_info()
        raise_(_ucs_school_import_framework_error, exc, etraceback)

    _config_args = {
        "dry_run": False,
        "logfile": "/var/log/univention/ucs-school-http-api-bb/ucs-school-import.log",
        "skip_tests": ["uniqueness"],
    }
    _config_args.update(config_kwargs)
    _ui = _UserImportCommandLine()
    _config_files = _ui.configuration_files
    logger = logging.getLogger("univention.testing.ucsschool")
    try:
        config = _setup_configuration(_config_files, **_config_args)
        if "mapped_udm_properties" not in config.get("configuration_checks", []):
            raise UcsSchoolImportError(
                'Missing "mapped_udm_properties" in configuration checks, e.g.: '
                '{.., "configuration_checks": ["defaults", "mapped_udm_properties"], ..}'
            )
        _ui.setup_logging(config["verbose"], config["logfile"])
        _setup_factory(config["factory"])
    except UcsSchoolImportError as exc:
        logger.exception("Error initializing UCS@school import framework: %s", exc)
        etype, exc, etraceback = sys.exc_info()
        _ucs_school_import_framework_error = InitialisationError(str(exc))
        raise_(etype, exc, etraceback)
    logger.info("------ UCS@school import tool configured ------")
    logger.info("Used configuration files: %s.", config.conffiles)
    logger.info("Using command line arguments: %r", _config_args)
    logger.info("Configuration is:\n%s", pprint.pformat(config))
    _ucs_school_import_framework_initialized = True
    return config
