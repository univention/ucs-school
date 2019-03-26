#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2019 Univention GmbH
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
import copy
from random import choice, shuffle
import string
import sys
import logging
import collections
from logging.handlers import MemoryHandler, TimedRotatingFileHandler
from contextlib import contextmanager
import subprocess

from six import string_types
from psutil import process_iter, NoSuchProcess
import colorlog
import lazy_object_proxy
import ruamel.yaml

from univention.lib.policy_result import policy_result
from univention.lib.i18n import Translation
from univention.config_registry import ConfigRegistry
import univention.debug as ud

try:
	from typing import Any, AnyStr, Dict, List, Optional, Tuple, Union
except ImportError:
	pass


# "global" translation for ucsschool.lib.models
_ = Translation('python-ucs-school').translate
LOGGING_CONFIG_PATH = '/etc/ucsschool/logging.yaml'


def _load_logging_config(path=LOGGING_CONFIG_PATH):  # type: (Optional[str]) -> Dict[str, Dict[str, str]]
	with open(path, 'r') as fp:
		config = ruamel.yaml.load(fp, ruamel.yaml.RoundTripLoader)
	return config


_logging_config = lazy_object_proxy.Proxy(_load_logging_config)
CMDLINE_LOG_FORMATS = lazy_object_proxy.Proxy(lambda: _logging_config['cmdline'])
FILE_LOG_FORMATS = lazy_object_proxy.Proxy(lambda: _logging_config['file'])
LOG_DATETIME_FORMAT = lazy_object_proxy.Proxy(lambda: _logging_config['date'])
LOG_COLORS = lazy_object_proxy.Proxy(lambda: _logging_config['colors'])

_handler_cache = dict()
_pw_length_cache = dict()


# "global" ucr for ucsschool.lib.models
ucr = ConfigRegistry()
ucr.load()


def _remove_password_from_log_record(record):  # type: (logging.LogRecord) -> logging.LogRecord
	for index, arg in enumerate(record.args):
		if isinstance(arg, collections.Mapping) and isinstance(arg.get('password'), string_types):
			# don't change original record arguments as it would change the objects being logged
			args = copy.deepcopy(record.args)
			args[index]['password'] = '*' * 8
			record.args = args
	return record


class UniFileHandler(TimedRotatingFileHandler):
	"""
	TimedRotatingFileHandler that can set file permissions and removes
	password entries from from dicts in args.
	"""
	def __init__(
			self,
			filename,  # type: AnyStr
			when='h',  # type: Optional[AnyStr]
			interval=1,  # type: Optional[int]
			backupCount=0,  # type: Optional[int]
			encoding=None,  # type: Optional[AnyStr]
			delay=False,  # type: Optional[bool]
			utc=False,  # type: Optional[bool]
			fuid=None,  # type: Optional[int]
			fgid=None,  # type: Optional[int]
			fmode=None  # type: Optional[int]
	):
		# type: (...) -> None
		self._fuid = fuid or os.geteuid()
		self._fgid = fgid or os.getegid()
		self._fmode = fmode or 0o600
		super(UniFileHandler, self).__init__(filename, when, interval, backupCount, encoding, delay, utc)

	def _open(self):
		"""set file permissions on log file"""
		stream = super(UniFileHandler, self)._open()
		file_stat = os.fstat(stream.fileno())
		if file_stat.st_uid != self._fuid or file_stat.st_gid != self._fgid:
			os.fchown(stream.fileno(), self._fuid, self._fgid)
		if file_stat.st_mode != self._fmode:
			os.fchmod(stream.fileno(), self._fmode)
		return stream

	def emit(self, record):
		"""remove password from from dicts in args"""
		_remove_password_from_log_record(record)
		super(UniFileHandler, self).emit(record)


