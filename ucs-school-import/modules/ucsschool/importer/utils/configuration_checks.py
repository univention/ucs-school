# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2018-2019 Univention GmbH
#
# http://www.univention.de/
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
from ucsschool.lib.pyhooks.pyhooks_loader import PyHooksLoader
from ..exceptions import UcsSchoolImportFatalError
from .ldap_connection import get_readonly_connection, get_unprivileged_connection

try:
	from typing import List, Type
	from ..configuration import ReadOnlyDict
except ImportError:
	pass


__all__ = ['ConfigurationChecks']

CONFIG_CHECKS_CODE_DIR = '/usr/share/ucs-school-import/checks'


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
		self.lo, po = get_unprivileged_connection()
		self.logger = logging.getLogger(__name__)


def run_configuration_checks(config):  # type: (ReadOnlyDict) -> None
	def is_module_in_config(kls):  # type: (Type[object]) -> bool
		return kls.__module__ in config.get('configuration_checks', [])

	logger = logging.getLogger(__name__)
	loader = PyHooksLoader(CONFIG_CHECKS_CODE_DIR, ConfigurationChecks, logger, is_module_in_config)
	config_check_classes = loader.get_hook_classes()  # type: List[Type[ConfigurationChecks]]
	for kls in config_check_classes:
		cc = kls(config)
		test_methods = inspect.getmembers(cc, lambda x: inspect.ismethod(x) and x.func_name.startswith('test_'))
		test_methods.sort(key=itemgetter(0))
		for name, method in test_methods:
			method()
