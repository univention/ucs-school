# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2021 Univention GmbH
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
from pathlib import Path
from random import choice, shuffle
from typing import IO, Any, Dict, List, Sequence, Tuple, Union

import colorlog
import lazy_object_proxy
import ruamel.yaml
from pkg_resources import resource_stream
from six import string_types

from univention.config_registry import ConfigRegistry, handler_set

# from univention.lib.policy_result import policy_result
from univention.lib.i18n import Translation

# "global" translation for ucsschool.lib.models
_ = Translation("python-ucs-school").translate


# TODO: get base/univention-policy/python-lib/policy_result.py and static univention-policy-result binary
def policy_result(dn: str) -> Tuple[Dict[str, List[Any]], Dict[str, str]]:
    return {"univentionPWLength": ["8"]}, {"univentionPWLength": "Policy-DN"}


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


def _load_logging_config() -> Dict[str, Dict[str, str]]:
    with resource_stream("ucsschool.lib", "logging.yaml") as fp:
        return ruamel.yaml.load(fp, ruamel.yaml.RoundTripLoader)


def _ucr() -> ConfigRegistry:
    ucr = ConfigRegistry()
    ucr.load()
    return ucr


def env_or_ucr(key: str) -> str:
    try:
        return os.environ[key.replace("/", "_").upper()]
    except KeyError:
        return ucr[key]


_logging_config: Dict[str, Dict[str, str]] = lazy_object_proxy.Proxy(_load_logging_config)
CMDLINE_LOG_FORMATS: Dict[str, str] = lazy_object_proxy.Proxy(lambda: _logging_config["cmdline"])
FILE_LOG_FORMATS: Dict[str, str] = lazy_object_proxy.Proxy(lambda: _logging_config["file"])
LOG_DATETIME_FORMAT: str = lazy_object_proxy.Proxy(lambda: _logging_config["date"])
LOG_COLORS: Dict[str, str] = lazy_object_proxy.Proxy(lambda: _logging_config["colors"])

APP_ID = "ucsschool-kelvin-rest-api"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = APP_BASE_PATH / "conf"
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"
DEFAULT_UCS_SSL_CA_CERT = "/usr/local/share/ca-certificates/ucs.crt"

_handler_cache: Dict[str, logging.Handler] = {}
_pw_length_cache: Dict[str, int] = {}
_udm_kwargs: Dict[str, str] = {}
ucr: ConfigRegistry = lazy_object_proxy.Proxy(_ucr)  # "global" ucr for ucsschool.lib.models
ucr_username_max_length: int = lazy_object_proxy.Proxy(
    lambda: int(ucr.get("ucsschool/username/max_length", 20))
)


def mkdir_p(dir_name: str, user: Union[str, int], group: Union[str, int], mode: int) -> None:
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


def _remove_password_from_log_record(record: logging.LogRecord) -> logging.LogRecord:
    def replace_password(obj, attr):
        ori = getattr(obj, attr)
        if isinstance(ori, collections.abc.Mapping) and isinstance(ori.get("password"), string_types):
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
        filename: str,
        when: str = "h",
        interval: int = 1,
        backupCount: int = 0,
        encoding: str = None,
        delay: bool = False,
        utc: bool = False,
        fuid: int = None,
        fgid: int = None,
        fmode: int = None,
    ) -> None:
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
        stream: IO = None,
        fuid: int = None,
        fgid: int = None,
        fmode: int = None,
    ) -> None:
        """
        `fuid`, `fgid` and `fmode` are here only for similarity of interface
        to UniFileHandler and are ignored.
        """
        super(UniStreamHandler, self).__init__(stream)

    def emit(self, record):
        """remove password from from dicts in args"""
        _remove_password_from_log_record(record)
        super(UniStreamHandler, self).emit(record)


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


def add_stream_logger_to_schoollib(
    level: str = "DEBUG",
    stream: IO = sys.stderr,
    log_format: str = None,
    name: str = None,
) -> logging.Logger:
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


