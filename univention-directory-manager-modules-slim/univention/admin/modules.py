# -*- coding: utf-8 -*-

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

import os
import logging
from collections import namedtuple
from typing import Dict, List
import ruamel.yaml
from univention.config_registry import ConfigRegistry
from univention.admin.client import UDM
from univention.admin.filter import parse as filter_parse, flatten_filter
from .client import Object, Module


MACHINE_PASSWORD_FILE = "/etc/machine.secret"
MachinePWCache = namedtuple("MachinePWCache", ["mtime", "password"])
logger = logging.getLogger(__name__)
ucr = ConfigRegistry()
ucr.load()
_udm_http = None


class ConnectionData(object):
	"""
	Connection details as it would be in a app Docker container.
	"""
	_machine_pw = MachinePWCache(0, "")

	@classmethod
	def _env_or_ucr(cls, key):  # type: (str) -> str
		try:
			return os.environ[key.replace("/", "_")]
		except KeyError:
			return ucr[key]

	@classmethod
	def ldap_base(cls):  # type: () -> str
		return cls._env_or_ucr("ldap/base")

	@classmethod
	def ldap_hostdn(cls):  # type: () -> str
		return cls._env_or_ucr("ldap/hostdn")

	@classmethod
	def ldap_server_name(cls):  # type: () -> str
		return cls._env_or_ucr("ldap/server/name")

	@classmethod
	def machine_password(cls):  # type: () -> str
		"""
		For developers: will try os.environ["ldap_machine_password"]
		before reading from /etc/machine.secret.
		"""
		try:
			return os.environ["ldap_machine_password"]
		except KeyError:
			pass

		mtime = os.stat(MACHINE_PASSWORD_FILE).st_mtime
		if cls._machine_pw.mtime == mtime:
			return cls._machine_pw.password
		else:
			with open(MACHINE_PASSWORD_FILE, "r") as fp:
				pw = fp.read()
				pw = pw.strip()
			cls._machine_pw = MachinePWCache(mtime, pw)
			return pw

	@classmethod
	def uri(cls):  # type: () -> str
		# TODO: should be HTTPS
		return "http://{}/univention/udm/".format(cls.ldap_server_name())


def get(name):  # type: (str) -> Module
	"""return UDM module"""
	global _udm_http
	if not _udm_http:
		_udm_http = UDM.http(
			uri=ConnectionData.uri(),
			username=ConnectionData.ldap_hostdn(),
			password=ConnectionData.machine_password()
		).version(0)
	return _udm_http.get(name)


def lookup(module_name, co, lo_udm, filter='', base='', superordinate=None, scope='sub'):
	# type: (...) -> List[Object]
	mod = lo_udm.get(module_name)  # type: Module
	filter_s_parsed = filter_parse(filter)
	if hasattr(filter_s_parsed, "expressions"):
		args = dict((e.variable, e.value) for e in flatten_filter(filter_s_parsed))
	else:
		args = dict(((filter_s_parsed.variable, filter_s_parsed.value),)) if filter_s_parsed.variable else {}
	res = mod.search(filter=args, position=base, scope=scope, superordinate=superordinate, opened=True)
	return list(res)


def init():
	# TODO
	pass
