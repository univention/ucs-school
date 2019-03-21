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
#   (ln -s /var/lib/ucs-school-import/configs/example.json ~/.import_shell_config)
# * store command line arguments in a JSON file in ~/.import_shell_args
#

"""
Module to ease interactive use of import system.
"""

from __future__ import absolute_import
import json
import logging
import os.path
import pprint

from ..configuration import setup_configuration as _setup_configuration
from ..factory import setup_factory as _setup_factory
from ..models.import_user import ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff, ImportUser
from .ldap_connection import (
	get_admin_connection as _get_admin_connection,
	get_machine_connection as _get_machine_connection,
	get_unprivileged_connection as _get_unprivileged_connection)
from ..exceptions import UcsSchoolImportFatalError as _UcsSchoolImportFatalError
from ..frontend.user_import_cmdline import UserImportCommandLine as _UserImportCommandLine
from ucsschool.lib.models.utils import get_stream_handler as _get_stream_handler, UniStreamHandler as _UniStreamHandler
from ucsschool.lib.models import *  # noqa

assert ImportStaff
assert ImportStudent
assert ImportTeacher
assert ImportTeachersAndStaff
assert ImportUser

_config_args = {
	"dry_run": False,
	"source_uid": "TestDB",
	"verbose": True
}
try:
	with open(os.path.expanduser("~/.import_shell_args"), "rb") as fp:
		_config_args.update(json.load(fp))
except IOError as exc:
	pass

logger = logging.getLogger('ucsschool')
logger.setLevel(logging.DEBUG)
if not any(isinstance(handler, _UniStreamHandler) for handler in logger.handlers):
	logger.addHandler(_get_stream_handler('DEBUG'))

_ui = _UserImportCommandLine()
_config_files = _ui.configuration_files
if os.path.exists(os.path.expanduser("~/.import_shell_config")):
	_config_files.append(os.path.expanduser("~/.import_shell_config"))

config = _setup_configuration(_config_files, **_config_args)
_ui.setup_logging(config["verbose"], config["logfile"])
factory = _setup_factory(config["factory"])
try:
	lo, _po = _get_admin_connection()
except _UcsSchoolImportFatalError:
	try:
		lo, _po = _get_machine_connection()
	except _UcsSchoolImportFatalError:
		lo, _po = _get_unprivileged_connection()

logger.info("------ UCS@school import tool configured ------")
logger.info("Used configuration files: %s.", config.conffiles)
logger.info("Using command line arguments: %r", _config_args)
logger.info("Configuration is:\n%s", pprint.pformat(config))
