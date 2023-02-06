#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## -*- coding: utf-8 -*-
## desc: test operations on school resource
## tags: [ucs_school_kelvin]
## exposure: dangerous
## packages: []
## bugs: []

from __future__ import unicode_literals

import logging
import random
from typing import Set, Tuple  # noqa: F401

import requests
from ldap.filter import filter_format
from six import string_types

from ucsschool.lib.models.group import WorkGroup as LibWorkGroup
from ucsschool.lib.models.user import Student as LibStudent
from univention.testing.ucsschool.kelvin_api import RESOURCE_URLS
from univention.udm import UDM

try:
    from urlparse import urljoin  # py2
except ImportError:
    from urllib.parse import urljoin  # py3


_cached_wgs = set()  # type: Set[Tuple[str,str]]
logger = logging.getLogger("univention.testing.ucsschool")

EXPECTED_WORKGROUP_RESOURCE_ATTRS = {
    "dn",
    "url",
    "ucsschool_roles",
    "udm_properties",
    "name",
    "school",
    "description",
    "users",
    "create_share",
    "email",
    "allowed_email_senders_users",
    "allowed_email_senders_groups",
}


def test_not_authenticated_connection():
    response = requests.get(RESOURCE_URLS["workgroups"])
    assert response.status_code == 401, "response.status_code = {} for URL {!r} -> {!r}".format(
        response.status_code, response.url, response.text
    )


def test_list(auth_header, lo, schoolenv):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"), use_cache=False)
    student = LibStudent(
        name="teststudent",
        school=ou_name,
        firstname="teststudent",
        lastname="teststudent",
    )
    student.create(lo)
    workgroup = LibWorkGroup(
        name="{}-testworkgroup".format(ou_name),
        school=ou_name,
        users=[student.dn],
        allowed_email_senders_users=[],
        allowed_email_senders_groups=[],
    )
    workgroup.create(lo)

    print(" ** auth_header={!r}".format(auth_header))
    response = requests.get(RESOURCE_URLS["workgroups"], headers=auth_header, params={"school": ou_name})
    assert response.status_code == 200, "response.status_code = {} for URL {!r} -> {!r}".format(
        response.status_code, response.url, response.text
    )
    json_response = response.json()
    assert isinstance(json_response, list)
    for obj in json_response:
        assert EXPECTED_WORKGROUP_RESOURCE_ATTRS.issubset(set(obj.keys()))
        for k, _v in obj.items():
            assert k in obj
            if k in (
                "ucsschool_roles",
                "users",
                "allowed_email_senders_users",
                "allowed_email_senders_groups",
            ):
                assert isinstance(obj[k], list)
            elif k == "udm_properties":
                assert isinstance(obj[k], dict)
            elif k == "create_share":
                assert isinstance(obj[k], bool)
            else:
                assert isinstance(obj[k], (string_types, type(None)))


def test_get(auth_header, lo, ucr_ldap_base, schoolenv):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"), use_cache=False)
    school_url = urljoin(RESOURCE_URLS["schools"], ou_name)
    student = LibStudent(
        name="teststudent",
        school=ou_name,
        firstname="teststudent",
        lastname="teststudent",
    )
    student.create(lo)
    workgroup = LibWorkGroup(
        name="{}-testworkgroup".format(ou_name),
        school=ou_name,
        users=[student.dn],
        allowed_email_senders_users=[],
        allowed_email_senders_groups=[],
    )
    workgroup.create(lo)

    logger.info("*** workgroup.to_dict()=%r", workgroup.to_dict())
    workgroup_url = urljoin(
        urljoin(RESOURCE_URLS["workgroups"], ou_name) + "/",
        workgroup.name.split("-", 1)[1],
    )
    school_url = urljoin(RESOURCE_URLS["schools"], ou_name)
    response = requests.get(workgroup_url, headers=auth_header)
    assert response.status_code == 200, "response.status_code = {} for URL {!r} -> {!r}".format(
        response.status_code, response.url, response.text
    )
    json_response = response.json()
    assert EXPECTED_WORKGROUP_RESOURCE_ATTRS.issubset(set(json_response.keys()))
    udm = UDM.admin().version(1)
    for k, v in json_response.items():
        if k == "url":
            assert v == workgroup_url
        elif k == "name":
            assert "{}-{}".format(ou_name, v) == workgroup.name
        elif k == "school":
            assert v == school_url
        elif k == "udm_properties":
            continue  # We are not interested in that here.
        elif k == "users":
            assert [user.split("/")[-1] for user in v] == [
                user.split(",", 1)[0][len("uid=") :] for user in workgroup.users
            ]
        elif k == "create_share" and v:
            logger.info("*** Looking up share object.")
            share_obj = udm.obj_by_dn(
                "cn={},cn=shares,ou={},{}".format(workgroup.name, ou_name, ucr_ldap_base)
            )
            assert workgroup.name == share_obj.props.name
        else:
            assert v == getattr(
                workgroup, k
            ), "Value of attribute {!r} in LDAP is {!r} and in resource is {!r} ({!r}).".format(
                k, getattr(workgroup, k), v, workgroup.dn
            )


def test_create(auth_header, lo, schoolenv):
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"), use_cache=False)
    school_url = urljoin(RESOURCE_URLS["schools"], ou_name)
    attrs = {
        "name": "testwg{}".format(random.randint(1000, 9999)),
        "school": school_url,
    }
    response = requests.post(RESOURCE_URLS["workgroups"], headers=auth_header, json=attrs)
    assert response.status_code == 201, "response.status_code = {} for URL {!r} -> {!r}".format(
        response.status_code, response.url, response.text
    )
    logger.info("*** response.json()=%r", response.json())
    filter_s = filter_format(
        "(&(objectClass=ucsschoolGroup)(cn=%s-%s))",
        (
            ou_name,
            attrs["name"],
        ),
    )
    res = lo.search(filter=filter_s)
    assert (
        len(res) == 1
    ), "Workgroup {!r} not found: search with filter={!r} did not return 1 result:\n{}".format(
        attrs["name"], filter_s, res
    )
    workgroup_attrs = res[0][1]
    assert {
        "name": workgroup_attrs["cn"][0].decode("utf-8").split("-")[-1],
        "school": urljoin(
            RESOURCE_URLS["schools"],
            workgroup_attrs["cn"][0].decode("utf-8").split("-")[0],
        ),
    } == attrs