class UniStreamHandler(colorlog.StreamHandler):
	"""
	Colorizing console stream handler that removes password entries from from
	dicts in args.
	"""
	def __init__(
			self,
			stream=None,  # type: file
			fuid=None,  # type: Optional[int]
			fgid=None,  # type: Optional[int]
			fmode=None  # type: Optional[int]
	):
		# type: (...) -> None
		"""
		`fuid`, `fgid` and `fmode` are here only for similarity of interface
		to UniFileHandler and are ignored.
		"""
		super(UniStreamHandler, self).__init__(stream)

	def emit(self, record):
		"""remove password from from dicts in args"""
		_remove_password_from_log_record(record)
		super(UniStreamHandler, self).emit(record)


class ModuleHandler(logging.Handler):
	"""Adapter: use Python logging but emit through univention debug"""
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
		# type: (Optional[int], Optional[int]) -> None
		self._udebug_facility = udebug_facility
		super(ModuleHandler, self).__init__(level)

	def emit(self, record):
		"""log to univention debug, remove password from dicts in args"""
		_remove_password_from_log_record(record)
		msg = self.format(record)
		if isinstance(msg, unicode):
			msg = msg.encode("utf-8")
		udebug_level = self.LOGGING_TO_UDEBUG[record.levelname]
		ud.debug(self._udebug_facility, udebug_level, msg)


def add_stream_logger_to_schoollib(level="DEBUG", stream=sys.stderr, log_format=None, name=None):
	# type: (Optional[AnyStr], Optional[file], Optional[AnyStr], Optional[AnyStr]) -> logging.Logger
	"""
	Outputs all log messages of the models code to a stream (default: "stderr")::

		from ucsschool.lib.models.utils import add_stream_logger_to_schoollib
		add_module_logger_to_schoollib()
		# or:
		add_module_logger_to_schoollib(level='ERROR', stream=sys.stdout, log_format='ERROR (or worse): %(message)s')
	"""
	logger = logging.getLogger(name or 'ucsschool')
	if logger.level < logging.DEBUG:
		# Must set this higher than NOTSET or the root loggers level (WARN)
		# will be used.
		logger.setLevel(logging.DEBUG)
	if not any(isinstance(handler, UniStreamHandler) for handler in logger.handlers):
		logger.addHandler(get_stream_handler(level, stream=stream, fmt=log_format))
	return logger


def add_module_logger_to_schoollib():
	# type: () -> None
	logger = logging.getLogger('ucsschool')
	if logger.level < logging.DEBUG:
		# Must set this higher than NOTSET or the root loggers level (WARN)
		# will be used.
		logger.setLevel(logging.DEBUG)
	if not any(handler.name in ('ucsschool_mem_handler', 'ucsschool_mod_handler') for handler in logger.handlers):
		module_handler = ModuleHandler(udebug_facility=ud.MODULE)
		module_handler.setLevel(logging.DEBUG)
		module_handler.set_name('ucsschool_mod_handler')
		memory_handler = MemoryHandler(-1, flushLevel=logging.DEBUG, target=module_handler)
		memory_handler.setLevel(logging.DEBUG)
		memory_handler.set_name('ucsschool_mem_handler')
		logger.addHandler(memory_handler)
	else:
		logger.info('add_module_logger_to_schoollib() should only be called once! Skipping...')


def create_passwd(length=8, dn=None, specials='$%&*-+=:.?'):
	# type: (Optional[int], Optional[AnyStr], Optional[AnyStr]) -> AnyStr
	assert length > 0

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

	pw = list()
	specials_allowed = length / 5  # 20% specials in a password is enough
	specials = list(specials) if specials else []
	lowercase = list(string.lowercase)
	for char in ('i', 'l', 'o'):
		# remove chars that are easy to mistake for one another
		lowercase.remove(char)
	uppercase = list(string.uppercase)
	for char in ('I', 'L', 'O'):
		uppercase.remove(char)
	digits = list(string.digits)
	for char in ('0', '1'):
		digits.remove(char)

	# password will start with a letter (prepended at end of function)
	length -= 1

	# one symbol from each character class, MS requirement:
	# https://technet.microsoft.com/en-us/library/cc786468(v=ws.10).aspx
	if length >= 3:
		pw.append(choice(lowercase))
		pw.append(choice(uppercase))
		pw.append(choice(digits))
		length -= 3
	if specials and length and specials_allowed:
		pw.append(choice(specials))
		specials_allowed -= 1
		length -= 1

	# fill up with random chars (but not more than 20% specials)
	for _x in range(length):
		char = choice(lowercase + uppercase + digits + (specials if specials_allowed else []))
		if char in specials:
			specials_allowed -= 1
		pw.append(char)

	shuffle(pw)
	pw = [choice(lowercase + uppercase)] + pw  # start with a letter
	return ''.join(pw)


