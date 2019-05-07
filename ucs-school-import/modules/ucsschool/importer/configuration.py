# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2016-2019 Univention GmbH
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
Configuration classes.
"""

import json
import logging
from six import string_types
from ucsschool.lib.models.utils import ucr, ucr_username_max_length
from .exceptions import InitialisationError, ReadOnlyConfiguration
from .utils.configuration_checks import run_configuration_checks
from .utils.import_pyhook import run_import_pyhooks
from .utils.config_pyhook import ConfigPyHook
try:
	from typing import Any, Dict, List, Optional, Type
except ImportError:
	pass


def setup_configuration(conffiles, **kwargs):  # type: (List[str], **str) -> ReadOnlyDict
	logger = logging.getLogger(__name__)
	config = Configuration(conffiles)
	config.update(kwargs)
	_set_username_maxlength(config, logger)
	run_import_pyhooks(ConfigPyHook, 'post_config_files_read', config, conffiles, kwargs)
	config.check_mandatory_attributes(logger)
	config.close()
	logger.info("Finished reading configuration, starting checks...")
	run_configuration_checks(config)
	return config


def _set_username_maxlength(config, logger):  # type: (ReadOnlyDict, logging.Logger) -> None
	ucrv = ucr.get('ucsschool/username/max_length')
	logger.info('UCRV ucsschool/username/max_length: %r', ucrv)
	try:
		default = config['username']['max_length']['default']
	except KeyError:
		default = int(ucr_username_max_length)  # convert lazy proxy object to int
		config['username'].setdefault('max_length', {})['default'] = default
		logger.info(
			'Set value of configuration key username:max_length:default to%s value of UCR variable '
			'ucsschool/username/max_length: %d.', ' default' if ucrv is None else '', default)
	try:
		student = config['username']['max_length']['student']
	except KeyError:
		exam_prefix = ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-")
		student = default - len(exam_prefix)
		config['username']['max_length']['student'] = student
		logger.info(
			'Set value of configuration key username:max_length:student to username:max_length:default reduced by '
			'length of the exam-prefix (%r): %d.', exam_prefix, student)


class ConfigurationFile(object):

	def __init__(self, filename):  # type: (str) -> None
		self.filename = filename
		self.logger = logging.getLogger(__name__)

	def read(self):  # type: () -> Dict[str, Any]
		self.logger.info("Reading configuration from %r...", self.filename)
		with open(self.filename, "rb") as fp:
			return json.load(fp)

	def write(self, conf):  # type: (str) -> None
		self.logger.info("Writing configuration to %r...", self.filename)
		with open(self.filename, "wb") as fp:
			return json.dump(conf, fp)

	def update(self, conf):  # type: (**str) -> None
		self.logger.info("Updating configuration in %r...", self.filename)
		cur = self.read()
		cur.update(conf)
		with open(self.filename, "wb") as fp:
			return json.dump(cur, fp)


class ReadOnlyDict(dict):

	@classmethod
	def _recursive_typed_update(cls, a, b):  # type: (Dict[Any, Any], Dict[Any, Any]) -> Dict[Any, Any]
		for k, v in b.items():
			if isinstance(v, dict):
				# recurse into nested dict
				a[k] = cls._recursive_typed_update(a.get(k, {}), v)
			else:
				# Try to use any other type than str (when overwriting
				# configuration from cmdline).
				if v is None or callable(v):
					a[k] = v
				else:
					t = type(v)
					if isinstance(t, string_types) and a.get(k):
						t = type(a[k])
					a[k] = t(v)
		return a

	def update(self, E=None, **F):  # type: (Optional[Dict[Any, Any]], **Any) -> None
		self._recursive_typed_update(self, E)
		if F:
			self._recursive_typed_update(self, F)

	@staticmethod
	def __closed(*args, **kwargs):  # type: (*Any, **Any) -> None
		raise ReadOnlyConfiguration()

	def check_mandatory_attributes(self, logger):  # type: (logging.Logger) -> None
		try:
			mandatory_attributes = self["mandatory_attributes"]
			assert isinstance(mandatory_attributes, list)
		except (AssertionError, KeyError):
			# will be checked in /usr/share/ucs-school-import/checks/defaults::test_minimal_mandatory_attributes()
			pass
		else:
			missing_mandatory_attributes = [
				attr for attr in ("firstname", "lastname", "name", "record_uid", "school", "source_uid")
				if attr not in mandatory_attributes
			]
			if missing_mandatory_attributes:
				logger.info("Adding %r to 'mandatory_attributes'.", missing_mandatory_attributes)
				mandatory_attributes.extend(missing_mandatory_attributes)
			mandatory_attributes.sort()

	def close(self):  # type: () -> None
		self.__setitem__ = self.__delitem__ = self.update = self._recursive_typed_update = self.__closed  # noqa


class Configuration(object):
	"""
	Singleton to the global configuration object.
	"""
	class __SingleConf:
		conffiles = list()

		def __init__(self, filenames):  # type: (List[str]) -> None
			if not filenames:
				raise InitialisationError("Configuration not yet loaded.")
			self.config = None
			for filename in filenames:
				try:
					cf = ConfigurationFile(filename)
					if self.config:
						self.config.update(cf.read())
					else:
						self.config = ReadOnlyDict(cf.read())
					self.conffiles.append(filename)
				except ValueError as ve:
					raise InitialisationError("Error in configuration file '{}': {}.".format(filename, ve))
				except IOError as exc:
					raise InitialisationError("Error reading configuration file {}.".format(exc))
			self.config.conffiles = self.conffiles

	_instance = None

	def __new__(cls, filenames=None):  # type: (Type[Configuration], Optional[List[str]]) -> ReadOnlyDict
		if not cls._instance:
			cls._instance = cls.__SingleConf(filenames)
		return cls._instance.config
