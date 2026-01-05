#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""UCS@school UDM-hook to prevent invalid combinations of user options"""

import univention.admin.localization
import univention.admin.modules
import univention.admin.uexceptions
from univention.admin.hook import simpleHook

translation = univention.admin.localization.translation("univention-admin-hooks-ucsschool_user_options")
_ = translation.translate


option_blacklist = {
    "ucsschoolAdministrator": {"ucsschoolExam", "ucsschoolStudent"},
    "ucsschoolExam": {"ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"},
    "ucsschoolStaff": {"ucsschoolExam", "ucsschoolStudent"},
    "ucsschoolStudent": {"ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"},
    "ucsschoolTeacher": {"ucsschoolExam", "ucsschoolStudent"},
    "ucsschoolLegalGuardian": {"ucsschoolExam"},
}


class UcsschoolUserOptions(simpleHook):
    type = "UcsschoolUserOptions"

    @staticmethod
    def check_options(module):
        def _option_name(option):
            return univention.admin.modules.get(module.module).options[option].short_description

        for option, invalid_options in option_blacklist.items():
            if option not in module.options:
                continue
            if invalid_options & set(module.options):
                raise univention.admin.uexceptions.invalidOptions(
                    _("%(option)s cannot be activated together with %(illegals)s.")
                    % {
                        "option": _option_name(option),
                        "illegals": ", ".join(
                            map(_option_name, (invalid_options & set(module.options)))
                        ),
                    }
                )

    def hook_ldap_pre_create(self, module):
        self.check_options(module)

    def hook_ldap_pre_modify(self, module):
        self.check_options(module)