def flatten(list_of_lists):  # type: (List[List[Any]]) -> List[Any]
	# return [item for sublist in list_of_lists for item in sublist]
	# => does not work well for strings in list
	ret = []
	for sublist in list_of_lists:
		if isinstance(sublist, (list, tuple)):
			ret.extend(flatten(sublist))
		else:
			ret.append(sublist)
	return ret


def loglevel_int2str(level):  # type: (Union[int, str]) -> str
	"""Convert numeric loglevel to string name."""
	if isinstance(level, int):
		return logging.getLevelName(level)
	else:
		return level


def nearest_known_loglevel(level):
	"""
	Get loglevel nearest to those known in `CMDLINE_LOG_FORMATS` and
	`FILE_LOG_FORMATS`.
	"""
	# TODO: smarter algo than just looking at highest and lowest
	if level in FILE_LOG_FORMATS:
		return level
	if isinstance(level, int):
		int_level = level
	else:
		int_level = logging._levelNames.get(level, 10)
	if int_level <= logging.DEBUG:
		return logging.DEBUG
	elif int_level >= logging.CRITICAL:
		return logging.CRITICAL
	else:
		return logging.INFO


def get_stream_handler(level, stream=None, fmt=None, datefmt=None, cls=None):
	# type: (Union[int, str], Optional[file], Optional[str], Optional[str], Optional[type]) -> logging.Handler
	"""
	Create a colored stream handler, usually for the console.

	:param level: log level
	:type level: int or str
	:param file stream: opened file to write to (/dev/stdout if None)
	:param str fmt: log message format (will be passt to a Formatter instance)
	:param str datefmt: date format (will be passt to a Formatter instance)
	:param type cls: Formatter class to use, defaults to
		:py:class:`colorlog.TTYColoredFormatter`, unless the environment
		variable `UCSSCHOOL_FORCE_COLOR_TERM` is set, then
		:py:class:`colorlog.ColoredFormatter` is used
	:return: a handler
	:rtype: logging.Handler
	"""
	fmt = '%(log_color)s{}'.format(fmt or CMDLINE_LOG_FORMATS[loglevel_int2str(nearest_known_loglevel(level))])
	datefmt = datefmt or str(LOG_DATETIME_FORMAT)
	formatter_kwargs = {'fmt': fmt, 'datefmt': datefmt}
	if os.environ and 'UCSSCHOOL_FORCE_COLOR_TERM' in os.environ:
		color_cls = colorlog.ColoredFormatter
	else:
		color_cls = colorlog.TTYColoredFormatter
	cls = cls or color_cls
	if issubclass(cls, colorlog.ColoredFormatter):
		formatter_kwargs['log_colors'] = LOG_COLORS
	formatter = cls(**formatter_kwargs)
	handler = UniStreamHandler(stream=stream)
	handler.setFormatter(formatter)
	handler.setLevel(level)
	return handler


def get_file_handler(level, filename, fmt=None, datefmt=None, uid=None, gid=None, mode=None):
	# type: (Union[int, str], str, Optional[str], Optional[str], Optional[int], Optional[int], Optional[int]) -> logging.Handler
	"""
	Create a :py:class:`UniFileHandler` (TimedRotatingFileHandler) for logging
	to a file.

	:param level: log level
	:type level: int or str
	:param str filename: path of file to write to
	:param str fmt: log message format (will be passt to a Formatter instance)
	:param str datefmt: date format (will be passt to a Formatter instance)
	:param int uid: user that the file should belong to (current user if None)
	:param int gid: group that the file should belong to (current users
		primary group if None)
	:param int mode: permissions of the file
	:return: a handler
	:rtype: logging.Handler
	"""
	fmt = fmt or FILE_LOG_FORMATS[loglevel_int2str(nearest_known_loglevel(level))]
	datefmt = datefmt or str(LOG_DATETIME_FORMAT)
	formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
	handler = UniFileHandler(filename, when="D", backupCount=10000000, fuid=uid, fgid=gid, fmode=mode)
	handler.setFormatter(formatter)
	handler.setLevel(level)
	return handler


