#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Test ResultPyHooks
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [47302]

import re
import os
import os.path
import copy
import random
import shutil

from ldap.filter import escape_filter_chars
import univention.testing.strings as uts
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucs_samba import wait_for_drs_replication


TESTHOOKSOURCE = os.path.join(os.path.dirname(__file__), 'test241_result_pyhookpy')
TESTHOOKTARGET = '/usr/share/ucs-school-import/pyhooks/test241_result_pyhook.py'
RESULTFILE = '/tmp/test241result.txt'


class Test(CLI_Import_v2_Tester):
	ou_B = None
	ou_C = None

	def pyhook_cleanup(self):
		for ext in ['', 'c', 'o']:
			path = '{}{}'.format(TESTHOOKTARGET, ext)
			try:
				os.remove(path)
				self.log.info('*** Deleted %s.', path)
			except OSError:
				self.log.warn('*** Could not delete %s.', path)

	def cleanup(self):
		self.pyhook_cleanup()
		try:
			os.remove(RESULTFILE)
			self.log.info('*** Deleted %s.', RESULTFILE)
		except OSError:
			self.log.warn('*** Could not delete %s.', RESULTFILE)
		super(Test, self).cleanup()

	def test(self):
		source_uid = 'source_uid-{}'.format(uts.random_string())
		config = copy.deepcopy(self.default_config)
		config.update_entry('csv:mapping:Benutzername', 'name')
		config.update_entry('csv:mapping:record_uid', 'record_uid')
		config.update_entry('csv:mapping:role', '__role')
		config.update_entry('source_uid', source_uid)
		config.update_entry('user_role', None)

		roles = ('staff', 'student', 'teacher', 'teacher_and_staff')
		user_num = dict((role, random.randint(1, 4)) for role in roles)
		_roles = user_num.keys()
		random.shuffle(_roles)  # moar random
		roles1 = dict((k, user_num[k]) for k in _roles[:2])
		roles2 = dict((k, user_num[k]) for k in _roles[1:])  # overlap 1

		person_list1 = list()
		person_list2 = list()
		for role, num in roles1.items():
			for _ in range(num):
				person = Person(self.ou_A.name, role)
				person.update(
					record_uid='record_uid-{}'.format(uts.random_string()),
					source_uid=source_uid,
				)
				person_list1.append(person)
				if role in roles2:
					# role will be imported twice
					person_list2.append(person)
		for role, num in roles2.items():
			if role in roles1:
				continue  # don't add a 2nd time
			for _ in range(num):
				person = Person(self.ou_A.name, role)
				person.update(
					record_uid='record_uid-{}'.format(uts.random_string()),
					source_uid=source_uid,
				)
				person_list2.append(person)

		self.log.info('*** Importing users without ResultPyHook: {!r}'.format(roles1))
		fn_csv = self.create_csv_file(person_list=person_list1, mapping=config['csv']['mapping'])
		config.update_entry('input:filename', fn_csv)
		fn_config = self.create_config_json(values=config)
		self.run_import(['-c', fn_config])
		wait_for_drs_replication('cn={}'.format(escape_filter_chars(person_list1[-1].username)))

		self.log.info('Creating PyHook %r...', TESTHOOKTARGET)
		shutil.copy(TESTHOOKSOURCE, TESTHOOKTARGET)

		self.log.info('*** Importing users with ResultPyHook: {!r}'.format(roles2))
		fn_csv = self.create_csv_file(person_list=person_list2, mapping=config['csv']['mapping'])
		config.update_entry('input:filename', fn_csv)
		fn_config = self.create_config_json(values=config)
		self.run_import(['-c', fn_config], fail_on_preexisting_pyhook=False)

		def added(role):
			return user_num[role] if role not in roles1 and role in roles2 else 0

		def modified(role):
			return user_num[role] if role in roles1 and role in roles2 else 0

		def deleted(role):
			return user_num[role] if role in roles1 and role not in roles2 else 0

		expected_result = [
			r'^errors=0$',
		]
		for role in roles:
			expected_result.append(r'^added_{}={}$'.format(role, added(role)))
		for role in ('staff', 'student', 'teacher', 'teacher_and_staff'):
			expected_result.append(r'^modified_{}={}$'.format(role, modified(role)))
		for role in ('staff', 'student', 'teacher', 'teacher_and_staff'):
			expected_result.append(r'^deleted_{}={}$'.format(role, deleted(role)))
		self.log.debug('expected_result:\n%s', '\n'.join(expected_result))

		for num, line in enumerate(open(RESULTFILE, 'rb')):
			if re.match(expected_result[num], line):
				self.log.debug('OK: {!r}'.format(line.strip('\n')))
			else:
				self.fail('Expected {!r} found {!r}.'.format(expected_result[num], line))


if __name__ == '__main__':
	Test().run()
