#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: Modify ucrv on school creation/deletion
## roles: [domaincontroller_master, domaincontroller_backup]
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python-ucsschool-lib
##   - ucs-school-import-http-api
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ucsschool.http_api.app.settings")  # noqa: E402
django.setup()  # noqa: E402
import univention.testing.strings as uts  # noqa: E402
import univention.testing.ucsschool.ucs_test_school as utu  # noqa: E402
from ucsschool.http_api.import_api.models import School  # noqa: E402


def test_school_creation():
    schoolenv = utu.UCSTestSchool()
    name = uts.random_name()
    schoolenv.create_ou(ou_name=name, use_cache=False)
    assert name in list(School.objects.all().values_list("name", flat=True))
