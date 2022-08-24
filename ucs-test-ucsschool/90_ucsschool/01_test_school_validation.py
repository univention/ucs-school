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

import ucsschool.lib.create_ou as _create_ou
from ucsschool.lib.models.attributes import ValidationError


def test_schoolname_validation(schoolenv):
    """Test schoolname validation (related bug: #53506)"""
    assert os.getuid() == 0

    with pytest.raises(ValidationError, match=r"'Invalid school name'"):
        schoolenv.create_ou(ou_name="bad€ou_name")


def test_schoolname_underscore_name_validation(schoolenv):
    """Test schoolname validation: underscores are allowed in name if dc is set"""
    underscore_ou_name = "underscore_ou_name"
    with pytest.raises(ValidationError, match=r"'Invalid Domain Controller name'"):
        schoolenv.create_ou(ou_name=underscore_ou_name, name_edudc="not_ok")
    try:
        schoolenv.create_ou(ou_name=underscore_ou_name, name_edudc="Ok-name1")
    except ValidationError:
        assert False, "Ou name %r is allowed but validation failed " % underscore_ou_name


def test_create_ou_validation(schoolenv, mocker):
    mocker.patch("ucsschool.lib.models.School.create", return_value=True)
    underscore_ou_name = "underscore_ou_name"
    baseDN = schoolenv.ucr["ldap/base"]
    is_single_master = schoolenv.ucr.is_true("ucsschool/singlemaster", False)
    hostname = schoolenv.ucr.get("hostname")
    with pytest.raises(ValueError, match=r"'Invalid Domain Controller name'"):
        _create_ou.create_ou(
            underscore_ou_name,
            underscore_ou_name,
            "edu_name",
            "not_allowed",
            "share_name",
            schoolenv.lo,
            baseDN,
            hostname,
            is_single_master,
            False,
        )
    try:
        _create_ou.create_ou(
            underscore_ou_name,
            underscore_ou_name,
            "edu-name",
            "admin-name",
            "share_name",
            schoolenv.lo,
            baseDN,
            hostname,
            is_single_master,
            False,
        )
    except ValueError:
        assert False, "Ou name %r is allowed but validation failed " % underscore_ou_name
