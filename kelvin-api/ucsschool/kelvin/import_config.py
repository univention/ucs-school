# -*- coding: utf-8 -*-

# Copyright 2020 Univention GmbH
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
import os.path
import pprint
import sys
from pathlib import Path
from typing import Any, Dict, List

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

from .constants import (
    IMPORT_CONFIG_FILE_DEFAULT,
    IMPORT_CONFIG_FILE_USER,
    KELVIN_IMPORTUSER_HOOKS_PATH,
)

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

    # Detect and setup developer env. Changes _config_files and _config_args!
    setup_dev_configs(_config_files, _config_args)

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
        logger.exception(
            "Error initializing UCS@school import framework (inside Kelvin REST API): %s",
            exc,
        )
        etype, exc, etraceback = sys.exc_info()
        _ucs_school_import_framework_error = InitialisationError(str(exc))
        raise_(etype, exc, etraceback)
    logger.info(
        "------ UCS@school import framework (inside Kelvin REST API) configured ------"
    )
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


def setup_dev_configs(config_files: List[str], config_args: Dict[str, Any]) -> None:
    """
    Detect and setup developer environment

    * only works if CWD is in git repo .../ucsschool[features/kelvin]/kelvin-api
    * changes config_files and config_args !
    """
    if Path("/usr/share/ucs-school-import").exists():
        return
    local_share_path = Path.cwd().absolute().parent / "ucs-school-import"
    if not local_share_path.exists():
        logger.warning(
            "*** Directory 'ucs-school-import' not found below CWD. Cannot setup dev env."
        )
        return

    import ucsschool.importer.utils.configuration_checks  # isort:skip

    local_var_path = Path.cwd().absolute() / "dev"
    Path(local_var_path).mkdir(exist_ok=True, parents=True)
    logger.warning(
        "*** Using '%s' instead of '/usr/share/ucs-school-import'.", local_share_path,
    )
    logger.warning(
        "*** Using '%s' as root of paths below '/var/' etc.", local_var_path,
    )
    # Kelvin hooks
    local_kelvin_hooks_path = local_var_path / str(KELVIN_IMPORTUSER_HOOKS_PATH).lstrip(
        "/"
    )
    logger.warning(
        "*** Setting config 'hooks_dir_pyhook' to '%s'.", local_kelvin_hooks_path,
    )
    Path(local_kelvin_hooks_path).mkdir(exist_ok=True, parents=True)
    config_args["hooks_dir_pyhook"] = local_kelvin_hooks_path
    # Kelvin config checks
    local_config_checks_dir = local_var_path / str(
        ucsschool.importer.utils.configuration_checks.CONFIG_CHECKS_CODE_DIR
    ).lstrip("/")
    logger.warning(
        "*** Setting config checks code dir to '%s'.", local_config_checks_dir
    )
    Path(local_config_checks_dir).mkdir(exist_ok=True, parents=True)
    ucsschool.importer.utils.configuration_checks.CONFIG_CHECKS_CODE_DIR = (
        local_config_checks_dir
    )
    # Import configuration paths
    new_paths = []
    for path_s in config_files:
        if path_s.endswith("kelvin_defaults.json"):
            local_kelvin_path = str(Path.cwd().absolute())
            new_path = os.path.join(local_kelvin_path, path_s.lstrip("/"))
            logger.warning("*** %r -> %r", path_s, new_path)
            new_paths.append(new_path)
        elif path_s.startswith("/usr/share/ucs-school-import"):
            new_path = os.path.join(local_share_path, path_s.lstrip("/"))
            logger.warning("*** %r -> %r", path_s, new_path)
            new_paths.append(new_path)
        elif path_s.startswith("/var/lib/ucs-school-import/configs"):
            conf_dir = local_var_path / "var/lib/ucs-school-import/configs"
            conf_dir.mkdir(exist_ok=True, parents=True)
            new_path = conf_dir / Path(path_s).name
            logger.warning("*** %r -> '%s'", path_s, new_path)
            if not new_path.exists():
                new_path.write_text("{}")
                logger.warning("*** Created new config file '%s'.", new_path)
            new_paths.append(str(new_path))
        else:
            logger.warning("*** Keeping unknown path %r.", path_s)
            new_paths.append(path_s)
    logger.warning("*** OLD config files: %r", config_files)
    config_files.clear()
    config_files.extend(new_paths)
    logger.warning("*** NEW config files: %r", config_files)
