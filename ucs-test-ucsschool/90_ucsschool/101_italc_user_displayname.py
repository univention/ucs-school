#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test displayname regex in italc
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: safe
## packages:
##   - ucs-school-umc-computerroom
## bugs: [52039]

import random

import pytest

import univention.testing.strings as uts
from univention.management.console.modules.computerroom.italc2 import UserMap

regex = UserMap.USER_REGEX


def random_display_name(n):  # type: (int) -> str
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


@pytest.mark.parametrize("display_name", random_display_name(100))
def test_usermap_regex(display_name):
    match = regex.match(display_name)
    assert match, "Invalid displayName: {}".format(display_name)


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
        display_name = "{0} {1}{2}{3}".format(uts.random_username(), a, uts.random_username(), b)
        match = regex.match(display_name)
        real_name = match.groupdict()["real_name"]
        assert not real_name, "Missing brackets in {}".format(display_name)
