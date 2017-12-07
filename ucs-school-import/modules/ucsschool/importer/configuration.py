# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Configuration classes.
"""
# Copyright 2016-2017 Univention GmbH
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


import json

from ucsschool.lib.models.utils import ucr
from ucsschool.importer.exceptions import InitialisationError, ReadOnlyConfiguration
from ucsschool.importer.utils.logging import get_logger


def setup_configuration(conffiles, **kwargs):
	config = Configuration(conffiles)
	config.update(kwargs)
	config.close()
	check_configuration(config)
	return config


def check_configuration(config):
	if not config.get("sourceUID"):
		raise InitialisationError("No sourceUID was specified.")
	if not config["input"].get("type"):
		raise InitialisationError("No input:type was specified.")
	if "user_deletion" in config:
		raise InitialisationError("The 'user_deletion' configuration key is deprecated. Please set 'deletion_grace_period'.")
	for role in ('default', 'staff',  'student', 'teacher', 'teacher_and_staff'):
		try:
			username_max_length = config["username"]["max_length"][role]
		except KeyError:
			continue
		if username_max_length < 4:
			raise InitialisationError(
				"Configuration value of username:max_length:{} must be higher than 3.".format(role)
			)
	exam_user_prefix_length = len(ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-"))
	student_username_max_length = config["username"]["max_length"].get("student", 20 - exam_user_prefix_length)
	if student_username_max_length > 20 - exam_user_prefix_length:
		raise InitialisationError(
			"Configuration value of username:max_length:student must be {} or less.".format(20 - exam_user_prefix_length)
		)
	for role in ('default', 'staff', 'teacher', 'teacher_and_staff'):
		username_max_length = config["username"]["max_length"].get(role, 20)
		if username_max_length > 20:
			raise InitialisationError(
				"Configuration value of username:max_length:{} must be 20 or less.".format(role)
			)


class ConfigurationFile(object):

	def __init__(self, filename):
		self.filename = filename
		self.logger = get_logger()

	def read(self):
		self.logger.info("Reading configuration from %r...", self.filename)
		with open(self.filename, "rb") as fp:
			return json.load(fp)

	def write(self, conf):
		self.logger.info("Writing configuration to %r...", self.filename)
		with open(self.filename, "wb") as fp:
			return json.dump(conf, fp)

	def update(self, conf):
		self.logger.info("Updating configuration in %r...", self.filename)
		cur = self.read()
		cur.update(conf)
		with open(self.filename, "wb") as fp:
			return json.dump(cur, fp)


class ReadOnlyDict(dict):

	@classmethod
	def _recursive_typed_update(cls, a, b):
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
					if isinstance(t, basestring) and a.get(k):
						t = type(a[k])
					a[k] = t(v)
		return a

	def update(self, E=None, **F):
		self._recursive_typed_update(self, E)
		if F:
			self._recursive_typed_update(self, F)

	@staticmethod
	def __closed(self, *args, **kwargs):
		raise ReadOnlyConfiguration()

	def close(self):
		self.__setitem__ = self.__delitem__ = self.update = self._recursive_typed_update = self.__closed


class Configuration(object):
	"""
	Singleton to the global configuration object.
	"""
	class __SingleConf:
		conffiles = list()

		def __init__(self, filenames):
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

	def __new__(cls, filename=None):
		if not cls._instance:
			cls._instance = cls.__SingleConf(filename)
		return cls._instance.config
