#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.share.MarketplaceShare
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: safe
## packages:
##   - ucs-school-import

import random
from typing import Iterable, Tuple  # noqa: F401

import pytest

import univention.testing.strings as uts
from ucsschool.importer.models.import_user import ImportUser

bad_chars = "äöüßàáâãåç"
repl_char = "-"


def names():  # type: () -> Iterable[Tuple[str, str]]
    res = []
    for bad_char in bad_chars:
        school = uts.random_username(8)
        class_name = uts.random_username(8)
        good_class_name = "{}-{}".format(school, class_name)
        pos = random.randint(0, len(class_name))
        bad_class_name = list(class_name)
        bad_class_name.insert(pos, bad_char)
        res.append((good_class_name, "{}-{}".format(school, "".join(bad_class_name))))
    return res


def ids(name):  # type: (Tuple[str, str]) -> str
    return "{} | {}".format(*name)


@pytest.mark.parametrize("name", names(), ids=ids)
def test_school_classes_invalid_character_replacement(name):
    good_class_name, bad_class_name = name
    calculated_name = ImportUser.school_classes_invalid_character_replacement(bad_class_name, repl_char)
    school, class_name = calculated_name.split("-", 1)
    removed_repl_char_name = class_name.replace(repl_char, "")
    calc_name_no_repl = "{}-{}".format(school, removed_repl_char_name)
    assert calc_name_no_repl == good_class_name
