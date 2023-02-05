#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2023 Univention GmbH
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
from io import IOBase
from logging.handlers import MemoryHandler, TimedRotatingFileHandler
from random import choice, shuffle
from typing import IO, Any, Dict, List, Optional, Sequence, Tuple, Union

import apt
import colorlog
import lazy_object_proxy
import ruamel.yaml
from six import string_types

import univention.debug as ud
from univention.config_registry import ConfigRegistry, handler_set
from univention.lib.i18n import Translation
from univention.lib.policy_result import policy_result

# "global" translation for ucsschool.lib.models
_ = Translation("python-ucs-school").translate
LOGGING_CONFIG_PATH = "/etc/ucsschool/logging.yaml"


class NotInstalled(Exception):
    """
    Raised by `get_package_version()` when the requested package is not
    installed.
    """

    pass


class UnknownPackage(Exception):
    """
    Raised by `get_package_version()` when the requested package is not
    known in the Debian package cache.
    """

    pass


class ValidationDataFilter(logging.Filter):
    def filter(self, record):
        return record.name != "UCSSchool-Validation"


def _load_logging_config(path=LOGGING_CONFIG_PATH):  # type: (Optional[str]) -> Dict[str, Dict[str, str]]
    with open(path, "r") as fp:
        config = ruamel.yaml.load(fp, ruamel.yaml.RoundTripLoader)
    return config


def _ucr():  # type: () -> ConfigRegistry
    ucr = ConfigRegistry()
    ucr.load()
    return ucr


_logging_config = lazy_object_proxy.Proxy(_load_logging_config)  # type: Dict[str, Dict[str, str]]
CMDLINE_LOG_FORMATS = lazy_object_proxy.Proxy(lambda: _logging_config["cmdline"])  # type: Dict[str, str]
FILE_LOG_FORMATS = lazy_object_proxy.Proxy(lambda: _logging_config["file"])  # type: Dict[str, str]
LOG_DATETIME_FORMAT = lazy_object_proxy.Proxy(lambda: _logging_config["date"])  # type: str
LOG_COLORS = lazy_object_proxy.Proxy(lambda: _logging_config["colors"])  # type: Dict[str, str]

_handler_cache = {}  # type: Dict[str, logging.Handler]
_pw_length_cache = {}  # type: Dict[str, int]
ucr = lazy_object_proxy.Proxy(_ucr)  # type: ConfigRegistry  # "global" ucr for ucsschool.lib.models
ucr_username_max_length = lazy_object_proxy.Proxy(
    lambda: int(ucr.get("ucsschool/username/max_length", 20))
)  # type: int


def mkdir_p(dir_name, user, group, mode):
    # type: (str, Union[str, int], Union[str, int], int) -> None
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
        if isinstance(ori, collections.Mapping) and isinstance(ori.get("password"), string_types):
            # don't change original record arguments as it would change the objects being logged
            new_dict = copy.deepcopy(ori)
            new_dict["password"] = "*" * 8
            setattr(obj, attr, new_dict)

    # check args
    if isinstance(record.args, tuple):
        # multiple arguments
        for index, arg in enumerate(record.args):
            # cannot call replace_password() to replace single arg, because a tuple is not mutable,
            # -> have to replace all of record.args
            if isinstance(arg, collections.Mapping) and isinstance(arg.get("password"), string_types):
                # don't change original record arguments as it would change the objects being logged
                args = copy.deepcopy(record.args)
                args[index]["password"] = "*" * 8
                record.args = args
    else:
        # one argument
        replace_password(record, "args")
    # check msg
    replace_password(record, "msg")
    return record


