#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test acceptence/conversion of birthday formats
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: safe
## packages:
##   - ucs-school-import

import datetime
import random
import pytest
from ucsschool.importer.utils.shell import *  # initialize import framework


def random_date():
	year = random.randint(1900, 2100)
	month = random.randint(1, 12)
	day = random.randint(1, 27)  # make sure not to hit an invalid day in february
	return year, month, day


test_data = [
	"{0}-{1:02d}-{2:02d}".format(*random_date()),  # YYYY-MM-DD
	"{2:02d}.{1:02d}.{0}".format(*random_date()),  # DD.MM.YYYY
	"{1:02d}/{2:02d}/{0}".format(*random_date()),  # MM/DD/YYYY
]
year, month, day = random_date()
test_data.append("{:02d}.{:02d}.{}".format(day, month, year % 100))  # DD.MM.YY
year, month, day = random_date()
test_data.append("{:02d}/{:02d}/{}".format(month, day, year % 100))  # MM/DD/YY


@pytest.mark.parametrize("test_date", test_data)
def test_birthday_formats(test_date):
	user = ImportUser(birthday=test_date)
	result = user.make_birthday()
	datetime.datetime.strptime(result, "%Y-%m-%d")
