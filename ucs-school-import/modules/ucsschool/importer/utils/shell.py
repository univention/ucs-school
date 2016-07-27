# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Module to ease interactive use of import system.
"""
# Copyright 2016 Univention GmbH
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

#
# This module initializes the ucsschool-import system and loads useful
# classes to make working in an interactive Python shell easier.
# It is NOT intended for production use!
# To use the module simply import its content by running in a Python shell:
#
# >>> from ucsschool.importer.utils.shell import *
#
# Two ways exist to configure the system additionally to the default
# configuration (same as with the import script):
# * create (or symlink to) a JSON configuration file: ~/.import_shell_config
# * store command line arguments in a JSON file in ~/.import_shell_args
#

import json
import os.path
import pprint

from ucsschool.importer.configuration import setup_configuration as _setup_configuration
from ucsschool.importer.factory import setup_factory as _setup_factory
from ucsschool.importer.utils.logging import get_logger as _get_logger
from ucsschool.importer.models.import_user import ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff, ImportUser
from ucsschool.importer.utils.ldap_connection import get_admin_connection as _get_admin_connection
from ucsschool.importer.frontend.user_import_cmdline import UserImportCommandLine as _UserImportCommandLine


_config_args = {
	"dry_run": False,
	"sourceUID": "TestDB",
	"verbose": True
}
try:
	_user_args = json.load(open(os.path.expanduser("~/.import_shell_args"), "rb"))
	_config_args.update(_user_args)
except IOError as exc:
	_user_args = None

_ui = _UserImportCommandLine()
_config_files = _ui.configuration_files
if os.path.exists(os.path.expanduser("~/.import_shell_config")):
	_config_files.append(os.path.expanduser("~/.import_shell_config"))

config = _setup_configuration(_config_files, **_config_args)
_ui.setup_logging(config["verbose"], config["logfile"])
factory = _setup_factory(config["factory"])
logger = _get_logger()
lo, _po = _get_admin_connection()

logger.info("------ UCS@school import tool configured ------")
logger.info("Used configuration files: %s.", config.conffiles)
if _user_args:
	logger.info("Using command line arguments: %r", _user_args)
logger.info("Configuration is:\n%s", pprint.pformat(config))
