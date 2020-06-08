#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Test creation of email addresses from a special email scheme (Bug #44993)
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [44993]

import copy
from ldap.filter import filter_format
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers_cli_v2 import UniqueObjectTester
from univention.testing.ucsschool.importusers import Person


class Test(UniqueObjectTester):
	def __init__(self):
		super(Test, self).__init__()
		self.ou_B = None
		self.ou_C = None

	def test(self):
		"""
		Test creation of email addresses from a special scheme (Bug #44993).
		"""
		config = copy.deepcopy(self.default_config)
		config.update_entry('csv:mapping:record_uid', 'record_uid')
		config.update_entry('csv:mapping:role', '__role')
		config.update_entry('user_role', None)
		del config['csv']['mapping']['E-Mail']

		for scheme in ["ALWAYSCOUNTER", "COUNTER2"]:
			source_uid = 'source_uid-%s' % (uts.random_string(),)
			config.update_entry('source_uid', source_uid)
			config.update_entry(
				'scheme:email',
				'<:umlauts><firstname>[0].<lastname>[{}]@{}'.format(scheme, self.maildomain)
			)
			self.log.info('*** Importing a user of each role and email scheme %r - 1. time', scheme)
			person_list = []
			for role in ('student', 'teacher', 'staff', 'teacher_and_staff'):
				person = Person(self.ou_A.name, role)
				person.update(record_uid=uts.random_name(), source_uid=source_uid, username=None, mail=None)
				person.email_prefix = None
				person_list.append(person)

			fn_csv = self.create_csv_file(person_list=person_list, mapping=config['csv']['mapping'])
			config.update_entry('input:filename', fn_csv)
			fn_config = self.create_config_json(config=config)
			self.save_ldap_status()
			self.run_import(['-c', fn_config, '-i', fn_csv])
			self.check_new_and_removed_users(4, 0)

			for person in person_list:
				person.update_from_ldap(self.lo, ['dn', 'username', 'mail'])
				self.log.debug('person.dn=%r person.username=%r person.mail=%r', person.dn, person.username, person.mail)
				wait_for_drs_replication(filter_format('cn=%s', (person.username,)))
				person.verify()

				person.email_prefix = '{}.{}'.format(person.firstname[0], person.lastname)
				self.log.info("Calculated person.email_prefix is %r.", person.email_prefix)
				self.unique_basenames_to_remove.append(person.email_prefix)
				ext = '1' if scheme == 'ALWAYSCOUNTER' else ''
				person.update(mail='{}{}@{}'.format(person.email_prefix, ext, self.maildomain))
				self.log.debug('person.dn=%r person.username=%r person.mail=%r', person.dn, person.username, person.mail)
				person.verify()
				self.check_unique_obj('unique-email', person.email_prefix, '2')

			for ext in [2, 3]:
				self.log.info('*** Deleting users - %d. time', ext - 1)
				fn_csv = self.create_csv_file(person_list=[], mapping=config['csv']['mapping'])
				config.update_entry('input:filename', fn_csv)
				fn_config = self.create_config_json(config=config)
				self.save_ldap_status()
				self.run_import(['-c', fn_config, '-i', fn_csv])
				utils.wait_for_replication()
				self.check_new_and_removed_users(0, 4)
				for person in person_list:
					person.set_mode_to_delete()
					person.verify()

				self.log.info('*** Importing same users - %d. time', ext)
				for person in person_list:
					person.update(mode='A', username=None, mail=None)
				fn_csv = self.create_csv_file(person_list=person_list, mapping=config['csv']['mapping'])
				config.update_entry('input:filename', fn_csv)
				fn_config = self.create_config_json(config=config)
				self.save_ldap_status()
				self.run_import(['-c', fn_config, '-i', fn_csv])
				utils.wait_for_replication()
				self.check_new_and_removed_users(4, 0)
				for person in person_list:
					person.update_from_ldap(self.lo, ['dn', 'username'])
					person.update(mail='{}{}@{}'.format(person.email_prefix, ext, self.maildomain))
					self.log.debug('person.dn=%r person.username=%r person.mail=%r', person.dn, person.username, person.mail)
					wait_for_drs_replication(filter_format('cn=%s', (person.username,)))
					person.verify()
					self.check_unique_obj('unique-email', person.email_prefix, str(ext + 1))


if __name__ == '__main__':
	Test().run()
