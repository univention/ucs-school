#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check ucs config in ucs@school
## tags: [apptest, ucsschool]
## exposure: safe

import pytest

import univention.config_registry
import univention.testing.utils as utils

ucr = univention.config_registry.ConfigRegistry()
ucr.load()


def check_setting(setting, value):
    assert ucr[setting] == value, "{} not correctly configured (is {}, should be {})".format(
        setting, value, ucr[setting]
    )


settings_connector = {
    "connector/s4/mapping/sid_to_s4": "yes",
    "connector/s4/mapping/sid_to_ucs": "no",
    "connector/s4/mapping/syncmode": "sync",
    "connector/s4/mapping/msprintconnectionpolicy": "yes",
    "connector/s4/mapping/msgpwl": "yes",
    "connector/s4/mapping/wmifilter": "yes",
    "connector/s4/mapping/gpo": "true",
    "connector/s4/mapping/dns/ignorelist": "_ldap._tcp.Default-First-Site-Name._site",
}

settings_samba = {
    "samba4/ldb/sam/module/prepend": "univention_samaccountname_ldap_check",
}

settings_school_slave = {
    "connector/s4/mapping/user/ignorelist": "root,ucs-s4sync,krbtgt,Guest",
    "connector/s4/allow/secondary": "true",
}


def test_settings_univention_samba4():
    if not utils.package_installed("univention-samba4"):
        pytest.skip("Missing univention-samba4")
    for setting, value in settings_samba.items():
        if setting == "samba4/ldb/sam/module/prepend" and not any(
            (
                utils.package_installed("ucs-school-singlemaster"),
                utils.package_installed("ucs-school-slave"),
                utils.package_installed("ucs-school-nonedu-slave"),
            )
        ):
            # Bug #49726: test only on slave / singlemaster
            continue
        check_setting(setting, value)


def test_settings_s4connector():
    if not utils.package_installed("univention-s4-connector"):
        pytest.skip("Missing univention-s4-connector")
    for setting, value in settings_connector.items():
        check_setting(setting, value)


def test_settings_ucs_school_slave():
    if not utils.package_installed("ucs-school-slave"):
        pytest.skip("Missing ucs-school-slave")
    for setting, value in settings_school_slave.items():
        check_setting(setting, value)
