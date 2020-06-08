#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: test content of API root
## tags: [ucs_school_kelvin]
## exposure: dangerous
## packages: []
## bugs: []

from __future__ import unicode_literals
import logging
import requests
from unittest import main, TestCase
from univention.testing.ucsschool.kelvin_api import HttpApiUserTestBase, OPENAPI_JSON_URL, RESSOURCE_URLS, URL_BASE_PATH


logger = logging.getLogger("univention.testing.ucsschool")


class Test(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.auth_headers = {"Authorization": "{} {}".format(*HttpApiUserTestBase.get_token())}
		print("*** auth_headers={!r}".format(cls.auth_headers))

	def test_01_unauth_connection_to_openapi_json_allowed(self):
		response = requests.get(OPENAPI_JSON_URL, verify=False)
		self.assertEqual(response.status_code, 200, "response.status_code = {} for URL {!r} -> {!r}".format(
				response.status_code, response.url, response.text
			)
		)

	def test_02_expected_resources_exit_in_openapi_json(self):
		response = requests.get(OPENAPI_JSON_URL, verify=False)
		self.assertEqual(response.status_code, 200, "{!r} -> [{}] {!r}".format(
				response.url, response.status_code, response.text
			)
		)
		res = response.json()
		print("*** Resource paths in openapi.json: {!r}".format(res["paths"].keys()))
		for resource in RESSOURCE_URLS:
			self.assertIn("{}{}/".format(URL_BASE_PATH, resource), res["paths"].keys())

	def test_03_unauth_connection_to_resources_not_allowed(self):
		for url in RESSOURCE_URLS.values():
			response = requests.get(url, verify=False)
			self.assertEqual(response.status_code, 401, "{!r} -> [{}] {!r}".format(
					response.url, response.status_code, response.text
				)
			)

	def test_04_auth_connection_to_resources_allowed(self):
		for url in RESSOURCE_URLS.values():
			response = requests.get(url, headers=self.auth_headers, verify=False)
			self.assertEqual(response.status_code, 200, "{!r} -> [{}] {!r}".format(
					response.url, response.status_code, response.text
				)
			)


if __name__ == "__main__":
	main(verbosity=2)
