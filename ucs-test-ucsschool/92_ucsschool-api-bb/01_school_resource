#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: test operations on school resource
## tags: [ucs_school_http_api]
## exposure: dangerous
## packages: [ucs-school-http-api-bb]
## bugs: []

from __future__ import unicode_literals
import logging
import requests
from unittest import main, TestCase
from ldap.filter import filter_format
try:
	from urlparse import urljoin  # py2
except ImportError:
	from urllib.parse import urljoin  # py3
import univention.testing.strings as uts
from ucsschool.importer.utils.ldap_connection import get_admin_connection
from ucsschool.lib.models.school import School as LibSchool
from univention.udm import UDM
from univention.testing.ucsschool.bb_api import API_ROOT_URL, HttpApiUserTestBase, RESSOURCE_URLS, setup_logging


logger = logging.getLogger("univention.testing.ucsschool")


class Test(TestCase):
	delete_ous = []

	@classmethod
	def setUpClass(cls):
		cls.lo, _po = get_admin_connection()
		cls.auth_headers = {"Authorization": "{} {}".format(*HttpApiUserTestBase.get_token())}
		print("*** auth_headers={!r}".format(cls.auth_headers))

	@classmethod
	def tearDownClass(cls):
		schools = LibSchool.get_all(cls.lo)
		for ou_name in cls.delete_ous:
			for school in schools:
				if school.name == ou_name:
					school.remove(cls.lo)

	def test_01_list_unauth_connection(self):
		response = requests.get(RESSOURCE_URLS['schools'])
		self.assertEqual(response.status_code, 401, 'response.status_code = {} for URL {!r} -> {!r}'.format(
			response.status_code, response.url, response.text))

	def test_02_list_auth_connection(self):
		response = requests.get(RESSOURCE_URLS['schools'], headers=self.auth_headers)
		self.assertEqual(response.status_code, 200, 'response.status_code = {} for URL  -> {!r}'.format(
			response.status_code, response.url, response.text))
		res = response.json()
		self.assertIsInstance(res, dict)
		self.assertIn('results', res)
		self.assertIsInstance(res['results'], list)
		self.assertIsInstance(res['results'][0], dict)
		self.assertIn('name', res['results'][0])
		self.assertIn('class_share_file_server', res['results'][0])

	def test_04_get_existing_ous(self):
		res = LibSchool.get_all(self.lo)
		if len(res) < 1:
			logger.error('No school was not found.')
			return

		udm = UDM.admin().version(1)
		for school in res:
			logger.info('*** school.to_dict()=%r', school.to_dict())
			response = requests.get(
				urljoin(RESSOURCE_URLS['schools'], school.name + "/"),
				headers=self.auth_headers
			)
			self.assertEqual(response.status_code, 200, 'response.status_code = {} for URL  -> {!r}'.format(
				response.status_code, response.url, response.text))
			for k, v in response.json().items():
				if k == 'url':
					continue
				elif k in ('class_share_file_server', 'home_share_file_server', 'administrative_servers', 'educational_servers') and v:
					logger.info('*** Looking up object for %r = %r...', k, v)
					ldap_val = getattr(school, k)
					if not ldap_val:
						self.fail('getattr({!r}, {!r})={!r}'.format(school, k, ldap_val))
					if k in ('administrative_servers', 'educational_servers'):
						logger.info('*** Looking up objects with DNs %r...', ldap_val)
						objs = [udm.obj_by_dn(lv) for lv in ldap_val]
						v_new = [o.props.name for o in objs]
					else:
						logger.info('*** Looking up object with DN %r...', ldap_val)
						obj = udm.obj_by_dn(ldap_val)
						v_new = obj.props.name
					self.assertEqual(
						v, v_new,
						'Value of attribute {!r} in LDAP is {!r} -> {!r} and in resource is {!r} ({!r}).'.format(
							k, ldap_val, v_new, v, school.dn))
				else:
					self.assertEqual(
						v, getattr(school, k),
						'Value of attribute {!r} in LDAP is {!r} and in resource is {!r} ({!r}).'.format(
							k, getattr(school, k), v, school.dn))

	def test_05_create_ou(self):
		attrs = {
			'display_name': uts.random_username(),
			'name': uts.random_username(),
		}
		self.delete_ous.append(attrs['name'])

		response = requests.post(RESSOURCE_URLS['schools'], headers=self.auth_headers, json=attrs)
		logger.info('*** response=%r', response)
		logger.info('*** response.json()=%r', response.json())
		self.assertEqual(response.status_code, 201, 'response.status_code = {} for URL  -> {!r}'.format(
			response.status_code, response.url, response.text))

		filter_s = filter_format('(&(objectClass=ucsschoolOrganizationalUnit)(ou=%s))', (attrs['name'],))
		res = self.lo.search(filter=filter_s)
		if len(res) != 1:
			logger.error('School {!r} not found: search with filter={!r} did not return 1 result:\n{}'.format(
				attrs['name'], filter_s, res))
		school_dn = res[0][0]
		school_attrs = res[0][1]
		LibSchool.from_dn(school_dn, None, self.lo).remove(self.lo)
		self.assertDictEqual(
			{
				'name': school_attrs['ou'][0],
				'display_name': school_attrs['displayName'][0]
			},
			attrs)


if __name__ == '__main__':
	main(verbosity=2)
