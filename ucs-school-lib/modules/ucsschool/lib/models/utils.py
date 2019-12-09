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

import collections
import copy
import grp
import logging
import os
import pwd
import string
import subprocess
import sys
from contextlib import contextmanager
from logging.handlers import TimedRotatingFileHandler
from random import choice, shuffle
from typing import Any, AnyStr, Dict, List, Optional, Sequence, Tuple, Union

import colorlog
import lazy_object_proxy
import ruamel.yaml
from pkg_resources import resource_stream
from six import string_types
from univention.config_registry import ConfigRegistry
# from univention.lib.policy_result import policy_result
from univention.lib.i18n import Translation

# "global" translation for ucsschool.lib.models
_ = Translation('python-ucs-school').translate


# TODO: get base/univention-policy/python-lib/policy_result.py and static univention-policy-result binary
def policy_result(dn):  # type: (str) -> Tuple[Dict[str, List[Any]], Dict[str, str]]
	return {"univentionPWLength": ["8"]}, {"univentionPWLength": "Policy-DN"}


def _load_logging_config():  # type: () -> Dict[str, Dict[str, str]]
	with resource_stream("ucsschool.lib", "logging.yaml") as fp:
		return ruamel.yaml.load(fp, ruamel.yaml.RoundTripLoader)


def _ucr():  # type: () -> ConfigRegistry
	ucr = ConfigRegistry()
	ucr.load()
	return ucr


def env_or_ucr(key: str) -> str:
	try:
		return os.environ[key.replace("/", "_").upper()]
	except KeyError:
		return ucr[key]


_logging_config = lazy_object_proxy.Proxy(_load_logging_config)
CMDLINE_LOG_FORMATS = lazy_object_proxy.Proxy(lambda: _logging_config['cmdline'])
FILE_LOG_FORMATS = lazy_object_proxy.Proxy(lambda: _logging_config['file'])
LOG_DATETIME_FORMAT = lazy_object_proxy.Proxy(lambda: _logging_config['date'])
LOG_COLORS = lazy_object_proxy.Proxy(lambda: _logging_config['colors'])

_handler_cache = dict()
_pw_length_cache = dict()
ucr = lazy_object_proxy.Proxy(_ucr)  # type: ConfigRegistry  # "global" ucr for ucsschool.lib.models
ucr_username_max_length = lazy_object_proxy.Proxy(lambda: int(ucr.get("ucsschool/username/max_length", 20)))  # type: int


def mkdir_p(dir_name, user, group, mode):  # type: (str, Union[str, int], Union[str, int], int) -> None
	"""
	Recursively create directories (like "mkdir -p").

	:param str dir_name: path to create
	:param str user: username of owner of new directories
	:param str group: group name for ownership of new directories
	:param octal mode: permission bits to set for new directories
	:returns: None
	:rtype: None
	"""
	if not dir_name:
		return

	parent = os.path.dirname(dir_name)
	if not os.path.exists(parent):
		mkdir_p(parent, user, group, mode)

	if not os.path.exists(dir_name):
		if isinstance(user, str):
			uid = pwd.getpwnam(user).pw_uid
		else:
			uid = user
		if isinstance(group, str):
			gid = grp.getgrnam(group).gr_gid
		else:
			gid = group
		os.mkdir(dir_name, mode)
		os.chown(dir_name, uid, gid)


def _remove_password_from_log_record(record):  # type: (logging.LogRecord) -> logging.LogRecord
	def replace_password(obj, attr):
		ori = getattr(obj, attr)
		if isinstance(ori, collections.abc.Mapping) and isinstance(ori.get('password'), string_types):
			# don't change original record arguments as it would change the objects being logged
			new_dict = copy.deepcopy(ori)
			new_dict['password'] = '*' * 8
			setattr(obj, attr, new_dict)

	# check args
	if isinstance(record.args, tuple):
		# multiple arguments
		for index, arg in enumerate(record.args):
			# cannot call replace_password() to replace single arg, because a tuple is not mutable,
			# -> have to replace all of record.args
			if isinstance(arg, collections.abc.Mapping) and isinstance(arg.get('password'), string_types):
				# don't change original record arguments as it would change the objects being logged
				args = copy.deepcopy(record.args)
				args[index]['password'] = '*' * 8
				record.args = args
	else:
		# one argument
		replace_password(record, 'args')
	# check msg
	replace_password(record, 'msg')
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
		parent_dir = os.path.dirname(self.baseFilename)
		if not os.path.exists(parent_dir):
			mkdir_p(parent_dir, self._fuid, self._fgid, 0o755)
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


