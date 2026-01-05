# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2024-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

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
        "$class_level": re.compile(r"^0(?P<class_level>\d)/[1,2]$"),
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
