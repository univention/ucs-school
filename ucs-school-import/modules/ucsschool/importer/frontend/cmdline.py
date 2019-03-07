#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention UCS@school
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
Base class for UCS@school import tool cmdline frontends.
"""

import pprint

from ucsschool.importer.utils.logging import get_logger, make_stdout_verbose, add_file_handler, move_our_handlers_to_lib_logger
from ucsschool.importer.frontend.parse_user_import_cmdline import ParseUserImportCmdline
from ucsschool.importer.configuration import Configuration, setup_configuration
from ucsschool.importer.factory import setup_factory
from ucsschool.importer.exceptions import InitialisationError, TooManyErrors, UcsSchoolImportFatalError

try:
	from typing import List
except ImportError:
	pass


class CommandLine(object):

	def __init__(self):
		self.logger = get_logger()
		self.args = None
		self.config = None
		self.factory = None
		self.errors = list()
		self.user_import_summary_str = ''

	def parse_cmdline(self):
		parser = ParseUserImportCmdline()
		self.args = parser.parse_cmdline()
		return self.args

	def setup_logging(self, stdout=False, filename=None, uid=None, gid=None, mode=None):
		if stdout:
			make_stdout_verbose()
		if filename:
			add_file_handler(filename, uid, gid, mode)
		# make ucsschool.lib use our logging
		move_our_handlers_to_lib_logger()

	def setup_config(self):
		configs = self.configuration_files
		if self.args.conffile and self.args.conffile not in configs:
			configs.append(self.args.conffile)
		try:
			self.config = setup_configuration(configs, **self.args.settings)
		except InitialisationError as exc:
			self.logger.exception('Error setting up or checking the configuration: %s', exc)
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
			"/var/lib/ucs-school-import/configs/global.json"
		]

	def do_import(self):
		importer = self.factory.make_mass_importer(self.config["dry_run"])

		self.logger.info("------ Starting mass import... ------")
		try:
			importer.mass_import()
		finally:
			self.errors = importer.errors
			self.user_import_summary_str = importer.user_import_stats_str
			self.logger.info("------ Mass import finished. ------")

	def prepare_import(self):
		self.parse_cmdline()
		# early logging configured by cmdline
		self.setup_logging(self.args.verbose, self.args.logfile)

		self.logger.info("------ UCS@school import tool starting ------")

		self.setup_config()
		# logging configured by config file
		self.setup_logging(self.config["verbose"], self.config["logfile"])

		self.logger.info("------ UCS@school import tool configured ------")
		self.logger.info("Used configuration files: %s.", self.config.conffiles)
		self.logger.info("Using command line arguments: %r", self.args.settings)
		self.logger.info("Configuration is:\n%s", pprint.pformat(self.config))

		self.factory = setup_factory(self.config["factory"])

	def main(self):
		try:
			self.prepare_import()
		except InitialisationError as exc:
			msg = "InitialisationError: {}".format(exc)
			self.logger.exception(msg)
			return 1
		try:
			self.do_import()

			if self.errors:
				# at least one non-fatal error
				msg = 'Import finished normally but with errors.'
				self.logger.warn(msg)
				return 2
		except Exception as exc:
			return 1
