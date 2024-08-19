#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Univention UCS@school
# Copyright 2019-2024 Univention GmbH
#
# https://www.univention.de/
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
A config hooks that changes the configuration depending on the user role
being imported. Works only with a fixed user role. Includes an additional
configuration file, which must be configured in the main configuration file.

Example::
    {
        "include": {
            "by_role": {
                "student": "/var/lib/ucs-school-import/configs/students.json",
                "teacher": "/var/lib/ucs-school-import/configs/teachers.json"
            }
        }
    }

If the `user_role` configuration value is `student`, the content of
`/var/lib/ucs-school-import/configs/students.json` will be read and applied on
top of the current configuration.

If the `user_role` configuration value is `staff` or `teacher_and_staff`,
nothing will be done.
"""

import json
import pprint
import sys
from typing import TYPE_CHECKING, Any, Dict, List  # noqa: F401

import six

from ucsschool.importer.exceptions import ConfigurationError
from ucsschool.importer.utils.config_pyhook import ConfigPyHook
from ucsschool.lib.roles import supported_roles

if TYPE_CHECKING:
    import ucsschool.importer.configuration.ReadOnlyDict  # noqa: F401


class ExtendConfigByRole(ConfigPyHook):
    """Config hooks that changes the configuration depending on the user role."""

    priority = {
        "post_config_files_read": 10,
    }

    def post_config_files_read(self, config, used_conffiles, used_kwargs):
        # type: (ucsschool.importer.configuration.ReadOnlyDict, List[str], Dict[str, Any]) -> ucsschool.importer.configuration.ReadOnlyDict  # noqa: E501
        """
        Hook that runs after reading the configuration files `used_conffiles`
        and applying the command line arguments `used_kwargs`. Resulting
        configuration is `config`, which can be manipulated and must be
        returned.

        :param ReadOnlyDict config: configuration that will be used by the
        import if not modified here, not yet read-only.
        :param list used_conffiles: configuration files read and applied
        :param dict used_kwargs: command line options read and applied
        :return: config dict
        :rtype: ReadOnlyDict
        """
        if not self.preconditions_met(config, used_conffiles, used_kwargs):
            return config

        user_role = config["user_role"]
        include_file = config["include"]["by_role"][user_role]
        self.logger.debug("Reading %r...", include_file)
        try:
            with open(include_file) as fp:
                include_config = json.load(fp)
        except (IOError, ValueError) as exc:
            self.logger.exception("Reading include file %r: %s", include_file, exc)
            six.reraise(ConfigurationError, ConfigurationError(str(exc)), sys.exc_info()[2])
        self.logger.info("Updating configuration with:\n%s", pprint.pformat(include_config))
        config.update(include_config)
        return config

    def preconditions_met(self, config, used_conffiles, used_kwargs):
        # type: (ucsschool.importer.configuration.ReadOnlyDict, List[str], Dict[str, Any]) -> bool
        """
        Verify preconditions for using the hook.

        :param ReadOnlyDict config: configuration that will be used by the
        import if not modified here, not yet read-only.
        :param list used_conffiles: configuration files read and applied
        :param dict used_kwargs: command line options read and applied
        :return: whether the hook can run
        :rtype: bool
        """
        if "by_role" not in config.get("include", {}):
            self.logger.error('Exiting hook: missing section "include:by_role".')
            return False
        if config.get("user_role") is None:
            self.logger.error('Exiting hook: hook requires a fixed role but "user_role" is None.')
            return False
        if config["user_role"] not in list(supported_roles) + ["student", "teacher_and_staff"]:
            self.logger.error("Exiting hook: unknown role %r.", config["user_role"])
            return False
        if config["user_role"] not in config["include"]["by_role"]:
            self.logger.warning(
                'No value for role %r in section "include:by_role", ignoring.', config["user_role"]
            )
            return False
        return True
