#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2021 Univention GmbH
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
Base class for UCS@school import tool cmdline frontends.
"""
import grp
import logging
import os
import pprint
import pwd
import sys
from datetime import datetime

import six

from ucsschool.lib.models.utils import (
    UniFileHandler,
    UniStreamHandler,
    get_file_handler,
    get_stream_handler,
)

from ..configuration import Configuration, setup_configuration
from ..exceptions import InitialisationError
from ..factory import setup_factory
from .parse_user_import_cmdline import ParseUserImportCmdline

try:
    from typing import List
except ImportError:
    pass

CENTRAL_LOG_DIR = "/var/log/univention/ucs-school-import"
LAST_FAIL_LOG_SYMLINK = os.path.join(CENTRAL_LOG_DIR, "LAST-FAIL")
LAST_LOG_DEBUG_SYMLINK = os.path.join(CENTRAL_LOG_DIR, "LAST-LOG-DEBUG")
LAST_LOG_ERROR_SYMLINK = os.path.join(CENTRAL_LOG_DIR, "LAST-LOG-ERROR")


class CommandLine(object):
    import_initiator = "unknown"

    def __init__(self):
        self.logger = None  # type: logging.Logger
        self.args = None
        self.config = None
        self.factory = None
        self.errors = list()
        self.user_import_summary_str = ""
        self._error_log_handler = None

    def parse_cmdline(self):
        parser = ParseUserImportCmdline()
        self.args = parser.parse_cmdline()
        return self.args

    def setup_logging(self, stdout=False, filename=None, uid=None, gid=None, mode=None):
        # we're called twice:
        # once after parsing the cmdline, if no `-v` was given, INFO is used,
        # then again after reading the configuration files, the loglevel may be different now
        self.logger = logging.getLogger("ucsschool")
        self.logger.setLevel(logging.DEBUG)
        # update existing stdout loggers, add one if none exist
        stream_handlers = [
            _handler for _handler in self.logger.handlers if isinstance(_handler, UniStreamHandler)
        ]
        for handler in stream_handlers:
            handler.setLevel(logging.DEBUG if stdout else logging.INFO)
        if not stream_handlers:
            self.logger.addHandler(get_stream_handler("DEBUG" if stdout else "INFO"))
        # add debug and error file handlers if non exist (and a filename was given)
        file_handlers = [
            _handler for _handler in self.logger.handlers if isinstance(_handler, UniFileHandler)
        ]
        if filename and not file_handlers:
            self.logger.addHandler(get_file_handler("DEBUG", filename, uid=uid, gid=gid, mode=mode))
            self.create_symlink(filename, LAST_LOG_DEBUG_SYMLINK)
            log_dir = os.path.dirname(filename)
            error_log_path = os.path.join(log_dir, "ucs-school-import-error.log")
            # set INFO level now, so the configuration will also end up in the logfile
            # will be raised to ERROR directly after logging the configuration
            self._error_log_handler = get_file_handler(
                "INFO", error_log_path, uid=uid, gid=gid, mode=mode
            )
            self.logger.addHandler(self._error_log_handler)
            self.create_symlink(error_log_path, LAST_LOG_ERROR_SYMLINK)
        return self.logger

    def setup_config(self):
        configs = self.configuration_files
        if self.args.conffile and self.args.conffile not in configs:
            configs.append(self.args.conffile)
        try:
            self.config = setup_configuration(configs, **self.args.settings)
        except InitialisationError as exc:
            self.logger.exception("Error setting up or checking the configuration: %s", exc)
            self.logger.error("Used configuration files: %s.", configs)
            self.logger.error("Using command line arguments: %r", self.args.settings)
            try:
                # if it was a config check error, the config singleton already exists
                config = Configuration()
                self.logger.error("Configuration is:\n%s", pprint.pformat(config))
            except InitialisationError:
                pass
            raise
        return self.config

    @property
    def configuration_files(self):  # type: () -> List[str]
        """
        IMPLEMENTME to add module specific configuration files:
        res = super(YouClass, self).configuration_files
        res.append("/your/config.json")
        return res

        :return: list of filenames
        :rtype: list(str)
        """
        return [
            "/usr/share/ucs-school-import/configs/global_defaults.json",
            "/var/lib/ucs-school-import/configs/global.json",
        ]

    def do_import(self):
        importer = self.factory.make_mass_importer(self.config["dry_run"])

        self.logger.info("------ Starting mass import... ------")
        try:
            importer.mass_import()
        except Exception:  # pylint: disable=broad-except
            logfile = os.path.realpath(LAST_LOG_DEBUG_SYMLINK)
            self.create_symlink(logfile, LAST_FAIL_LOG_SYMLINK)
            if logfile.startswith("/var/lib/ucs-school-import"):
                job_id = os.path.split(os.path.dirname(logfile))[-1]
                job_id = "job_{:0>4}".format(job_id)
            else:
                job_id = "cmdline"
            link = os.path.join(
                CENTRAL_LOG_DIR, "FAIL_{:%Y-%m-%d_%H:%M:%S}_{}".format(datetime.now(), job_id)
            )
            self.create_symlink(logfile, link)
            etype, exc, etraceback = sys.exc_info()
            six.reraise(etype, exc, etraceback)
        finally:
            self.errors = importer.errors
            self.user_import_summary_str = importer.user_import_stats_str
            # log result to error log (was logged before at INFO level)
            if self.user_import_summary_str:
                log_msgs = (
                    "------ User import statistics ------\n"
                    "{}\n"
                    "------ End of user import statistics ------".format(self.user_import_summary_str)
                )
                record = self.logger.makeRecord(
                    self.logger.name,
                    logging.INFO,
                    "ucs-school-import-error.log",
                    0,
                    log_msgs,
                    (),
                    None,
                    "user_import_stats_str",
                    None,
                )
                self._error_log_handler.handle(record)
            self.logger.info("------ Mass import finished. ------")

    def prepare_import(self):
        self.parse_cmdline()
        # early logging configured by cmdline
        self.setup_logging(self.args.verbose, self.args.logfile)
        self.logger.info("Loading UCS@school import configuration...")
        self.setup_config()
        # logging configured by config file
        self.setup_logging(self.config["verbose"], self.config["logfile"])
        self.logger.info("------ UCS@school import tool starting ------")
        self.logger.info(
            "Import started by %s (class %r).", self.import_initiator, self.__class__.__name__
        )

        with open(self.config["input"]["filename"]) as fin:
            line = fin.readline()
            self.logger.info("First line of %r:\n%r", self.config["input"]["filename"], line)

        self.logger.info("------ UCS@school import tool configured ------")
        self.logger.info("Used configuration files: %s.", self.config.conffiles)
        self.logger.info("Using command line arguments: %r", self.args.settings)
        self.logger.info("Configuration is:\n%s", pprint.pformat(self.config))
        self._error_log_handler.setLevel("ERROR")

        self.factory = setup_factory(self.config["factory"])

    def create_symlink(self, source, link_name):  # type: (str, str) -> None
        """
        Create a symlink file `link_name` that points to a file at `source`.
        If `link_name` exists and is a symlink, it will first be deleted.
        This is a wrapper around `os.symlink(source, link_name)`.

        :param str source: the file that the symlink should point to
        :param str link_name: the symlink file to create
        :return: None
        :rtype: None
        """
        source = os.path.abspath(os.path.realpath(source))
        self.logger.debug("Creating symlink from %r to %r.", source, link_name)
        parent_dir = os.path.dirname(link_name)
        if not os.path.isdir(parent_dir):
            self.logger.debug("Creating directory %r.", parent_dir)
            os.mkdir(parent_dir, 0o750)
            uid = pwd.getpwnam("uas-import").pw_uid
            gid = grp.getgrnam("uas-import").gr_gid
            os.chown(parent_dir, uid, gid)
        if os.path.islink(link_name):
            os.remove(link_name)
        os.symlink(source, link_name)

    async def main(self):
        try:
            self.prepare_import()
        except InitialisationError as exc:
            msg = "InitialisationError: {}".format(exc)
            self.logger.exception(msg)
            return 1
        try:
            await self.do_import()

            if self.errors:
                # at least one non-fatal error
                msg = "Import finished normally but with errors."
                self.logger.warning(msg)
                return 2
        except Exception as exc:  # pylint: disable=broad-except
            return 1
