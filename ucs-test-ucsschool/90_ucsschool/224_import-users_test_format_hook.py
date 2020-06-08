#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: test FormatPyHook
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [42144, 45524]

import os
import sys
import copy
import random
import shutil
import datetime
from ldap.filter import escape_filter_chars
import univention.testing.strings as uts
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester
from univention.testing.ucsschool.importusers import Person


TESTHOOKSOURCE = CONFIG = os.path.join(os.path.dirname(__file__), 'testformathookpy')
TESTHOOKTARGET = '/usr/share/ucs-school-import/pyhooks/testformathook.py'


class Test(CLI_Import_v2_Tester):
	ou_B = None
	ou_C = None

	def __init__(self):
		super(Test, self).__init__()
		self.log.info('*** Copying %r to %r...', TESTHOOKSOURCE, TESTHOOKTARGET)
		shutil.copy2(TESTHOOKSOURCE, TESTHOOKTARGET)
		sys.path.append('/usr/share/ucs-school-import/pyhooks/')

	def cleanup(self):
		for ext in ['', 'c', 'o']:
			path = '{}{}'.format(TESTHOOKTARGET, ext)
			try:
				os.remove(path)
				self.log.info('*** Deleted %s.', path)
			except OSError:
				self.log.warn('*** Could not delete %s.', path)
		super(Test, self).cleanup()

	def test(self):
		"""
		Bug #42144 / #45524: create users and check if the FormatTestPyHook did do its job.
		"""
		source_uid = 'source_uid-{}'.format(uts.random_string())
		config = copy.deepcopy(self.default_config)
		config.update_entry('csv:mapping:Benutzername', 'name')
		config.update_entry('csv:mapping:record_uid', 'record_uid')
		config.update_entry('csv:mapping:role', '__role')
		# No csv:mapping:birthday, so the birthday attribute is empty. This
		# will in ImportUser.make_birthday() trigger format_from_scheme().
		config.update_entry('scheme:birthday', '<firstname>')  # create birthday attribute from firstname value
		config.update_entry('scheme:email', '<:umlauts><firstname:lower>.<lastname:lower>@<maildomain>'),
		config.update_entry('source_uid', source_uid)
		config.update_entry('user_role', None)
		del config['csv']['mapping']['E-Mail']

		self.log.info('Importing a user from each role...')
		person_list = list()
		for role in ('student', 'teacher', 'staff', 'teacher_and_staff'):
			person = Person(self.ou_A.name, role)
			record_uid = 'record_uid-%s' % (uts.random_string(),)
			person.update(
				record_uid=record_uid,
				source_uid=source_uid,
				# write date in correct format (%Y-%m-%d) into firstname
				firstname='{}-{:02}-{:02}'.format(random.randint(1900, 2016), random.randint(1, 12), random.randint(1, 27)),
				lastname=uts.random_username(),
				mail=None  # emtpy, so that it will be generated from scheme
			)
			if person.role in ('staff', 'student'):
				person._bday = person.firstname
				# Rewrite date in _wrong_ format (e.g. 17.8.2000 -> 17.aug.2000).
				# If a format hook does not fix this value, the import will
				# fail, because UDM will reject it as invalid date.
				person.update(firstname=datetime.datetime.strptime(person.firstname, '%Y-%m-%d').strftime('%Y.%b.%d'))
			person_list.append(person)
		fn_csv = self.create_csv_file(person_list=person_list, mapping=config['csv']['mapping'])
		config.update_entry('input:filename', fn_csv)
		fn_config = self.create_config_json(values=config)
		self.save_ldap_status()
		self.run_import(['-c', fn_config], fail_on_preexisting_pyhook=False)
		wait_for_drs_replication('cn={}'.format(escape_filter_chars(person_list[-1].username)))
		self.check_new_and_removed_users(4, 0)

		for person in person_list:
			# The format hook for generaing the email attribute should have
			# removed all vowels from the lastname of these three roles.
			if person.role in ('student', 'teacher', 'teacher_and_staff'):
				lastname = person.lastname.translate(None, 'aeiou')
			else:
				# staffs lastname was not modified
				lastname = person.lastname
			# email will be generated as configured above in scheme:email, but
			# with the modified lastname
			email_local = '{}.{}'.format(person.firstname, lastname).lower()
			person.update(mail='{}@{}'.format(email_local, self.maildomain))
			if person.role in ('staff', 'student'):
				person.update(birthday=person._bday)
			else:
				person.update(birthday=person.firstname)
			person.verify()
		self.log.info('*** OK: All %r users were created correctly.', len(person_list))


if __name__ == '__main__':
	Test().run()
