#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: |
##  test Display.user()/Display.user_ldap() showing the email instead of the
##  username (UCR ucsschool/umc/grid/show-email-instead-of-username) and that
##  LDAP_Filter.forUsers() also searches the primary email address
## roles: [domaincontroller_master]
## tags: [ucsschool,apptest,ucsschool_base1]
## exposure: dangerous
## packages: [python3-ucsschool-lib]

from unittest.mock import patch

import pytest

from ucsschool.lib.school_umc_base import Display, LDAP_Filter

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
    """LDAP_Filter.forUsers() also matches the primary email address."""

    def test_searches_mail_primary_address(self):
        assert "mailPrimaryAddress=" in LDAP_Filter.forUsers("pattern")

    @pytest.mark.parametrize("attr", ["lastname", "username", "firstname"])
    def test_still_searches_name_attributes(self, attr):
        assert "%s=" % attr in LDAP_Filter.forUsers("pattern")
