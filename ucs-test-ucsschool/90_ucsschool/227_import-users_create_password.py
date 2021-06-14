#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: check password generation code
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - python-ucsschool-lib
## bugs: [45640]

import string

import pytest

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.udm as udm_test
from ucsschool.lib.models.utils import create_passwd

default_length = 8
default_specials = "$%&*-+=:.?"
forbidden_chars = ["i", "I", "l", "L", "o", "O", "0", "1"]
pw_count = 0


def create_pw(length, specials, num_specials_allowed):
    global pw_count
    cpw_kwargs = {"length": length, "dn": None}
    if specials is not None:
        cpw_kwargs["specials"] = specials

    pw = create_passwd(**cpw_kwargs)
    pw_count += 1
    assert len(pw) == length
    check_num_specials(pw, specials, num_specials_allowed)
    check_forbidden_chars(pw)
    check_char_classes(pw, specials if specials is not None else default_specials)


def check_pw_policy():
    global pw_count

    with udm_test.UCSTestUDM() as udm, ucr_test.UCSTestConfigRegistry() as ucr:
        for length in range(1, 21):
            policy_dn = udm.create_object(
                "policies/pwhistory",
                position="cn=pwhistory,cn=users,cn=policies,{}".format(ucr["ldap/base"]),
                name=uts.random_name(),
                pwLength=length,
            )
            user_dn, username = udm.create_user(
                policy_reference=policy_dn, password=uts.random_string(length)
            )
            pw = create_passwd(dn=user_dn)
            pw_count += 1
            assert len(pw) == length
            check_num_specials(pw)
            check_forbidden_chars(pw)
            check_char_classes(pw, default_specials)


def check_num_specials(pw, specials=None, num_specials_allowed=None):
    specials = default_specials if specials is None else specials
    forbidden_specials = set(default_specials) - set(specials)
    num_specials_allowed = len(pw) // 5 if num_specials_allowed is None else num_specials_allowed

    num_specials = 0
    for char in pw:
        assert char not in forbidden_specials
        if char in specials:
            num_specials += 1
    assert num_specials <= num_specials_allowed


def check_char_classes(pw, specials):
    assert any(char in (string.ascii_lowercase + string.ascii_uppercase) for char in pw)

    if len(pw) >= 4:
        assert any(char in string.ascii_lowercase for char in pw)
        assert any(char in string.ascii_uppercase for char in pw)
        assert any(char in string.digits for char in pw)
        if specials != "" and len(pw) // 5 > 0:
            assert any(char in specials for char in pw), (specials, pw)


def check_forbidden_chars(pw):
    for char in pw:
        assert char not in forbidden_chars


def test_import_user_create_password():
    global pw_count

    print("Checking default password length...")
    pw = create_passwd()
    pw_count += 1
    assert len(pw) == default_length
    check_num_specials(pw)
    check_forbidden_chars(pw)

    print("Checking password length 0...")
    with pytest.raises(AssertionError):
        pw = create_passwd(0)

    for length in range(1, 21):
        print("Checking password length {}...".format(length))
        for _x in range(100):
            create_pw(length, None, None)
            create_pw(length, "", 0)
            create_pw(length, "@#~", None)

    print("Checking password policy...")
    check_pw_policy()

    print("Checked {} passwords.".format(pw_count))
