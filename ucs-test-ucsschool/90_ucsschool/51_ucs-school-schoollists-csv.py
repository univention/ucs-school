#!/usr/share/ucs-test/runner /usr/bin/py.test
# -*- coding: utf-8 -*-
## desc: unit-test for csv-list creation
## exposure: dangerous
## tags: [apptest, ucsschool,unit-test]
## bugs: [51363]

import pytest
import csv
import StringIO
import random
import univention.testing.strings as uts


def random_ucr_values(n):
	values = []
	for _ in range(n):
		u = random.randint(0, 10)
		values.append(",".join(['{} {}'.format(uts.random_name(),
		                                       uts.random_name()) for _ in range(u)]))
	return values


def user_values(num_attributes, school_class):
	for _ in range(10):
		values = [uts.random_string() for _ in range(num_attributes)]
		values.append(school_class)
		yield values


@pytest.mark.parametrize("ucr_value", random_ucr_values(50))
@pytest.mark.parametrize("separator", [',', ' ', '\t'])
@pytest.mark.parametrize("group", [uts.random_name() for _ in range(5)])
def test_write_csv(ucr_value, separator, group):
	school_class = 'DEMOSCHOOL-{}'.format(group)
	csvfile = StringIO.StringIO()
	default = 'firstname Firstname,lastname Lastname,Class Class,username Username'
	ucr_value = ucr_value or default
	attributes, fieldnames = zip(*[field.split() for field in ucr_value.split(",")])
	writer = csv.writer(csvfile, delimiter=str(separator))
	writer.writerow(fieldnames)
	students = user_values(len(attributes), school_class)
	for student in students:
		writer.writerow(student)
	csvfile.close()
