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
from typing import Set  # noqa: F401

import pytest
import requests
from ldap.filter import filter_format
from six import string_types

import univention.testing.strings as uts
from ucsschool.lib.models.school import School as LibSchool
from univention.testing.ucsschool.kelvin_api import RESOURCE_URLS
from univention.udm import UDM, NoObject as UdmNoObject

try:
    from urlparse import urljoin  # py2
except ImportError:
    from urllib.parse import urljoin  # py3


_cached_ous = set()  # type: Set[str]
logger = logging.getLogger("univention.testing.ucsschool")

EXPECTED_SCHOOL_RESSOURCE_ATTRS = {
    "administrative_servers",
    "class_share_file_server",
    "display_name",
    "dn",
    "educational_servers",
    "home_share_file_server",
    "name",
    "ucsschool_roles",
    "url",
    "udm_properties",
}


@pytest.fixture(scope="session")
def delete_ou_cleanup(ucr_ldap_base, ucr):
    def _func(ou_name):  # type (str) -> None
        udm = UDM.admin().version(0)
        group_dns = [
            "cn=admins-{},cn=ouadmins,cn=groups,{}".format(ou_name.lower(), ucr_ldap_base),
            "cn=OU{}-Klassenarbeit,cn=ucsschool,cn=groups,{}".format(ou_name, ucr_ldap_base),
            "cn=OU{}-DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ou_name.lower(), ucr_ldap_base),
            "cn=OU{}-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(
                ou_name.lower(), ucr_ldap_base
            ),
            "cn=OU{}-Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(
                ou_name.lower(), ucr_ldap_base
            ),
            "cn=OU{}-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(
                ou_name.lower(), ucr_ldap_base
            ),
        ]
        mod = udm.get("groups/group")
        for dn in group_dns:
            print("Deleting group: {!r}...".format(dn))
            try:
                obj = mod.get(dn)
                obj.delete()
            except UdmNoObject:
                print("Error: group does not exist: {!r}".format(dn))
        if ucr.is_true("ucsschool/singlemaster"):
            master_hostname = ucr["hostname"]
            mod = udm.get("computers/domaincontroller_master")
            for obj in mod.search("cn={}".format(master_hostname)):
                print(
                    "Removing 'ucsschoolRole=single_master:school:{}' from {!r}...".format(
                        ou_name, obj.dn
                    )
                )
                try:
                    obj.props.ucsschoolRole.remove("single_master:school:{}".format(ou_name))
                    obj.save()
                except ValueError:
                    print("Error: role was no set: ucsschoolRole={!r}".format(obj.props.ucsschoolRole))

    return _func


@pytest.fixture(scope="session")
def schedule_delete_ou_at_end_of_session(delete_ou, delete_ou_cleanup):
    def _func(ou_name):  # type: (str) -> None
        _cached_ous.add(ou_name)

    yield _func

    for ou_name in _cached_ous:
        delete_ou(ou_name)
        delete_ou_cleanup(ou_name)


def test_not_authenticated_connection():
    response = requests.get(RESOURCE_URLS["schools"])
    assert response.status_code == 401, "response.status_code = {} for URL {!r} -> {!r}".format(
        response.status_code, response.url, response.text
    )


def test_list(auth_header):
    print(" ** auth_header={!r}".format(auth_header))
    response = requests.get(RESOURCE_URLS["schools"], headers=auth_header)
    assert response.status_code == 200, "response.status_code = {} for URL {!r} -> {!r}".format(
        response.status_code, response.url, response.text
    )
    json_response = response.json()
    assert isinstance(json_response, list)
    for obj in json_response:
        assert EXPECTED_SCHOOL_RESSOURCE_ATTRS.issubset(set(obj.keys()))
        for k, _v in obj.items():
            assert k in obj
            if k in ("administrative_servers", "educational_servers", "ucsschool_roles"):
                assert isinstance(obj[k], list)
            elif k == "udm_properties":
                assert isinstance(obj[k], dict)
            else:
                assert isinstance(obj[k], (string_types, type(None)))


def test_get(auth_header, lo):
    schools = LibSchool.get_all(lo)
    if len(schools) < 1:
        raise RuntimeError("No school was not found.")

    udm = UDM.admin().version(1)
    for school in schools:
        logger.info("*** school.to_dict()=%r", school.to_dict())
        school_url = urljoin(RESOURCE_URLS["schools"], school.name)
        response = requests.get(school_url, headers=auth_header)
        assert response.status_code == 200, "response.status_code = {} for URL {!r} -> {!r}".format(
            response.status_code, response.url, response.text
        )
        json_response = response.json()
        assert EXPECTED_SCHOOL_RESSOURCE_ATTRS.issubset(set(json_response.keys()))
        for k, v in json_response.items():
            if k == "url":
                assert v == school_url
            elif k == "udm_properties":
                continue  # We are not interested in that here.
            elif (
                k
                in (
                    "administrative_servers",
                    "class_share_file_server",
                    "educational_servers",
                    "home_share_file_server",
                )
                and v
            ):
                logger.info("*** Looking up object for %r = %r...", k, v)
                ldap_val = getattr(school, k)
                assert ldap_val, "getattr({!r}, {!r})={!r}".format(school, k, ldap_val)
                if k in ("administrative_servers", "educational_servers"):
                    logger.info("*** Looking up objects with DNs %r...", ldap_val)
                    objs = [udm.obj_by_dn(lv) for lv in ldap_val]
                    v_new = [o.props.name for o in objs]
                else:
                    logger.info("*** Looking up object with DN %r...", ldap_val)
                    obj = udm.obj_by_dn(ldap_val)
                    v_new = obj.props.name
                assert v == v_new, (
                    "Value of attribute {!r} in LDAP is {!r} -> {!r} and in resource is {!r} "
                    "({!r}).".format(k, ldap_val, v_new, v, school.dn)
                )
            else:
                assert v == getattr(
                    school, k
                ), "Value of attribute {!r} in LDAP is {!r} and in resource is {!r} ({!r}).".format(
                    k, getattr(school, k), v, school.dn
                )


def test_create(auth_header, lo, schedule_delete_ou_at_end_of_session):
    attrs = {
        "display_name": uts.random_username(),
        "name": "testou{}".format(random.randint(1000, 9999)),
    }
    schedule_delete_ou_at_end_of_session(attrs["name"])

    response = requests.post(RESOURCE_URLS["schools"], headers=auth_header, json=attrs)
    assert response.status_code == 201, "response.status_code = {} for URL {!r} -> {!r}".format(
        response.status_code, response.url, response.text
    )
    logger.info("*** response.json()=%r", response.json())
    filter_s = filter_format("(&(objectClass=ucsschoolOrganizationalUnit)(ou=%s))", (attrs["name"],))
    res = lo.search(filter=filter_s)
    assert (
        len(res) == 1
    ), "School {!r} not found: search with filter={!r} did not return 1 result:\n{}".format(
        attrs["name"], filter_s, res
    )
    school_attrs = res[0][1]
    assert {
        "name": school_attrs["ou"][0].decode("utf-8"),
        "display_name": school_attrs["displayName"][0].decode("utf-8"),
    } == attrs
