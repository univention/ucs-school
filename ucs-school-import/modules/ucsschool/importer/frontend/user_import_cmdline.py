#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""UCS@school new import tool cmdline frontend."""

from typing import List  # noqa: F401

from .cmdline import CommandLine


class UserImportCommandLine(CommandLine):
    import_initiator = "commandline"

    @property
    def configuration_files(self):  # type: () -> List[str]
        """
        Add new user import specific configuration files.

        :return: list of filenames
        :rtype: list(str)
        """
        res = super(UserImportCommandLine, self).configuration_files
        res.append("/usr/share/ucs-school-import/configs/user_import_defaults.json")
        res.append("/var/lib/ucs-school-import/configs/user_import.json")
        return res
