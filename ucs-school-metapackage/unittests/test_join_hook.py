#!/usr/bin/pytest-3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 Univention GmbH
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

import pytest

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
    import logging  # noqa: F401
    from typing import Any, List, NamedTuple, Optional  # noqa: F401

    from typing_extensions import Protocol

    from univention.config_registry import ConfigRegistry  # noqa: F401
    from univention.lib.package_manager import PackageManager  # noqa: F401

    StdoutStderr = NamedTuple("StdoutStderr", [("stdout", str), ("stderr", "str")])

    class JoinHookModule(Protocol):
        log = None  # type: Optional[logging.Logger]
        ucr = None  # type: Optional[ConfigRegistry]
        StdoutStderr = None  # type: StdoutStderr

        @staticmethod
        def call_cmd_locally(*cmd):  # type: (*str) -> StdoutStderr
            pass

        @staticmethod
        def determine_app_version(primary_node_app_version, package_manager):
            # type: (str, PackageManager) -> str
            pass

        @staticmethod
        def install_veyon_app(options, roles_pkg_list):  # type: (Any, List[str]) -> None
            pass


except ImportError:
    pass

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


options_mock = mock.MagicMock()
package = MockPackage()
package_manager = mock.MagicMock()
package_manager.get_package.return_value = package
ucr_mock = mock.MagicMock()


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
def join_hook_module():  # type: () -> JoinHookModule
    info = imp.find_module(JOIN_HOOK_FILE[:-3], [os.path.dirname(os.path.dirname(__file__))])
    with mock.patch(mock_import_func, side_effect=import_mock):
        return imp.load_module(JOIN_HOOK_FILE[:-3], *info)


def role_id(roles):  # type: (List[str]) -> str
    return roles[0] if roles else "<empty list>"


def test_determine_app_version_lower_than_req_for_44v7(join_hook_module):
    # type: (JoinHookModule) -> None
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
    # type: (JoinHookModule) -> None
    primary_node_app_version = "4.4 v7"
    package.version = "4.4.6-762"
    with mock.patch.object(join_hook_module, "log") as log_mock:
        result_version = join_hook_module.determine_app_version(
            primary_node_app_version, package_manager
        )
        assert result_version == "4.4 v7"
        assert not log_mock.warning.called


def test_determine_app_version_higher_than_req_for_44v7(join_hook_module):
    # type: (JoinHookModule) -> None
    primary_node_app_version = "4.4 v7"
    for local_errata_version in ("4.4.6-763", "4.4.6-999", "4.5.0-0", "4.5", "4.6.0-0", "5.0.0-0"):
        package.version = local_errata_version
        with mock.patch.object(join_hook_module, "log") as log_mock:
            result_version = join_hook_module.determine_app_version(
                primary_node_app_version, package_manager
            )
            assert result_version == "4.4 v7"
            assert not log_mock.warning.called


def test_determine_app_version_lower_than_req_for_44v9(join_hook_module):
    # type: (JoinHookModule) -> None
    primary_node_app_version = "4.4 v9"
    for local_errata_version, expected in (
        ("3.1.2-999", "4.4 v6"),
        ("4.4.6-761", "4.4 v6"),
        ("4.4.6-999", "4.4 v8"),
        ("4.4.7-840", "4.4 v8"),
    ):
        package.version = local_errata_version
        with mock.patch.object(join_hook_module, "log") as log_mock:
            result_version = join_hook_module.determine_app_version(
                primary_node_app_version, package_manager
            )
            assert result_version == expected
            assert log_mock.warning.called


def test_determine_app_version_equals_req_for_44v9(join_hook_module):
    # type: (JoinHookModule) -> None
    primary_node_app_version = "4.4 v9"
    package.version = "4.4.7-841"
    with mock.patch.object(join_hook_module, "log") as log_mock:
        result_version = join_hook_module.determine_app_version(
            primary_node_app_version, package_manager
        )
        assert result_version == "4.4 v9"
        assert not log_mock.warning.called


def test_determine_app_version_higher_than_req_for_44v9(join_hook_module):
    # type: (JoinHookModule) -> None
    primary_node_app_version = "4.4 v9"
    for local_errata_version in ("4.4.7-842", "4.4.7-999", "4.5.0-0", "4.5", "4.6.0-0", "5.0.0-0"):
        package.version = local_errata_version
        with mock.patch.object(join_hook_module, "log") as log_mock:
            result_version = join_hook_module.determine_app_version(
                primary_node_app_version, package_manager
            )
            assert result_version == "4.4 v9"
            assert not log_mock.warning.called


@pytest.mark.parametrize(
    "roles",
    (
        [],
        ["ucs-school-master"],
        ["ucs-school-singlemaster"],
        ["ucs-school-slave"],
        ["ucs-school-nonedu-slave"],
        ["ucs-school-central-slave"],
    ),
    ids=role_id,
)
def test_install_veyon_app(roles, join_hook_module):
    # type: (List[str], JoinHookModule) -> None
    with mock.patch.object(join_hook_module, "log") as log_mock, mock.patch.object(
        join_hook_module, "call_cmd_locally", return_value=join_hook_module.StdoutStderr("{}", "")
    ) as call_cmd_locally_mock, mock.patch.object(join_hook_module, "ucr", ucr_mock):
        if roles in ([], ["ucs-school-singlemaster"]):
            options_mock.server_role = "domaincontroller_master"
            ucr_mock.is_true.return_value = True
        else:
            options_mock.server_role = "foo"
            ucr_mock.is_true.return_value = False
        join_hook_module.install_veyon_app(options_mock, roles)
        assert log_mock.info.called
        if roles in ([], ["ucs-school-singlemaster"], ["ucs-school-slave"]):
            log_mock.info.assert_called_with("Log output of the installation goes to 'appcenter.log'.")
            assert "/usr/bin/univention-app" in call_cmd_locally_mock.call_args[0]
            assert "install" in call_cmd_locally_mock.call_args[0]
            assert "ucsschool-veyon-proxy" in call_cmd_locally_mock.call_args[0]
        else:
            log_mock.info.assert_called_with(
                "Not installing 'UCS@school Veyon Proxy' app on this system role."
            )
            assert not call_cmd_locally_mock.called