class UniFileHandler(TimedRotatingFileHandler):
    """
    TimedRotatingFileHandler that can set file permissions and removes
    password entries from from dicts in args.
    """

    def __init__(
        self,
        filename,  # type: str
        when="h",  # type: Optional[str]
        interval=1,  # type: Optional[int]
        backupCount=0,  # type: Optional[int]
        encoding=None,  # type: Optional[str]
        delay=False,  # type: Optional[bool]
        utc=False,  # type: Optional[bool]
        fuid=None,  # type: Optional[int]
        fgid=None,  # type: Optional[int]
        fmode=None,  # type: Optional[int]
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
        stream=None,  # type: IO
        fuid=None,  # type: Optional[int]
        fgid=None,  # type: Optional[int]
        fmode=None,  # type: Optional[int]
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

    LOGGING_TO_UDEBUG = {
        "CRITICAL": ud.ERROR,
        "ERROR": ud.ERROR,
        "WARN": ud.WARN,
        "WARNING": ud.WARN,
        "INFO": ud.PROCESS,
        "DEBUG": ud.INFO,
        "NOTSET": ud.INFO,
    }

    def __init__(self, level=logging.NOTSET, udebug_facility=ud.LISTENER):
        # type: (Optional[int], Optional[int]) -> None
        self._udebug_facility = udebug_facility
        super(ModuleHandler, self).__init__(level)

    def emit(self, record):
        """log to univention debug, remove password from dicts in args"""
        _remove_password_from_log_record(record)
        msg = self.format(record)
        if not isinstance(msg, str) and not isinstance(msg, bytes):  # Python 2
            msg = msg.encode("utf-8")
        udebug_level = self.LOGGING_TO_UDEBUG[record.levelname]
        ud.debug(self._udebug_facility, udebug_level, msg)


class UCSTTYColoredFormatter(colorlog.TTYColoredFormatter):
    """
    Subclass of :py:class:`colorlog.TTYColoredFormatter` that will force
    colorization on, in case UCSSCHOOL_FORCE_COLOR_TERM is found in env.
    """

    def color(self, log_colors, level_name):
        if os.environ and "UCSSCHOOL_FORCE_COLOR_TERM" in os.environ:
            return colorlog.ColoredFormatter.color(self, log_colors, level_name)
        else:
            return super(UCSTTYColoredFormatter, self).color(log_colors, level_name)


def add_stream_logger_to_schoollib(level="DEBUG", stream=sys.stderr, log_format=None, name=None):
    # type: (Optional[str], Optional[IO], Optional[str], Optional[str]) -> logging.Logger
    """
    Outputs all log messages of the models code to a stream (default: "stderr")::

        from ucsschool.lib.models.utils import add_stream_logger_to_schoollib
        add_stream_logger_to_schoollib()
        # or:
        add_stream_logger_to_schoollib(level='ERROR', stream=sys.stdout,
            log_format='ERROR (or worse): %(message)s')
    """
    logger = logging.getLogger(name or "ucsschool")
    if logger.level < logging.DEBUG:
        # Must set this higher than NOTSET or the root loggers level (WARN)
        # will be used.
        logger.setLevel(logging.DEBUG)
    if not any(isinstance(handler, UniStreamHandler) for handler in logger.handlers):
        logger.addHandler(get_stream_handler(level, stream=stream, fmt=log_format))
    return logger


def add_module_logger_to_schoollib():
    # type: () -> None
    logger = logging.getLogger("ucsschool")
    if logger.level < logging.DEBUG:
        # Must set this higher than NOTSET or the root loggers level (WARN)
        # will be used.
        logger.setLevel(logging.DEBUG)
    if not any(
        handler.name in ("ucsschool_mem_handler", "ucsschool_mod_handler") for handler in logger.handlers
    ):
        module_handler = ModuleHandler(udebug_facility=ud.MODULE)
        module_handler.setLevel(logging.DEBUG)
        module_handler.set_name("ucsschool_mod_handler")
        memory_handler = MemoryHandler(-1, flushLevel=logging.DEBUG, target=module_handler)
        memory_handler.setLevel(logging.DEBUG)
        memory_handler.set_name("ucsschool_mem_handler")
        memory_handler.addFilter(ValidationDataFilter())
        logger.addHandler(memory_handler)
    else:
        logger.info("add_module_logger_to_schoollib() should only be called once! Skipping...")


def create_passwd(
    length=8, dn=None, specials="$%&*-+=:.?"
):  # type: (Optional[int], Optional[str], Optional[str]) -> str
    """pseudorandom!"""
    assert length > 0

    if dn:
        # get dn pw policy
        if not _pw_length_cache.get(dn):
            try:
                results, policies = policy_result(dn)
                _pw_length_cache[dn] = int(results.get("univentionPWLength", ["8"])[0])
            except Exception:  # nosec # TODO: replace with specific exeptions
                pass
        length = _pw_length_cache.get(dn, length)

        # get ou pw policy
        ou = "ou=" + dn[dn.find("ou=") + 3 :]
        if not _pw_length_cache.get(ou):
            try:
                results, policies = policy_result(ou)
                _pw_length_cache[ou] = int(results.get("univentionPWLength", ["8"])[0])
            except Exception:  # nosec # TODO: replace with specific exeptions
                pass
        length = _pw_length_cache.get(ou, length)

    pw = []
    specials_allowed = length // 5  # 20% specials in a password is enough
    specials = list(specials) if specials else []
    lowercase = list(string.ascii_lowercase)
    for char in ("i", "l", "o"):
        # remove chars that are easy to mistake for one another
        lowercase.remove(char)
    uppercase = list(string.ascii_uppercase)
    for char in ("I", "L", "O"):
        uppercase.remove(char)
    digits = list(string.digits)
    for char in ("0", "1"):
        digits.remove(char)

    # password will start with a letter (prepended at end of function)
    length -= 1

    # one symbol from each character class, MS requirement:
    # https://technet.microsoft.com/en-us/library/cc786468(v=ws.10).aspx
    if length >= 3:  # nosec
        pw.append(choice(lowercase))
        pw.append(choice(uppercase))
        pw.append(choice(digits))
        length -= 3
    if specials and length and specials_allowed:  # nosec
        pw.append(choice(specials))
        specials_allowed -= 1
        length -= 1

    # fill up with random chars (but not more than 20% specials)
    for _x in range(length):  # nosec
        char = choice(lowercase + uppercase + digits + (specials if specials_allowed else []))
        if char in specials:
            specials_allowed -= 1
        pw.append(char)

    shuffle(pw)
    pw = [choice(lowercase + uppercase)] + pw  # nosec # start with a letter
    return "".join(pw)


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
        int_level = logging.getLevelName(level)
        if not isinstance(int_level, int):
            int_level = 10
    if int_level <= logging.DEBUG:
        return logging.DEBUG
    elif int_level >= logging.CRITICAL:
        return logging.CRITICAL
    else:
        return logging.INFO


def get_stream_handler(level, stream=None, fmt=None, datefmt=None, fmt_cls=None):
    # type: (Union[int, str], Optional[IO], Optional[str], Optional[str], Optional[type]) -> logging.Handler  # noqa: E501
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
    fmt = "%(log_color)s{}".format(
        fmt or CMDLINE_LOG_FORMATS[loglevel_int2str(nearest_known_loglevel(level))]
    )
    datefmt = datefmt or str(LOG_DATETIME_FORMAT)
    formatter_kwargs = {
        "fmt": fmt,
        "datefmt": datefmt,
        "stream": sys.stdout if stream is None else stream,
    }
    fmt_cls = fmt_cls or UCSTTYColoredFormatter
    if issubclass(fmt_cls, colorlog.ColoredFormatter):
        formatter_kwargs["log_colors"] = LOG_COLORS
    formatter = fmt_cls(**formatter_kwargs)
    handler = UniStreamHandler(stream=stream)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def get_file_handler(
    level, filename, fmt=None, datefmt=None, uid=None, gid=None, mode=None, backupCount=10000, when="D"
):
    # type: (Union[int, str], str, Optional[str], Optional[str], Optional[int], Optional[int], Optional[int], Optional[int],Optional[str]) -> logging.Handler  # noqa: E501
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
    :param int backupCount: If backupCount is nonzero, at most backupCount files will be kept.
        When rollover occurs, the oldest one is deleted.
    :param str when: time when log is rotated.
    :return: a handler
    :rtype: logging.Handler
    """
    fmt = fmt or FILE_LOG_FORMATS[loglevel_int2str(nearest_known_loglevel(level))]
    datefmt = datefmt or str(LOG_DATETIME_FORMAT)
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    handler = UniFileHandler(
        filename, when=when, backupCount=backupCount, fuid=uid, fgid=gid, fmode=mode
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def get_logger(
    name,  # type: str
    level="INFO",  # type: Optional[str]
    target=sys.stdout,  # type: Optional[IO]
    handler_kwargs=None,  # type: Optional[Dict[str, Any]]
    formatter_kwargs=None,  # type: Optional[Dict[str, Any]]
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
    if isinstance(target, IOBase) or hasattr(target, "write"):
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
        handler_kwargs = {}
    if not isinstance(formatter_kwargs, dict):
        formatter_kwargs = {}

    if isinstance(target, IOBase) or hasattr(target, "write"):
        handler_defaults = {"cls": UniStreamHandler, "stream": target}
        fmt = "%(log_color)s{}".format(CMDLINE_LOG_FORMATS[level])
        fmt_cls = colorlog.TTYColoredFormatter
    else:
        handler_defaults = {"cls": UniFileHandler, "filename": target, "when": "D", "backupCount": 10000000}
        fmt = FILE_LOG_FORMATS[level]
        fmt_cls = logging.Formatter
    handler_defaults.update(handler_kwargs)
    fmt_kwargs = {"cls": fmt_cls, "fmt": fmt, "datefmt": str(LOG_DATETIME_FORMAT)}
    fmt_kwargs.update(formatter_kwargs)
    if issubclass(fmt_cls, colorlog.ColoredFormatter):
        fmt_kwargs["log_colors"] = LOG_COLORS

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
    _logger.warning('get_logger() is deprecated, use "logging.getLogger(__name__)" instead.')
    return _logger


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
    process = subprocess.Popen(cmd, **kwargs)  # nosec
    stdout, stderr = process.communicate()
    if isinstance(stdout, bytes):
        stdout = stdout.decode("UTF-8")
    if isinstance(stderr, bytes):
        stderr = stderr.decode("UTF-8")
    if log:
        logger = logging.getLogger(__name__)
        if stdout:
            logger.info(stdout)
        if stderr:
            logger.error(stderr)
    if raise_exc and process.returncode:
        raise subprocess.CalledProcessError(
            returncode=process.returncode, cmd=cmd, output=stderr or stdout
        )
    return process.returncode, stdout, stderr


@contextmanager
def stopped_notifier(strict=True):  # type: (Optional[bool]) -> None
    """
    Stops univention-directory-notifier while in a block and starts it in the
    end. Service if stopped/started by systemctl.

    Will not start if ``ucr get notifier/autostart=no`` -- but *will* stop!

    ::

        with stopped_notifier():
            ...

    :param bool strict: raise RuntimeError if stopping fails
    :raises RuntimeError: if stopping failed and ``strict=True``
    """
    service_name = "univention-directory-notifier"
    logger = logging.getLogger(__name__)

    def _run(args):
        returncode, stdout, stderr = exec_cmd(args, log=True)
        return returncode == 0

    logger.info("Stopping %s", service_name)
    if _run(["/bin/systemctl", "stop", service_name]):
        logger.info("%s stopped", service_name)
    else:
        logger.error("Failed to stop %s...", service_name)
        if strict:
            raise RuntimeError(
                "Failed to stop %s, but this seems to be very important (strict=True was specified)"
                % service_name
            )
        else:
            logger.warning("In the end, will try to start it nonetheless")
    try:
        yield
    finally:
        logger.info("Starting %s", service_name)
        command = ["/bin/systemctl", "start", service_name]
        if _run(command):
            logger.info("%s started", service_name)
        else:
            logger.error(
                'Failed to start %s... Bad news! Better run "%s" manually!',
                service_name,
                " ".join(command),
            )  # correct: shlex... unnecessary


def _write_logging_config(path=LOGGING_CONFIG_PATH):  # type: (Optional[str]) -> None
    with open(path, "w") as fp:
        ruamel.yaml.dump(
            {
                "date": str(LOG_DATETIME_FORMAT),
                "cmdline": collections.OrderedDict(CMDLINE_LOG_FORMATS),
                "colors": collections.OrderedDict(LOG_COLORS),
                "file": collections.OrderedDict(FILE_LOG_FORMATS),
            },
            fp,
            ruamel.yaml.RoundTripDumper,
            indent=4,
        )


def get_package_version(package_name):  # type: (str) -> str
    """
    Retrieve the version of the Debian package `package_name` from the
    Debian package cache.

    :param str package_name: name of Debian package
    :return: version of Debian package, if installed
    :rtype: str
    :raises NotInstalled: if the package is not installed
    :raises UnknownPackage: if the package is unknown
    """
    cache = apt.cache.Cache()
    try:
        package = cache[package_name]
    except KeyError:
        raise UnknownPackage("Debian package {!r} not in package cache.".format(package_name))
    if not package:
        raise NotInstalled("Debian package {!r} ist not installed.".format(package_name))
    return package.installed.version


def add_or_remove_ucrv_value(ucrv, action, value, delimiter):
    """
    Adds or removes a value to a ucrv. Delimiter splits the value of the existing ucr.

    This code was refactored from ucs-school-lib/modify_ucr_list, so that it could also
    be used in the school_creation listener. Bcause the method is also called from a cli
    script it returns 0.
    """
    if action == "remove" and ucrv not in ucr.keys():
        return 0
    cur_val = ucr.get(ucrv, "")
    cur_val_list = [v for v in cur_val.split(delimiter) if v]
    if action == "add":
        if value not in cur_val_list:
            cur_val_list.append(value)
    elif action == "remove":
        try:
            cur_val_list.remove(value)
        except ValueError:
            return 0

    handler_set(["{}={}".format(ucrv, delimiter.join(cur_val_list))])
    return 0