def create_passwd(length: int = 8, dn: str = None, specials: str = "$%&*-+=:.?") -> str:
    assert length > 0

    if dn:
        # get dn pw policy
        if not _pw_length_cache.get(dn):
            try:
                results, policies = policy_result(dn)
                _pw_length_cache[dn] = int(results.get("univentionPWLength", ["8"])[0])
            except Exception:  # nosec # TODO: replace with specific exceptions
                pass
        length = _pw_length_cache.get(dn, length)

        # get ou pw policy
        ou = "ou=" + dn[dn.find("ou=") + 3 :]
        if not _pw_length_cache.get(ou):
            try:
                results, policies = policy_result(ou)
                _pw_length_cache[ou] = int(results.get("univentionPWLength", ["8"])[0])
            except Exception:  # nosec # TODO: replace with specific exceptions
                pass
        length = _pw_length_cache.get(ou, length)

    pw = list()
    specials_allowed = length / 5  # 20% specials in a password is enough
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


def flatten(list_of_lists: List[List[Any]]) -> List[Any]:
    # return [item for sublist in list_of_lists for item in sublist]
    # => does not work well for strings in list
    ret = []
    for sublist in list_of_lists:
        if isinstance(sublist, (list, tuple)):
            ret.extend(flatten(sublist))
        else:
            ret.append(sublist)
    return ret


def loglevel_int2str(level: Union[int, str]) -> str:
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


def get_stream_handler(
    level: Union[int, str],
    stream: IO = None,
    fmt: str = None,
    datefmt: str = None,
    fmt_cls: type = None,
) -> logging.Handler:
    # noqa: E501
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
    fmt = "%(log_color)s{}".format(
        fmt or CMDLINE_LOG_FORMATS[loglevel_int2str(nearest_known_loglevel(level))]
    )
    datefmt = datefmt or str(LOG_DATETIME_FORMAT)
    formatter_kwargs = {"fmt": fmt, "datefmt": datefmt}
    fmt_cls = fmt_cls or UCSTTYColoredFormatter
    if issubclass(fmt_cls, colorlog.ColoredFormatter):
        formatter_kwargs["log_colors"] = LOG_COLORS
    if issubclass(fmt_cls, colorlog.TTYColoredFormatter):
        formatter_kwargs["stream"] = stream
    formatter = fmt_cls(**formatter_kwargs)
    handler = UniStreamHandler(stream=stream)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def get_file_handler(
    level: Union[int, str],
    filename: str,
    fmt: str = None,
    datefmt: str = None,
    uid: int = None,
    gid: int = None,
    mode: int = None,
    backupCount: int = 10000,
    when: str = "D",
) -> logging.Handler:
    # noqa: E501
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


def exec_cmd(
    cmd: Sequence[str], log: bool = False, raise_exc: bool = False, **kwargs: Any
) -> Tuple[int, str, str]:
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
    if isinstance(stderr, bytes):
        stderr = stderr.decode()
    if isinstance(stdout, bytes):
        stdout = stdout.decode()
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
def stopped_notifier(strict: bool = True) -> None:
    try:
        yield
    finally:
        pass


def _write_logging_config(path: str) -> None:
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


def udm_rest_client_cn_admin_kwargs() -> Dict[str, str]:
    global _udm_kwargs
    if not _udm_kwargs:
        host = env_or_ucr("ldap/master")
        with open(CN_ADMIN_PASSWORD_FILE, "r") as fp:
            cn_admin_password = fp.read().strip()
        _udm_kwargs = {
            "username": "cn=admin",
            "password": cn_admin_password,
            "url": f"https://{host}/univention/udm/",
        }
    return _udm_kwargs


def add_or_remove_ucrv_value(ucrv, action, value, delimiter):
    """Adds or removes a value to a ucrv. Delimiter splits the value of the existing ucr.

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
