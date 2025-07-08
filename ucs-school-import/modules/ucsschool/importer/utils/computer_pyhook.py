# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2016-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class for all Python based Computer hooks."""

from typing import Dict, List, Optional  # noqa: F401

from ucsschool.lib.models.computer import SchoolComputer  # noqa: F401

from .import_pyhook import ImportPyHook


class ComputerPyHook(ImportPyHook):
    """
    Base class for Python based computer import hooks.

    The base class' :py:meth:`__init__()` provides the following attributes:

    * self.lo          # LDAP connection object (2)
    * self.logger      # Python logging instance

    If multiple hook classes are found, hook functions with higher
    priority numbers run before those with lower priorities. None disables
    a function (no need to remove it / comment it out).

    """

    priority = {"pre_create": None, "post_create": None}  # type: Dict[str, Optional[int]]

    def pre_create(self, computer, row):  # type: (SchoolComputer, List[str]) -> None
        """
        Run code before creating a computer.

        * The computer does not exist in LDAP, yet.
        * `computer.dn` is the future DN of the computer,
        * set `priority["pre_create"]` to an `int`, to enable this method

        :param SchoolComputer computer: Computer (subclass of SchoolComputer)
        :param List[str] row: the CSV line (split by the separator)
        :return: None
        """
        pass

    def post_create(self, computer, row):  # type: (SchoolComputer, List[str]) -> None
        """
        Run code after creating a computer.

        * The hook is only executed if adding the computer succeeded.
        * `computer` will be an :py:class:`SchoolComputer`, loaded from LDAP.
        * set `priority["post_create"]` to an int, to enable this method

        :param SchoolComputer computer: Computer (subclass of SchoolComputer)
        :param List[str] row: the CSV line (split by the separator)
        :return: None
        """
        pass
