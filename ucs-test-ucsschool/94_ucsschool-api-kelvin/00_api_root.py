#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test content of API root
## tags: [ucs_school_kelvin]
## exposure: dangerous
## packages: []
## bugs: []

from __future__ import unicode_literals

import logging
from unittest import TestCase, main

import requests

from univention.testing.ucsschool.kelvin_api import (
    OPENAPI_JSON_URL,
    RESOURCE_URLS,
    URL_BASE_PATH,
    HttpApiUserTestBase,
)

logger = logging.getLogger("univention.testing.ucsschool")


class Test(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth_headers = {"Authorization": "{} {}".format(*HttpApiUserTestBase.get_token())}
        print("*** auth_headers={!r}".format(cls.auth_headers))

    def test_01_unauth_connection_to_openapi_json_allowed(self):
        response = requests.get(OPENAPI_JSON_URL, verify=False)  # noqa: S501
        assert response.status_code == 200

    def test_02_expected_resources_exit_in_openapi_json(self):
        response = requests.get(OPENAPI_JSON_URL, verify=False)  # noqa: S501
        assert response.status_code == 200
        res = response.json()
        print("*** Resource paths in openapi.json: {!r}".format(res["paths"].keys()))
        for resource in RESOURCE_URLS:
            assert "{}{}/".format(URL_BASE_PATH, resource) in res["paths"].keys()

    def test_03_unauth_connection_to_resources_not_allowed(self):
        for url in RESOURCE_URLS.values():
            response = requests.get(url, verify=False)  # noqa: S501
            assert response.status_code == 401

    def test_04_auth_connection_to_resources_allowed(self):
        for url in RESOURCE_URLS.values():
            params = {}
            # workgroups has a required parameter for GET
            if url == RESOURCE_URLS["workgroups"]:
                schools = requests.get(
                    RESOURCE_URLS["schools"], headers=self.auth_headers, verify=False  # noqa: S501
                ).json()
                params["school"] = schools[0]["name"]
            response = requests.get(url, headers=self.auth_headers, verify=False, params=params)  # noqa: S501
            assert response.status_code == 200


if __name__ == "__main__":
    main(verbosity=2)
