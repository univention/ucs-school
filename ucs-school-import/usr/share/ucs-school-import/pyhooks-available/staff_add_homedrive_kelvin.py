#!/usr/bin/python3
#
# SPDX-FileCopyrightText: 2020-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

##############################################################################
#
# This hook requires the follopwing UCR variables to be set inside the Kelvin
# API Docker container:
#
#   ucsschool/import/set/netlogon/script/path
#   ucsschool/import/set/homedrive
#   ucsschool/import/set/sambahome
#   ucsschool/singlemaster
#   ucsschool/import/set/serverprofile/path
#
# This will be done automatically upon installation of the Kelvin API app.
# When the variables are changed in the Primary Directory Node, the variables have to be
# updated in the Kelvin API Docker container aswel. To do so rerun the Kelvin
# apps join script:
#    univention-run-join-scripts --run-scripts --force 50ucsschool-kelvin-rest-api.inst
#
###############################################################################

from ucsschool.importer.models.import_user import ImportUser
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

    async def pre_create(self, user: ImportUser) -> None:  # noqa: E999
        if isinstance(user, Staff):
            user.udm_properties["sambahome"] = await super(Staff, user).get_samba_home_path(self.lo)
            user.udm_properties["profilepath"] = await super(Staff, user).get_profile_path(self.lo)
            user.udm_properties["scriptpath"] = super(Staff, user).get_samba_netlogon_script_path()
            user.udm_properties["homedrive"] = super(Staff, user).get_samba_home_drive()

    pre_modify = pre_create  # this is for the case of a school change