def get_logger(
		name,  # type: AnyStr
		level="INFO",  # type: Optional[AnyStr]
		target=sys.stdout,  # type: Optional[file]
		handler_kwargs=None,  # type: Optional[Dict[AnyStr, Any]]
		formatter_kwargs=None  # type: Optional[Dict[AnyStr, Any]]
):
	# type: (...) -> logging.Logger
	"""
	Get a logger object below the ucsschool root logger.

	.. deprecated:: 4.4 v2
		Use `logging.getLogger(__name__)` and :py:func:`get_stream_handler()`,
		:py:func:`get_file_handler()`.

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

	:param name: str: will be appended to "ucsschool." as name of the logger
	:param level: str: loglevel (DEBUG, INFO etc)
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
		fmt = '%(log_color)s{}'.format(CMDLINE_LOG_FORMATS[level])
		fmt_cls = colorlog.TTYColoredFormatter
	else:
		handler_defaults = dict(cls=UniFileHandler, filename=target, when="D", backupCount=10000000)
		fmt = FILE_LOG_FORMATS[level]
		fmt_cls = logging.Formatter
	handler_defaults.update(handler_kwargs)
	fmt_kwargs = dict(cls=fmt_cls, fmt=fmt, datefmt=LOG_DATETIME_FORMAT)
	fmt_kwargs.update(formatter_kwargs)
	if issubclass(fmt_cls, colorlog.ColoredFormatter):
		fmt_kwargs['log_colors'] = LOG_COLORS

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
	_logger.warn('get_logger() is deprecated, use "logging.getLogger(__name__)" instead.')
	return _logger


@contextmanager
def stopped_notifier(strict=True):  # type: (Optional[bool]) -> None
	"""
	Stops univention-directory-notifier while in a block and starts it in the
	end. Service if stopped/started by /etc/init.d.

	Will not start if ``ucr get notifier/autostart=no`` -- but *will* stop!

	::

		with stopped_notifier():
			...

	:param bool strict: raise RuntimeError if stopping fails
	:raises RuntimeError: if stopping failed and ``strict=True``
	"""
	service_name = 'univention-directory-notifier'
	logger = logging.getLogger(__name__)

	def _run(args):
		process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()
		if stdout:
			logger.info(stdout)
		if stderr:
			logger.error(stderr)
		return process.returncode == 0

	notifier_running = False
	logger.info('Stopping %s', service_name)
	for process in process_iter():
		try:
			if process.name() == service_name:
				notifier_running = True
				break
		except (IOError, NoSuchProcess):
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
		logger.info('Starting %s', service_name)
		if not notifier_running:
			logger.warning('Notifier was not running! Skipping')
		else:
			start_disabled = ucr.is_false('notifier/autostart', False)
			command = ['/etc/init.d/%s' % service_name, 'start']
			if not start_disabled and _run(command):
				logger.info('%s started', service_name)
			else:
				logger.error('Failed to start %s... Bad news! Better run "%s" manually!', service_name, ' '.join(command))  # correct: shlex... unnecessary


def _write_logging_config(path=LOGGING_CONFIG_PATH):  # type: (Optional[str]) -> None
	with open(path, 'w') as fp:
		ruamel.yaml.dump(
			{
				'date': str(LOG_DATETIME_FORMAT),
				'cmdline': collections.OrderedDict(CMDLINE_LOG_FORMATS),
				'colors': collections.OrderedDict(LOG_COLORS),
				'file': collections.OrderedDict(FILE_LOG_FORMATS),
			},
			fp,
			ruamel.yaml.RoundTripDumper,
			indent=4
		)