def add_stream_logger_to_schoollib(level="DEBUG", stream=sys.stderr, log_format=None, name=None):
	# type: (Optional[AnyStr], Optional[file], Optional[AnyStr], Optional[AnyStr]) -> logging.Logger
	"""
	Outputs all log messages of the models code to a stream (default: "stderr")::

		from ucsschool.lib.models.utils import add_stream_logger_to_schoollib
		add_stream_logger_to_schoollib()
		# or:
		add_stream_logger_to_schoollib(level='ERROR', stream=sys.stdout, log_format='ERROR (or worse): %(message)s')
	"""
	logger = logging.getLogger(name or 'ucsschool')
	if logger.level < logging.DEBUG:
		# Must set this higher than NOTSET or the root loggers level (WARN)
		# will be used.
		logger.setLevel(logging.DEBUG)
	if not any(isinstance(handler, UniStreamHandler) for handler in logger.handlers):
		logger.addHandler(get_stream_handler(level, stream=stream, fmt=log_format))
	return logger


class UCSTTYColoredFormatter(colorlog.TTYColoredFormatter):
	"""
	Subclass of :py:class:`colorlog.TTYColoredFormatter` that will force
	colorization on, in case UCSSCHOOL_FORCE_COLOR_TERM is found in env.
	"""
	def color(self, log_colors, level_name):
		if os.environ and 'UCSSCHOOL_FORCE_COLOR_TERM' in os.environ:
			return colorlog.ColoredFormatter.color(self, log_colors, level_name)
		else:
			return super(UCSTTYColoredFormatter, self).color(log_colors, level_name)


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
	lowercase = list(string.ascii_lowercase)
	for char in ('i', 'l', 'o'):
		# remove chars that are easy to mistake for one another
		lowercase.remove(char)
	uppercase = list(string.ascii_uppercase)
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
		try:
			int_level = logging._levelNames.get(level, 10)  # py2
		except AttributeError:
			int_level = logging._nameToLevel.get(level, 10)  # py3
	if int_level <= logging.DEBUG:
		return logging.DEBUG
	elif int_level >= logging.CRITICAL:
		return logging.CRITICAL
	else:
		return logging.INFO


def get_stream_handler(level, stream=None, fmt=None, datefmt=None, fmt_cls=None):
	# type: (Union[int, str], Optional[file], Optional[str], Optional[str], Optional[type]) -> logging.Handler
	"""
	Create a colored stream handler, usually for the console.

	:param level: log level
	:type level: int or str
	:param file stream: opened file to write to (/dev/stdout if None)
	:param str fmt: log message format (will be passt to a Formatter instance)
	:param str datefmt: date format (will be passt to a Formatter instance)
	:param type fmt_cls: Formatter class to use, defaults to
		:py:class:`UCSTTYColoredFormatter`
	:return: a handler
	:rtype: logging.Handler
	"""
	if stream is None:
		stream = sys.stderr
	fmt = '%(log_color)s{}'.format(fmt or CMDLINE_LOG_FORMATS[loglevel_int2str(nearest_known_loglevel(level))])
	datefmt = datefmt or str(LOG_DATETIME_FORMAT)
	formatter_kwargs = {'fmt': fmt, 'datefmt': datefmt}
	fmt_cls = fmt_cls or UCSTTYColoredFormatter
	if issubclass(fmt_cls, colorlog.ColoredFormatter):
		formatter_kwargs['log_colors'] = LOG_COLORS
	if issubclass(fmt_cls, colorlog.TTYColoredFormatter):
		formatter_kwargs['stream'] = stream
	formatter = fmt_cls(**formatter_kwargs)
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


def exec_cmd(cmd, log=False, raise_exc=False, **kwargs):
	# type: (Sequence[str], Optional[bool], Optional[bool], **Any) -> Tuple[int, str, str]
	"""
	Execute command.

	:param list(str) cmd: command line as list of strings
	:param bool log: log text returned in stdout (with level INFO) and text
		returned in stderr (with level ERROR)
	:param bool raise_exc: raise RunTime
	:param dict kwargs: arguments to pass to `subprocess.Popen()` call
	:return: 3-tuple: returncode (int), stdout (str), stderr (str)
	:rtype: tuple(int, str, str)
	:raises subprocess.CalledProcessError: if raise_exc is True and the return
		code was != 0
	:raises OSError: if cmd[0] does not exist: "No such file or directory"
	"""
	assert all(isinstance(arg, string_types) for arg in cmd)
	kwargs["stdout"] = kwargs.get("stdout", subprocess.PIPE)
	kwargs["stderr"] = kwargs.get("stderr", subprocess.PIPE)
	process = subprocess.Popen(cmd, **kwargs)
	stdout, stderr = process.communicate()
	if log:
		logger = logging.getLogger(__name__)
		if stdout:
			logger.info(stdout)
		if stderr:
			logger.error(stderr)
	if raise_exc and process.returncode:
		raise subprocess.CalledProcessError(returncode=process.returncode, cmd=cmd, output=stderr or stdout)
	return process.returncode, stdout, stderr


@contextmanager
def stopped_notifier(strict=True):  # type: (Optional[bool]) -> None
	try:
		yield
	finally:
		pass


def _write_logging_config(path):  # type: (str) -> None
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
