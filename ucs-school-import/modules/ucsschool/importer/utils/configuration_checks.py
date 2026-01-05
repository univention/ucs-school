#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2018-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Configuration checks.

After the configuration has been read, checks run.

To add your own checks, subclass :py:class:`ConfigurationChecks`, save the
module in ``/usr/share/ucs-school-import/checks`` and add its module name
(without ``.py``) to the list in the configuration key ``configuration_checks``.

Remove ``defaults`` from your ``configuration_checks`` only if you know what you
are doing.

----

Example: Save the following to ``/usr/share/ucs-school-import/checks/mychecks.py``:

>>> from ucsschool.importer.exceptions import InitialisationError
>>> from ucsschool.importer.utils.configuration_checks import ConfigurationChecks
>>>
>>> class MyConfigurationChecks(ConfigurationChecks):
>>> 	def test_nonzero_deactivation_grace(self):
>>> 		if self.config.get('deletion_grace_period', {}).get('deactivation', 0) == 0:
>>> 			raise InitialisationError('deletion_grace_period:deactivation must not be zero.')

Then add a configuration entry to ``/var/lib/ucs-school-import/configs/user_import.json``::

    {
    [..]
        "configuration_checks": ["defaults", "mychecks"]
    }
"""

from __future__ import absolute_import

import inspect
import logging
from operator import itemgetter
from typing import TYPE_CHECKING, List, Type  # noqa: F401

from ucsschool.lib.pyhooks.pyhooks_loader import PyHooksLoader

from ..exceptions import UcsSchoolImportFatalError
from .ldap_connection import get_readonly_connection, get_unprivileged_connection

if TYPE_CHECKING:
    from ..configuration import ReadOnlyDict  # noqa: F401


__all__ = ["ConfigurationChecks"]

CONFIG_CHECKS_CODE_DIR = "/usr/share/ucs-school-import/checks"


class ConfigurationChecks(object):
    """
    Base class for configuration checks.

    Provides the configuration singleton in :py:attr:`self.config`, a
    read-only LDAP connection object in :py:attr:`self.lo` and a logging
    instance in :py:attr:`self.logger`.

    All methods with names starting with ``test_`` will be executed in
    alphanumerical order. Failing tests should raise a
    py:exception:`ucsschool.importer.exceptions.InitialisationError` exception.
    """

    def __init__(self, config):  # type: (ReadOnlyDict) -> None
        self.config = config
        try:
            self.lo, po = get_readonly_connection()
        except UcsSchoolImportFatalError:
            self.lo, po = get_unprivileged_connection()
        self.logger = logging.getLogger(__name__)


def run_configuration_checks(config):  # type: (ReadOnlyDict) -> None
    def is_module_in_config(kls):  # type: (Type[object]) -> bool
        return kls.__module__ in config.get("configuration_checks", [])

    logger = logging.getLogger(__name__)
    loader = PyHooksLoader(CONFIG_CHECKS_CODE_DIR, ConfigurationChecks, logger, is_module_in_config)
    config_check_classes = loader.get_hook_classes()  # type: List[Type[ConfigurationChecks]]
    disabled_checks = config.get("disabled_checks", [])
    for kls in config_check_classes:
        cc = kls(config)
        test_methods = inspect.getmembers(
            cc, lambda x: inspect.ismethod(x) and x.__name__.startswith("test_")
        )
        test_methods.sort(key=itemgetter(0))
        for name, method in test_methods:
            if name in disabled_checks:
                logger.warning("Skipping configuration check %r.", name)
                continue
            method()
