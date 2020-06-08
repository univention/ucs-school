#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Check roles through the python client
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import-http-api
##   - ucs-school-import-http-api-client
## bugs: [45749]

import pprint
import random
from ldap.filter import filter_format
import univention.testing.strings as uts
from ucsschool.http_api.client import Client
from univention.testing.ucsschool.importusers_http import HttpApiImportTester


class Test(HttpApiImportTester):
	def test(self):
		user_creation_fn = [self.schoolenv.create_staff, self.schoolenv.create_teacher, self.schoolenv.create_teacher_and_staff]
		ous = [self.ou_A, self.ou_B, self.ou_C]
		password = uts.random_string()
		random.shuffle(user_creation_fn)
		random.shuffle(ous)
		all_roles = list(self.all_roles)
		random.shuffle(all_roles)

		self.log.info('*** Creating user...')
		username, user_dn = user_creation_fn[0](ous[0].name, password=password)

		self.log.info('*** Modifying import-permission groups...')
		role_combinations = [{all_roles[0], all_roles[1]}, {all_roles[1], all_roles[2]}, {all_roles[2]}]

		groups = {}
		for ou in ous:
			roles = role_combinations.pop()
			group_dn, group_name = self.create_import_security_group(
				ou_dn=ou.dn,
				allowed_ou_names=[ou.name],
				roles=roles,
				user_dns=[user_dn]
			)
			groups[ou] = {'dn': group_dn, 'roles': roles}

		# add 3rd OU to 2nd group
		self.udm.modify_object(
			'groups/group',
			dn=groups[ous[1]]['dn'],
			append={'ucsschoolImportSchool': [ous[2].name]}
		)
		# so that the roles of the 2nd group are also valid for the 3rd OU
		groups[ous[2]]['roles'].update(groups[ous[1]]['roles'])

		for dn, obj in self.lo.search(filter_format(
				'(&(objectClass=ucsschoolImportGroup)(memberUid=%s))', (username,)
		)):
			self.log.info('%s: %s', dn, pprint.pformat(obj))

		client = Client(username, password, log_level=Client.LOG_RESPONSE)

		self.log.info('*** Checking schools via Python-API...')
		schools = client.school.list()
		expected_schools = set(ou.name for ou in ous)
		received_schools = set(s.name for s in schools)
		self.log.info('Expected schools: %r', expected_schools)
		self.log.info('Received schools: %r', received_schools)
		if expected_schools != received_schools:
			self.fail('expected schools != found schools.')

		self.log.info('*** Checking roles via Python-API...')
		for ou in ous:
			expected_roles = groups[ou]['roles']
			roles_from_api = client.school.get(ou.name).roles
			received_roles = set(r.name for r in roles_from_api)
			self.log.info('Expected roles: %r', expected_roles)
			self.log.info('Received roles: %r', received_roles)
			if expected_roles == received_roles:
				self.log.info('OK.')
			else:
				self.fail('expected roles != found roles.')


if __name__ == '__main__':
	Test().run()
