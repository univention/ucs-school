#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2018-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class for all Python based Result-Pyhooks."""

from typing import TYPE_CHECKING

from .import_pyhook import ImportPyHook

if TYPE_CHECKING:
    from ..mass_import.user_import import UserImportData  # noqa: F401


class ResultPyHook(ImportPyHook):
    """
    Hook that is called after import has finished.

    The base class' :py:meth:`__init__()` provides the following attributes:

    * self.dry_run     # whether hook is executed during a dry-run (1)
    * self.lo          # LDAP connection object (2)
    * self.logger      # Python logging instance

    If multiple hook classes are found, hook functions with higher
    priority numbers run before those with lower priorities. None disables
    a function (no need to remove it / comment it out).

    (1) Hooks are only executed during dry-runs, if the class attribute
    :py:attr:`supports_dry_run` is set to `True` (default is `False`). Hooks
    with `supports_dry_run == True` must not modify LDAP objects.
    Therefore the LDAP connection object self.lo will be a read-only connection
    during a dry-run.
    (2) Read-write cn=admin connection in a real run, read-only cn=admin
    connection during a dry-run.
    """

    priority = {
        "user_result": None,
    }

    def user_result(self, user_import_data):  # type: (UserImportData) -> None
        """
        Run code after user import has finished. Relevant data from the
        UserImport class is passed to this hook, so result summaries etc are
        possible.

        :param UserImportData user_import_data: relevant data from the UserImport class
        :return: None
        """
        return
