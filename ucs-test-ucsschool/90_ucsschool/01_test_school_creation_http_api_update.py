#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Modify ucrv on school creation/deletion
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python-ucs-school
##   - ucs-school-selfservice-support
import os

import django

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ucsschool.http_api.app.settings")
django.setup()
from ucsschool.http_api.import_api.models import School  # noqa: E402


def test_school_creation():
    schoolenv = utu.UCSTestSchool()
    name = uts.random_name()
    schoolenv.create_ou(ou_name=name, use_cache=False)
    assert name in School.objects.all().values_list("name", flat=True)


if __name__ == "__main__":
    test_school_creation()
