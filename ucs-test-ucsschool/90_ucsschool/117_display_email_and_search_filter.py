#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: |
##  test Display.user()/Display.user_ldap() showing the email instead of the
##  username (UCR ucsschool/umc/show-email-instead-of-username) and that
##  LDAP_Filter.forUsers() searches the primary email address instead of the
##  username while that variable is set
## roles: [domaincontroller_master]
## tags: [ucsschool,apptest,ucsschool_base1]
## exposure: dangerous
## packages: [python3-ucsschool-lib]

from collections.abc import Callable, Iterator
from unittest.mock import patch

import pytest

from ucsschool.lib.school_umc_base import Display, LDAP_Filter
from univention.management.console.config import ucr as umc_ucr
from univention.testing.ucr import UCSTestConfigRegistry

# udm-object-like mapping (supports __getitem__, __contains__ and .get())
UDM_USER = {
    "lastname": "Doe",
    "firstname": "Jane",
    "username": "jdoe",
    "mailPrimaryAddress": "jane@example.com",
}
# raw LDAP attributes (bytes lists), as returned by an LDAP search
LDAP_USER = {
    "sn": [b"Doe"],
    "givenName": [b"Jane"],
    "uid": [b"jdoe"],
    "mailPrimaryAddress": [b"jane@example.com"],
}


@pytest.fixture
def show_email_instead_of_username(
    ucr: UCSTestConfigRegistry,
) -> Iterator[Callable[[bool | None], None]]:
    """
    Return a callable that sets ucsschool/umc/show-email-instead-of-username.

    `None` unsets the variable again, which is how it is shipped and therefore what the
    default behaviour has to be tested against.

    LDAP_Filter.forUsers() reads the ConfigRegistry of univention.management.console.config,
    which is loaded once when that module is imported, so it has to be reloaded after every
    change. The ucr fixture reverts the variable itself, but only after this fixture is torn
    down, hence the explicit revert before the final reload.
    """
    var = "ucsschool/umc/show-email-instead-of-username"

    def _set(enabled: bool | None) -> None:
        if enabled is None:
            ucr.handler_unset([var])
        else:
            ucr.handler_set(["%s=%s" % (var, "yes" if enabled else "no")])
        umc_ucr.load()

    yield _set

    ucr.revert_to_original_registry()
    umc_ucr.load()


class TestDisplayUser:
    """Display.user() works on udm-object-like mappings."""

    @patch.object(Display, "show_email_instead_of_username", lambda: False)
    def test_shows_username_by_default(self):
        assert Display.user(UDM_USER) == "Doe, Jane (jdoe)"

    @patch.object(Display, "show_email_instead_of_username", lambda: True)
    def test_shows_email_when_enabled(self):
        assert Display.user(UDM_USER) == "Doe, Jane (jane@example.com)"

    @patch.object(Display, "show_email_instead_of_username", lambda: True)
    def test_falls_back_to_username_without_email(self):
        assert Display.user(dict(UDM_USER, mailPrimaryAddress="")) == "Doe, Jane (jdoe)"
        user_no_attr = {"lastname": "Doe", "firstname": "Jane", "username": "jdoe"}
        assert Display.user(user_no_attr) == "Doe, Jane (jdoe)"

    @patch.object(Display, "show_email_instead_of_username", lambda: True)
    def test_without_firstname(self):
        user = {"lastname": "Doe", "username": "jdoe", "mailPrimaryAddress": "jane@example.com"}
        assert Display.user(user) == "Doe (jane@example.com)"


class TestDisplayUserLdap:
    """Display.user_ldap() works on raw (bytes) LDAP attribute dicts."""

    @patch.object(Display, "show_email_instead_of_username", lambda: False)
    def test_shows_username_by_default(self):
        assert Display.user_ldap(LDAP_USER) == "Doe, Jane (jdoe)"

    @patch.object(Display, "show_email_instead_of_username", lambda: True)
    def test_shows_email_when_enabled(self):
        assert Display.user_ldap(LDAP_USER) == "Doe, Jane (jane@example.com)"

    @patch.object(Display, "show_email_instead_of_username", lambda: True)
    def test_falls_back_to_username_without_email(self):
        ldap_obj = dict(LDAP_USER)
        del ldap_obj["mailPrimaryAddress"]
        assert Display.user_ldap(ldap_obj) == "Doe, Jane (jdoe)"


class TestForUsersFilter:
    """LDAP_Filter.forUsers() matches the primary email address instead of the username."""

    @pytest.mark.parametrize("enabled", [None, False], ids=["unset", "disabled"])
    def test_searches_username_while_disabled(
        self, show_email_instead_of_username: Callable[[bool | None], None], enabled: bool | None
    ) -> None:
        show_email_instead_of_username(enabled)
        users_filter = LDAP_Filter.forUsers("pattern")
        assert "username=" in users_filter
        assert "mailPrimaryAddress=" not in users_filter

    def test_searches_mail_primary_address_when_enabled(
        self, show_email_instead_of_username: Callable[[bool | None], None]
    ) -> None:
        show_email_instead_of_username(True)
        users_filter = LDAP_Filter.forUsers("pattern")
        assert "mailPrimaryAddress=" in users_filter
        assert "username=" not in users_filter

    @pytest.mark.parametrize("enabled", [None, True], ids=["unset", "enabled"])
    def test_always_searches_the_name_attributes(
        self, show_email_instead_of_username: Callable[[bool | None], None], enabled: bool | None
    ) -> None:
        show_email_instead_of_username(enabled)
        users_filter = LDAP_Filter.forUsers("pattern")
        assert "lastname=" in users_filter
        assert "firstname=" in users_filter
