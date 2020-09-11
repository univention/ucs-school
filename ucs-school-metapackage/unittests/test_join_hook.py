#!/usr/bin/pytest
# -*- coding: utf-8 -*-
#
# Copyright 2020 Univention GmbH
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

import imp
import os.path
import sys

if sys.version_info.major > 2:
    import builtins
    from unittest import mock

    orig_import = builtins.__import__
    mock_import_func = "builtins.__import__"
else:
    import mock

    orig_import = __import__
    mock_import_func = "__builtin__.__import__"

try:
    import typing
    from types import ModuleType
except ImportError:
    pass

import pytest

JOIN_HOOK_FILE = "ucsschool-join-hook.py"


class MockPackage(object):
    _version = 0

    @property
    def installed(self):
        return self

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        self._version = value


package = MockPackage()
package_manager = mock.MagicMock()
package_manager.get_package.return_value = package


def import_mock(name, *args):
    if name in [
        "ldap.filter",
        "univention.admin",
        "univention.config_registry",
        "univention.lib.package_manager",
    ]:
        return mock.MagicMock()
    return orig_import(name, *args)


@pytest.fixture(scope="session")
def join_hook_module():  # type () -> ModuleType
    info = imp.find_module(JOIN_HOOK_FILE[:-3], [os.path.dirname(os.path.dirname(__file__))])
    with mock.patch(mock_import_func, side_effect=import_mock):
        return imp.load_module(JOIN_HOOK_FILE[:-3], *info)


def test_determine_app_version_lower_than_req_for_44v7(join_hook_module):
    primary_node_app_version = "4.4 v7"
    for local_errata_version in ("3.1.2-999", "4.4.5-999", "4.4.6-761"):
        package.version = local_errata_version
        with mock.patch.object(join_hook_module, "log") as log_mock:
            result_version = join_hook_module.determine_app_version(
                primary_node_app_version, package_manager
            )
            assert result_version == "4.4 v6"
            assert log_mock.warning.called


def test_determine_app_version_equals_req_for_44v7(join_hook_module):
    primary_node_app_version = "4.4 v7"
    package.version = "4.4.6-762"
    with mock.patch.object(join_hook_module, "log") as log_mock:
        result_version = join_hook_module.determine_app_version(
            primary_node_app_version, package_manager
        )
        assert result_version == "4.4 v7"
        assert not log_mock.warning.called


def test_determine_app_version_higher_than_req_for_44v7(join_hook_module):
    primary_node_app_version = "4.4 v7"
    for local_errata_version in ("4.4.6-763", "4.4.6-999", "4.5.0-0", "4.5", "4.6.0-0", "5.0.0-0"):
        package.version = local_errata_version
        with mock.patch.object(join_hook_module, "log") as log_mock:
            result_version = join_hook_module.determine_app_version(
                primary_node_app_version, package_manager
            )
            assert result_version == "4.4 v7"
            assert not log_mock.warning.called