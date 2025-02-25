# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2024 Univention GmbH
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

import re

from ucsschool.importer.models.import_user import ImportStudent
from ucsschool.importer.utils.user_pyhook import UserPyHook


class LUSDClassLevel(UserPyHook):  # type: ignore[misc]
    """
    This hook transforms a value from the input data in the attribute ``LUSD_CLASS_LEVEL_ATTRIBUTE``
    and sets the result as the udm property ``UDM_CLASS_LEVEL_ATTRIBUTE``.
    """

    supports_dry_run = True

    priority = {
        "pre_create": 1,
        "pre_modify": 1,
    }

    """
    Specifies the name of the class level attribute in the LUSD import input data.
    """
    LUSD_CLASS_LEVEL_ATTRIBUTE = "stufeSemester"

    """
    Specifies the name of the udm attribute to write the transformed value into.
    """
    UDM_CLASS_LEVEL_ATTRIBUTE = "class_level"

    """
    This dictionary specifies the transformation rules.
    The hook iterates over each regular expression.
    If one matches, the key is used as the value for the class level attribute.
    If the key starts with ``$``, the hook expects the regular expression to contain
    a named group of the same name without the ``$`` symbol.
    Its value is used for the class level attribute.
    """
    REGEX_PATTERNS = {
        "$class_level": re.compile(r"^0(?P<class_level>[0-9])/[1,2]$"),
        "10": re.compile(r"^10/[1,2]$"),
        "11": re.compile(r"^E[1,2]$"),
        "12": re.compile(r"^Q[1,2]$"),
        "13": re.compile(r"^Q[3,4]$"),
        "": re.compile(r"^-/[1,2]$"),
    }

    def pre_create(self, user):  # type: ignore[no-untyped-def]
        if not isinstance(user, ImportStudent):
            return
        self.logger.info("Calculating class level for %s", user)
        class_level = self.calculate_class_level(user)  # type: ignore[no-untyped-call]
        if class_level is not None:
            self.logger.info("Class level calculated for %s: %s", user, class_level)
            user.udm_properties[LUSDClassLevel.UDM_CLASS_LEVEL_ATTRIBUTE] = class_level
        else:
            self.logger.warning("No class level could be calculated for %s", user)

    pre_modify = pre_create

    def calculate_class_level(self, user):  # type: ignore[no-untyped-def]
        if isinstance(user.input_data, dict):
            raw_data = user.input_data.get(LUSDClassLevel.LUSD_CLASS_LEVEL_ATTRIBUTE, "")
        else:
            raw_data = ""  # happens on move to limbo ou
        if not isinstance(raw_data, str):
            raw_data = str(raw_data)
        class_level = None
        for value, pattern in self.REGEX_PATTERNS.items():
            match = pattern.match(raw_data)
            if match is None:
                continue
            if value.startswith("$"):
                class_level = match.groupdict().get(value[1:], None)
                if class_level is not None:
                    break
            else:
                class_level = value
                break
        return class_level
