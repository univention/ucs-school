#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2019-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class for all Python based pre-read hooks."""

from typing import TYPE_CHECKING, Any, Optional  # noqa: F401

from ..configuration import Configuration
from .import_pyhook import ImportPyHook

if TYPE_CHECKING:
    import univention.admin.uldap.access  # noqa: F401

    from ..configuration import ReadOnlyDict  # noqa: F401


class PreReadPyHook(ImportPyHook):
    """
    Hook that is called before starting to read the input file.

    The base class' :py:meth:`__init__()` provides the following attributes:

    * self.dry_run     # whether hook is executed during a dry-run (1)
    * self.lo          # LDAP connection object (2)
    * self.logger      # Python logging instance
    * self.config      # read-only import configuration

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
        "pre_read": None,
    }

    def __init__(self, lo=None, dry_run=False, *args, **kwargs):
        # type: (Optional[univention.admin.uldap.access], Optional[bool], *Any, **Any) -> None
        super(PreReadPyHook, self).__init__(lo, dry_run, *args, **kwargs)
        self.config = Configuration()  # type: ReadOnlyDict

    def pre_read(self):  # type: () -> None
        """
        Run code before starting to read the input file.

        :return: None
        """
        return
