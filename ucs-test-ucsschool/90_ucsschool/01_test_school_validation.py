#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test school validation
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

import os

import pytest

from ucsschool.lib.models.attributes import ValidationError


def test_schoolname_validation(schoolenv):
    """Test schoolname validation (related bug: #53506)"""
    assert os.getuid() == 0

    with pytest.raises(ValidationError, match=r"'Invalid school name'"):
        schoolenv.create_ou(ou_name="bad€ou_name")
