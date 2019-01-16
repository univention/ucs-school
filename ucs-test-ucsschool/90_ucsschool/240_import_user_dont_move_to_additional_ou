#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Test then when importing into an additional school with alphanum lower name the user is not moved.
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [47450]

import copy

import univention.testing.strings as uts
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester
from univention.testing.ucsschool.importusers import Person


class Test(CLI_Import_v2_Tester):
	ou_C = None

	def test(self):
		source_uid = 'source_uid-%s' % (uts.random_string(),)
		config = copy.deepcopy(self.default_config)
		config.update_entry('csv:mapping:record_uid', 'record_uid')
		config.update_entry('csv:mapping:Benutzername', 'name')
		config.update_entry('csv:mapping:role', '__role')
		config.update_entry('source_uid', source_uid)
		config.update_entry('user_role', None)

		# second_ou has "smaller" name
		# first_ou has "larger" name
		second_ou, first_ou = sorted((self.ou_A.name, self.ou_B.name))
		self.log.info('*** first_ou=%r second_ou=%r', first_ou, second_ou)

		self.log.info('*** Importing a new user of each role into OU %r...', first_ou)
		person_list = []
		for role in ('student', 'teacher', 'staff', 'teacher_and_staff'):
			person = Person(first_ou, role)
			person.update(
				record_uid='record_uid-{}'.format(uts.random_string()),
				source_uid=source_uid
			)
			person_list.append(person)

		fn_config = self.create_config_json(config=config)
		fn_csv = self.create_csv_file(person_list=person_list, mapping=config['csv']['mapping'])
		self.save_ldap_status()
		self.run_import(['-c', fn_config, '-i', fn_csv])
		for person in person_list:
			person.verify()
		self.log.info('OK, all users have been imported into OU %r.', first_ou)

		self.log.info('*** Importing a same users into OU %r...', second_ou)
		for person in person_list:
			person.update(school=first_ou, schools=[first_ou, second_ou])
		fn_config = self.create_config_json(config=config)
		fn_csv = self.create_csv_file(person_list=person_list, mapping=config['csv']['mapping'])
		self.save_ldap_status()
		self.run_import(['-c', fn_config, '-i', fn_csv])
		for person in person_list:
			person.verify()
		self.log.info('OK, all users are still in OU %r and additionally in %r.', first_ou, second_ou)


if __name__ == '__main__':
	Test().run()
