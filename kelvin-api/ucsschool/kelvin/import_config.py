# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2019 Univention GmbH
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
Diverse helper functions.
"""

import logging
import pprint
import sys
from typing import List

from six import reraise as raise_

from ucsschool.importer.configuration import (
    Configuration,
    ReadOnlyDict,
    setup_configuration as _setup_configuration,
)
from ucsschool.importer.exceptions import UcsSchoolImportError
from ucsschool.importer.factory import setup_factory as _setup_factory
from ucsschool.importer.frontend.user_import_cmdline import (
    UserImportCommandLine as _UserImportCommandLine,
)

from .constants import IMPORT_CONFIG_FILE_DEFAULT, IMPORT_CONFIG_FILE_USER

_ucs_school_import_framework_initialized = False
_ucs_school_import_framework_error = None
logger = logging.getLogger(__name__)


class InitialisationError(Exception):
    pass


class KelvinUserImportCommandLine(_UserImportCommandLine):
    @property
    def configuration_files(self) -> List[str]:
        res = super(KelvinUserImportCommandLine, self).configuration_files
        res.append(str(IMPORT_CONFIG_FILE_DEFAULT))
        if IMPORT_CONFIG_FILE_USER.is_file():
            res.append(str(IMPORT_CONFIG_FILE_USER))
        return res


def init_ucs_school_import_framework(**config_kwargs) -> ReadOnlyDict:
    global _ucs_school_import_framework_initialized, _ucs_school_import_framework_error

    if _ucs_school_import_framework_initialized:
        return Configuration()
    if _ucs_school_import_framework_error:
        # prevent "Changing the configuration is not allowed." error if we
        # return here after raising an InitialisationError
        raise _ucs_school_import_framework_error

    _config_args = {}
    _config_args.update(config_kwargs)
    _ui = KelvinUserImportCommandLine()
    _config_files = _ui.configuration_files
    try:
        config = _setup_configuration(_config_files, **_config_args)
        if "mapped_udm_properties" not in config.get("configuration_checks", []):
            raise UcsSchoolImportError(
                'Missing "mapped_udm_properties" in configuration checks, e.g.: '
                '{.., "configuration_checks": ["defaults", "mapped_udm_properties", '
                '"class_overwrites"], ..}'
            )
        if "class_overwrites" not in config.get("configuration_checks", []):
            raise UcsSchoolImportError(
                'Missing "class_overwrites" in configuration checks, e.g.: '
                '{.., "configuration_checks": ["defaults", "mapped_udm_properties", '
                '"class_overwrites"], ..}'
            )
        # no need to call _ui.setup_logging(), because we configure logger and
        # handlers for 'ucsschool.*' and 'univention.*' in
        # ucsschool.kelvin.main.setup_logging()
        _setup_factory(config["factory"])  # noqa
    except UcsSchoolImportError as exc:
        logger.exception("Error initializing UCS@school import framework: %s", exc)
        etype, exc, etraceback = sys.exc_info()
        _ucs_school_import_framework_error = InitialisationError(str(exc))
        raise_(etype, exc, etraceback)
    logger.info("------ UCS@school import tool configured ------")
    logger.info("Used configuration files: %s.", config.conffiles)
    logger.info("Using command line arguments: %r", _config_args)
    logger.info("Configuration is:\n%s", pprint.pformat(config))
    _ucs_school_import_framework_initialized = True
    return config


def get_import_config() -> ReadOnlyDict:
    if _ucs_school_import_framework_initialized:
        return Configuration()
    else:
        return init_ucs_school_import_framework()
