#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: diagnostic module 908 ignores unrelated groups matching admins-* pattern
## roles: [domaincontroller_master]
## tags: [ucsschool,diagnostic_test,apptest,ucsschool_base1]
## exposure: dangerous
## bugs: [59604]
## packages: []

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from univention.testing import utils

if TYPE_CHECKING:
    from univention.testing.udm import UCSTestUDM

plugin908 = importlib.import_module(
    "univention.management.console.modules.diagnostic.plugins.908_ucsschool_school_admin_accounts"
)


def test_admin_group_filter_ignores_unrelated_admins_named_group(udm_session: UCSTestUDM):
    """
    A customer may have their own group whose name happens to start with
    "admins-" for something entirely unrelated to UCS@school (e.g. a
    hand-made "admins-nextcloud" group). It must never be treated as a
    UCS@school school-admin group just because of its name.
    """
    group_dn, _group_name = udm_session.create_group(name="admins-nextcloud")

    lo = utils.get_ldap_connection(admin_uldap=True)
    matched_dns = [dn for dn, _attrs in lo.search(filter=plugin908.GROUP_FILTER)]
    assert group_dn not in matched_dns, (
        "GROUP_FILTER of diagnostic module 908_ucsschool_school_admin_accounts "
        "must not match unrelated, non-UCS@school groups like {!r}.".format(group_dn)
    )

    try:
        plugin908.run(None)
    except plugin908.Warning as exc:
        assert not all(
            s in str(exc.message)
            for s in [
                group_dn,
                plugin908.MALFORMED_GROUP_WARN_STR,
            ]
        ), (
            "The diagnostics module 908_ucsschool_school_admin_accounts.py must not report "
            "the unrelated, customer-created group {!r} as malformed!".format(group_dn)
        )
