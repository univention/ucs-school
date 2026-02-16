#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test School.get_all
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest, ucsschool, ucs-school-lib]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

from __future__ import annotations

from typing import TYPE_CHECKING

from ucsschool.lib.models.school import School

if TYPE_CHECKING:
    from univention.testing.ucsschool.ucs_test_school import UCSTestSchool


def test_filter_local(schoolenv: UCSTestSchool):
    current_hostname = schoolenv.ucr.get("hostname")
    _, local_school_dn = schoolenv.create_ou(name_edudc=current_hostname)
    _, other_school_dn = schoolenv.create_ou(name_edudc="otherhost")

    local_schools = School.get_all(schoolenv.lo)
    assert len(local_schools) >= 1
    assert any(school.dn == local_school_dn for school in local_schools)
    if schoolenv.ucr.get("server/role") in ("domaincontroller_master", "domaincontroller_backup"):
        assert any(school.dn == other_school_dn for school in local_schools)
    else:
        assert not any(school.dn == other_school_dn for school in local_schools)

    all_schools = School.get_all(schoolenv.lo, filter_local=False)
    assert len(all_schools) >= 2
    assert any(school.dn == local_school_dn for school in all_schools)
    assert any(school.dn == other_school_dn for school in all_schools)
