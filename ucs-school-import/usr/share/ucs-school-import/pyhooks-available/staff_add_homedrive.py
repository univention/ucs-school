#!/usr/bin/python3
#
# SPDX-FileCopyrightText: 2020-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from ucsschool.importer.utils.user_pyhook import UserPyHook
from ucsschool.lib.models.user import Staff


class UserStaffPyHook(UserPyHook):
    priority = {
        "pre_create": 1000,
        "post_create": None,
        "pre_modify": 1000,
        "post_modify": None,
        "pre_remove": None,
        "post_remove": None,
    }

    def pre_create(self, user):
        if isinstance(user, Staff):
            user.udm_properties["sambahome"] = super(Staff, user).get_samba_home_path(self.lo)
            user.udm_properties["profilepath"] = super(Staff, user).get_profile_path(self.lo)
            user.udm_properties["scriptpath"] = super(Staff, user).get_samba_netlogon_script_path()
            user.udm_properties["homedrive"] = super(Staff, user).get_samba_home_drive()

    pre_modify = pre_create  # this is for the case of a school change
