#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2016 Univention GmbH
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

from random import choice, shuffle
import string
import sys
import logging
from logging.handlers import MemoryHandler, TimedRotatingFileHandler
from contextlib import contextmanager
import subprocess

from psutil import process_iter

from univention.lib.policy_result import policy_result
from univention.lib.i18n import Translation
from univention.config_registry import ConfigRegistry
import univention.debug as ud


# "global" translation for ucsschool.lib.models
_ = Translation('python-ucs-school').translate

FILE_LOG_FORMATS = dict(
	DEBUG="%(asctime)s %(levelname)-5s %(module)s.%(funcName)s:%(lineno)d  %(message)s",
	INFO="%(asctime)s %(levelname)-5s %(message)s"
)
for lvl in ["CRITICAL", "ERROR", "WARN", "WARNING"]:
	FILE_LOG_FORMATS[lvl] = FILE_LOG_FORMATS["INFO"]
FILE_LOG_FORMATS["NOTSET"] = FILE_LOG_FORMATS["DEBUG"]
CMDLINE_LOG_FORMATS = dict(
	DEBUG="%(asctime)s %(levelname)-5s %(module)s.%(funcName)s:%(lineno)d  %(message)s",
	INFO="%(message)s",
	WARN="%(levelname)-5s  %(message)s"
)
for lvl in ["CRITICAL", "ERROR", "WARNING"]:
	CMDLINE_LOG_FORMATS[lvl] = CMDLINE_LOG_FORMATS["WARN"]
CMDLINE_LOG_FORMATS["NOTSET"] = CMDLINE_LOG_FORMATS["DEBUG"]
LOG_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

_handler_cache = dict()
_module_handler = None
_pw_length_cache = dict()


# "global" ucr for ucsschool.lib.models
ucr = ConfigRegistry()
ucr.load()

logger = logging.getLogger("ucsschool")
# Must set this higher than NOTSET or the root loggers level (WARN)
# will be used.
logger.setLevel(logging.DEBUG)


class UniFileHandler(TimedRotatingFileHandler):
	pass


class UniStreamHandler(logging.StreamHandler):
	pass


class ModuleHandler(logging.Handler):
	LOGGING_TO_UDEBUG = dict(
		CRITICAL=ud.ERROR,
		ERROR=ud.ERROR,
		WARN=ud.WARN,
		WARNING=ud.WARN,
		INFO=ud.PROCESS,
		DEBUG=ud.INFO,
		NOTSET=ud.INFO
	)

	def __init__(self, level=logging.NOTSET, udebug_facility=ud.LISTENER):
		self._udebug_facility = udebug_facility
		super(ModuleHandler, self).__init__(level)

	def emit(self, record):
		msg = self.format(record)
		if isinstance(msg, unicode):
			msg = msg.encode("utf-8")
		udebug_level = self.LOGGING_TO_UDEBUG[record.levelname]
		ud.debug(self._udebug_facility, udebug_level, msg)


def add_stream_logger_to_schoollib(level="DEBUG", stream=sys.stderr, log_format=None, name=None):
	"""Outputs all log messages of the models code to a stream (default: "stderr")
	>>> from ucsschool.lib.models.utils import add_stream_logger_to_schoollib
	>>> add_module_logger_to_schoollib()
	>>> # or:
	>>> add_module_logger_to_schoollib(level='ERROR', stream=sys.stdout, log_format='ERROR (or worse): %(message)s')
	"""
	return get_logger(name, level, stream, formatter_kwargs={"fmt": log_format, "datefmt": None})


def add_module_logger_to_schoollib():
	global _module_handler
	if _module_handler is None:
		module_handler = ModuleHandler(udebug_facility=ud.MODULE)
		_module_handler = MemoryHandler(-1, flushLevel=logging.DEBUG, target=module_handler)
		_module_handler.setLevel(logging.DEBUG)
		logger.addHandler(_module_handler)
	else:
		logger.info('add_module_logger_to_schoollib() should only be called once! Skipping...')
	return _module_handler


def create_passwd(length=8, dn=None, specials='@#$%&*-_+=\:,.;?/()'):
	if dn:
		# get dn pw policy
		if not _pw_length_cache.get(dn):
			try:
				results, policies = policy_result(dn)
				_pw_length_cache[dn] = int(results.get('univentionPWLength', ['8'])[0])
			except Exception:
				pass
		length = _pw_length_cache.get(dn, length)

		# get ou pw policy
		ou = 'ou=' + dn[dn.find('ou=') + 3:]
		if not _pw_length_cache.get(ou):
			try:
				results, policies = policy_result(ou)
				_pw_length_cache[ou] = int(results.get('univentionPWLength', ['8'])[0])
			except Exception:
				pass
		length = _pw_length_cache.get(ou, length)

	if not specials:
		specials = ''
	pw = list()
	if length >= 4:
		pw.append(choice(string.lowercase))
		pw.append(choice(string.uppercase))
		pw.append(choice(string.digits))
		if specials:
			pw.append(choice(specials))
		length -= len(pw)
	pw.extend(choice(string.ascii_letters + string.digits + specials) for x in range(length))
	shuffle(pw)
	return ''.join(pw)


def flatten(list_of_lists):
	# return [item for sublist in list_of_lists for item in sublist]
	# => does not work well for strings in list
	ret = []
	for sublist in list_of_lists:
		if isinstance(sublist, (list, tuple)):
			ret.extend(flatten(sublist))
		else:
			ret.append(sublist)
	return ret


