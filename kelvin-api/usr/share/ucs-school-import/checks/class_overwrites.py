# -*- coding: utf-8 -*-
#
# Univention UCS@school
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
import importlib
import inspect

from ucsschool.importer.exceptions import InitialisationError
from ucsschool.importer.utils.configuration_checks import ConfigurationChecks


class ClassOverwriteConfigurationCheck(ConfigurationChecks):
    def test_01_no_overwrite(self):
        classes = self.config.get("classes", {})
        for k, v in classes.items():
            self.logger.info(f"Checking class override for {k}: {v}")
            module_name, class_name = v.rsplit(".", 1)
            try:
                imported_module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                raise InitialisationError(
                    f"Overwriting the class for {k} is not possible, because the module {module_name} "
                    f"could not be found. You might deactivating the override for Kelvin by setting the "
                    f"class in the kelvin.json to ''."
                )
            if not inspect.isclass(getattr(imported_module, class_name)):
                raise InitialisationError(
                    f"Overwriting the class for {k} is not possible, because the class {class_name} "
                    f"could not be found in module {module_name}. You might deactivating the override "
                    f"for Kelvin by setting the class in the kelvin.json to ''."
                )
