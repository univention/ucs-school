#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Check exam adding, putting and getting
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1,unittest]
## exposure: safe
## bugs: [52039]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]


import random

import pytest

import univention.testing.strings as uts
from univention.management.console.modules.computerroom.italc2 import UserMap

user_map = UserMap()


def random_user_str(n):  # type: (int) -> str
    enclosing = [
        ("[", "]"),
        ("{", "}"),
        ("(", ")"),
        ("$", "$"),
        ("&", "&"),
        ("/", "/"),
        ("", ""),
    ]
    for i in range(n // 2):
        a, b = random.choice(enclosing)
        yield "{0} ({1}{2}{3})".format(uts.random_username(), a, uts.random_username(), b)
    for i in range(n // 2):
        yield "{0} ({1})".format(uts.random_string(), uts.random_string())


@pytest.mark.parametrize("user_str", random_user_str(100))
def test_usermap_regex(user_str):
    user_map.validate_userstr(user_str)


def test_username_missing():
    for enclosing in [
        ("[", "]"),
        ("{", "}"),
        ("$", "$"),
        ("&", "&"),
        ("/", "/"),
        ("", ""),
    ]:
        a, b = enclosing
        user_str = "{0} {1}{2}{3}".format(uts.random_username(), a, uts.random_username(), b)
        with pytest.raises(AttributeError):
            user_map.validate_userstr(user_str)
