#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
# -*- coding: utf-8 -*-
## desc: unit-test for csv-list creation
## exposure: dangerous
## tags: [apptest, ucsschool,unit-test, ucs-school-umc-list]
## bugs: [51363]
## packages: [ucs-school-umc-lists]

import random

import pytest

import univention.testing.strings as uts
from univention.management.console.modules.schoollists import write_classlist_csv


def random_ucr_values(n):
    values = []
    for _ in range(n):
        u = random.randint(0, 10)
        values.append(",".join(["{} {}".format(uts.random_name(), uts.random_name()) for _ in range(u)]))
    return values


def user_values(num_attributes, school_class):
    students = []
    for _ in range(10):
        values = [uts.random_string() for _ in range(num_attributes)]
        values.append(school_class)
        students.append(values)
    return students


@pytest.mark.parametrize("ucr_value", random_ucr_values(50))
@pytest.mark.parametrize("separator", [",", " ", "\t"])
@pytest.mark.parametrize("group", [uts.random_name() for _ in range(5)])
def test_write_csv(ucr_value, separator, group):
    school_class = "DEMOSCHOOL-{}".format(group)
    default = "firstname Firstname,lastname Lastname,username Username"
    ucr_value = ucr_value or default
    attributes, fieldnames = zip(*[field.split() for field in ucr_value.split(",")])
    students = user_values(len(attributes), school_class)
    attributes, fieldnames = list(attributes), list(fieldnames)
    fieldnames.append("Class")
    attributes.append("Class")
    result = write_classlist_csv(fieldnames, students, separator)
    lines = result.strip().split("\n")
    header = lines[0]
    assert separator.join(fieldnames) == header.strip()
    body = lines[1:]
    assert len(body) == len(students)
    for i, line in enumerate(body):
        assert separator.join(students[i]) == line.strip()