def get_logger(name, level="INFO", target=sys.stdout, handler_kwargs=None, formatter_kwargs=None):
	"""
	Get a logger object below the ucsschool root logger.

	* The logger will use UniStreamHandler(StreamHandler) for streams
	(sys.stdout etc) and UniFileHandler(TimedRotatingFileHandler) for files if
	not configured differently through handler_kwargs[cls].
	* A call with the same name will return the same logging object.
	* There is only one handler per name-target combination.
	* If name and target are the same, and only the log level changes, it will
	return the logging object with the same handlers and change both the log
	level of the respective handler and of the logger object to be the lowest
	of the previous and the new level.
	* Complete output customization is possible, setting kwargs for the
	constructors of the handler and formatter.
	* Using custom handler and formatter classes is possible by configuring
	the 'cls' key of handler_kwargs and formatter_kwargs.
	* The logging level can be configured through ucsschool/logging/level/<name>.

	:param name: str: will be appended to "ucsschool." as name of the logger
	:param level: str: loglevel (DEBUG, INFO etc), the UCRV
	ucsschool/logging/level/<name> overwrites this setting!
	:param target: stream (open file) or a str (file path)
	:param handler_kwargs: dict: will be passed to the handlers constructor.
	It cannot be used to modify a handler, as it is only used at creation time.
	If it has a key 'cls' it will be used as handler instead of UniFileHandler
	or UniStreamHandler. It should be a subclass of one of those!
	:param formatter_kwargs: dict: will be passed to the formatters constructor,
	if it has a key 'cls' it will be used to create a formatter instead of
	logging.Formatter.
	:return: a python logging object
	"""
	if not name:
		name = "noname"
	level = ucr.get("ucsschool/logging/level/{}".format(name), level)
	if isinstance(target, file) or hasattr(target, "write"):
		# file like object
		filename = target.name
	else:
		filename = target
	cache_key = "{}-{}".format(name, filename)
	_logger = logging.getLogger("ucsschool.{}".format(name))

	if cache_key in _handler_cache and getattr(logging, level) >= _handler_cache[cache_key].level:
		return _logger

	# The logger objects level must be the lowest of all handlers, or handlers
	# with a higher level will not be able to log anything.
	if getattr(logging, level) < _logger.level:
		_logger.setLevel(level)

	if not isinstance(handler_kwargs, dict):
		handler_kwargs = dict()
	if not isinstance(formatter_kwargs, dict):
		formatter_kwargs = dict()

	if isinstance(target, file) or hasattr(target, "write"):
		handler_defaults = dict(cls=UniStreamHandler, stream=target)
		fmt = CMDLINE_LOG_FORMATS[level]
	else:
		handler_defaults = dict(cls=UniFileHandler, filename=target, when="D", backupCount=10000000)
		fmt = FILE_LOG_FORMATS[level]
	handler_defaults.update(handler_kwargs)
	fmt_kwargs = dict(cls=logging.Formatter, fmt=fmt, datefmt=LOG_DATETIME_FORMAT)
	fmt_kwargs.update(formatter_kwargs)

	if _logger.level == logging.NOTSET:
		# fresh logger
		_logger.setLevel(level)

	if cache_key in _handler_cache:
		# Check if loglevel from this request is lower than the one used in
		# the cached loggers handler. We do only lower level, never raise it.
		if getattr(logging, level) < _handler_cache[cache_key].level:
			handler = _handler_cache[cache_key]
			handler.setLevel(level)
			formatter = fmt_kwargs.pop("cls")(**fmt_kwargs)
			handler.setFormatter(formatter)
	else:
		# Create handler and formatter from scratch.
		handler = handler_defaults.pop("cls")(**handler_defaults)
		handler.set_name("ucsschool.{}".format(name))
		handler.setLevel(level)
		formatter = fmt_kwargs.pop("cls")(**fmt_kwargs)
		handler.setFormatter(formatter)
		_logger.addHandler(handler)
		_handler_cache[cache_key] = handler
	return _logger


@contextmanager
def stopped_notifier(strict=True):
	'''Stops univention-directory-notifier while in a block
	Starts it in the end
	Service if stopped/started by /etc/init.d
	Raises RuntimeError if stopping failed and strict=True
	Will not start if ucr get notifier/autostart=no -- but stop!
	>>> with stopped_notifier():
	>>> 	...
	'''
	service_name = 'univention-directory-notifier'
	def _run(args):
		process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()
		if stdout:
			logger.info(stdout)
		if stderr:
			logger.error(stderr)
		return process.returncode == 0

	notifier_running = False
	logger.warning('Stopping %s', service_name)
	for process in process_iter():
		try:
			if process.name == service_name:
				notifier_running = True
				break
		except IOError:
			pass
	if not notifier_running:
		logger.warning('%s is not running! Skipping', service_name)
	else:
		if _run(['/etc/init.d/%s' % service_name, 'stop']):
			logger.info('%s stopped', service_name)
		else:
			logger.error('Failed to stop %s...', service_name)
			if strict:
				raise RuntimeError('Failed to stop %s, but this seems to be very important (strict=True was specified)' % service_name)
			else:
				logger.warning('In the end, will try to start it nonetheless')
	try:
		yield
	finally:
		logger.warning('Starting %s', service_name)
		if not notifier_running:
			logger.warning('Notifier was not running! Skipping')
		else:
			start_disabled = ucr.is_false('notifier/autostart', False)
			command = ['/etc/init.d/%s' % service_name, 'start']
			if not start_disabled and _run(command):
				logger.info('%s started', service_name)
			else:
				logger.error('Failed to start %s... Bad news! Better run "%s" manually!', service_name, ' '.join(command)) # correct: shlex... unnecessary
