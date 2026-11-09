#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: the local Samba of a school replica has the servicePrincipalName of Keycloak
## roles: [domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [univention-samba4, ucs-school-replica|ucs-school-nonedu-replica]
## bugs: [55403]

#
# Bug #55403: Windows clients need the servicePrincipalName HTTP/<Keycloak FQDN> of
# krbkeycloak in the local Samba for Kerberos SSO with Keycloak. The 62 join scripts of
# ucs-school-replica and ucs-school-nonedu-replica added it before Samba was provisioned,
# so new school replicas missed it. 98ucs-school-replica-keycloak-spn.inst adds it after
# the S4 connector has synchronized krbkeycloak.
#

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pytest

from univention.testing import utils

if TYPE_CHECKING:
    from pathlib import Path

    from univention.testing.ucr import UCSTestConfigRegistry

JOIN_SCRIPT = "98ucs-school-replica-keycloak-spn"
SERVICE_ACCOUNT = "krbkeycloak"


def list_spns() -> set[str]:
    output = subprocess.run(
        ["samba-tool", "spn", "list", SERVICE_ACCOUNT],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    # The SPNs are the indented lines after
    # "User CN=krbkeycloak,... has the following servicePrincipalName:"
    return {line.strip().lower() for line in output.splitlines() if line.startswith(("\t", " "))}


def run_join_script(admin_username: str, admin_pwdfile: Path) -> None:
    subprocess.run(
        [
            "univention-run-join-scripts",
            "-dcaccount",
            admin_username,
            "-dcpwd",
            str(admin_pwdfile),
            "--force",
            "--run-scripts",
            JOIN_SCRIPT,
        ],
        check=True,
    )


@pytest.fixture(scope="module")
def keycloak_spn(ucr: UCSTestConfigRegistry, ucr_domainname: str) -> str:
    lo = utils.get_ldap_connection()
    if not lo.searchDn(filter=f"(&(uid={SERVICE_ACCOUNT})(objectClass=person))"):
        pytest.skip(f"There is no Keycloak service account {SERVICE_ACCOUNT!r} in the domain.")
    # the join script takes the FQDN from the same UCR variable
    fqdn = urlparse(ucr.get("ucs/server/sso/uri", "")).hostname or f"ucs-sso-ng.{ucr_domainname}"
    return f"HTTP/{fqdn}"


@pytest.fixture
def admin_pwdfile(tmp_path: Path, admin_password: str) -> Path:
    pwdfile = tmp_path / "adminpw"
    pwdfile.write_text(admin_password)
    return pwdfile


def test_keycloak_spn_exists_after_join(keycloak_spn: str) -> None:
    """The join of the school replica must have added the Keycloak SPN to the local Samba."""
    assert keycloak_spn.lower() in list_spns(), (
        f"servicePrincipalName {keycloak_spn!r} of {SERVICE_ACCOUNT!r} is missing in the local Samba."
    )


def test_join_script_adds_missing_keycloak_spn(
    keycloak_spn: str, admin_username: str, admin_pwdfile: Path
) -> None:
    """Existing school replicas get the missing SPN when the join script runs again."""
    subprocess.run(["samba-tool", "spn", "delete", keycloak_spn, SERVICE_ACCOUNT], check=True)
    try:
        assert keycloak_spn.lower() not in list_spns()
        # A join script must be re-runnable without failure
        for _ in range(2):
            run_join_script(admin_username, admin_pwdfile)
            assert keycloak_spn.lower() in list_spns(), (
                f"{JOIN_SCRIPT} did not add the servicePrincipalName {keycloak_spn!r}."
            )
    finally:
        if keycloak_spn.lower() not in list_spns():
            subprocess.run(["samba-tool", "spn", "add", keycloak_spn, SERVICE_ACCOUNT], check=True)
