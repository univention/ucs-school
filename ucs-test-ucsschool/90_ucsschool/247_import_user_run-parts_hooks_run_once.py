#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Test if run-parts hooks are executed exacly once
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [48141]

import os
import os.path
import sys
import copy
import subprocess
import tempfile
from univention.admin.uexceptions import noObject
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException
from univention.testing.ucsschool.importusers import Person


HOOK_TEXT = """#!/bin/bash

echo "$(date) $@" >> {logfile}
"""
OUTESTHOOKTARGET = '/usr/share/ucs-school-import/hooks/ou_create_post.d/247_hook_test'
USERTESTHOOKTARGET = '/usr/share/ucs-school-import/hooks/user_create_post.d/247_hook_test'


class Test(CLI_Import_v2_Tester):
	ou_B = None
	ou_C = None

	def __init__(self, *args, **kwargs):
		super(Test, self).__init__(*args, **kwargs)
		self.my_ou_name = uts.random_name()
		self.my_ou_dn = 'ou={},{}'.format(self.my_ou_name, self.ucr['ldap/base'])
		_fd, self.ou_hook_log_path = tempfile.mkstemp()
		_fd, self.user_hook_log_path = tempfile.mkstemp()

	def ou_cleanup(self):
		self.run_cmd(['udm', 'container/ou', 'remove', '--ignore_not_exists', '--dn', self.my_ou_dn])
		try:
			objs = self.lo.search(base=self.my_ou_dn, attr=[])
			dns = [x[0] for x in objs]
		except noObject:
			dns = []
		dns.append('cn=admins-{},cn=ouadmins,cn=groups,{}'.format(self.my_ou_name, self.ucr['ldap/base']))
		dns.extend([x[0] for x in self.lo.search('cn=OU{}-*'.format(self.my_ou_name), attr=[])])
		dns = sorted(dns, key=lambda x: x.count(','), reverse=True)
		for dn in dns:
			print('*** Removing {!r}...'.format(dn))
			try:
				self.lo.delete(dn)
			except noObject as exc:
				print('*** {}'.format(exc))

	def hooks_cleanup(self):
		paths = [OUTESTHOOKTARGET, USERTESTHOOKTARGET, self.ou_hook_log_path, self.user_hook_log_path]
		for path in paths:
			try:
				os.remove(path)
				self.log.info('*** Deleted %s.', path)
			except OSError:
				self.log.warn('*** Could not delete %s.', path)

	def cleanup(self):
		self.hooks_cleanup()
		self.ou_cleanup()
		super(Test, self).cleanup()

	def run_cmd(self, cmd):
		self.log.info('Executing command: %r', cmd)
		sys.stdout.flush()
		sys.stderr.flush()
		exitcode = subprocess.call(cmd)
		if exitcode:
			self.fail('Non-zero exit code {!r} from command {!r}.'.format(exitcode, cmd))
		else:
			self.log.info('OK: Process exited with exit code %r.', exitcode)

	def test_ou_create_post_hook(self):
		self.log.info('** Creating ou_create_post shell hook that will log to %r.', self.ou_hook_log_path)
		with open(OUTESTHOOKTARGET, 'w') as fp:
			fp.write(HOOK_TEXT.format(logfile=self.ou_hook_log_path))
		os.chmod(OUTESTHOOKTARGET, 0o755)

		self.log.info('** Creating OU %r...', self.my_ou_name)
		self.run_cmd(['/usr/share/ucs-school-import/scripts/create_ou', '--verbose', self.my_ou_name])

		with open(self.ou_hook_log_path, 'r') as fp:
			log_text = fp.read()
		self.log.info('Content of %r:\n%s', self.ou_hook_log_path, log_text)

		occurences = 0
		self.log.debug('** Looking for lines ening with %r...', self.my_ou_dn)
		for line in log_text.split('\n'):
			if line.endswith(self.my_ou_dn):
				occurences += 1
		if occurences != 1:
			self.fail('Hook called {!r} times, expected 1.'.format(occurences))
		else:
			self.log.info('OK: Hook called %d times.', occurences)

	def test_user_create_post_hook(self):
		self.log.info('** Creating user_create_post shell hook that will log to %r.', self.user_hook_log_path)
		with open(USERTESTHOOKTARGET, 'w') as fp:
			fp.write(HOOK_TEXT.format(logfile=self.user_hook_log_path))
		os.chmod(USERTESTHOOKTARGET, 0o755)

		source_uid = 'source_uid-{}'.format(uts.random_string())
		config = copy.deepcopy(self.default_config)
		config.update_entry('source_uid', source_uid)
		config.update_entry('csv:mapping:Benutzername', 'name')
		person = Person(self.ou_A.name, 'student')
		person.update(source_uid='sourceDB')
		fn_csv = self.create_csv_file(person_list=[person], mapping=config['csv']['mapping'])
		config.update_entry('input:filename', fn_csv)
		fn_config = self.create_config_json(values=config)
		self.run_import(['-c', fn_config])
		utils.verify_ldap_object(person.dn, should_exist=True)
		self.log.debug('** OK: user %r exists.', person.dn)

		with open(self.user_hook_log_path, 'r') as fp:
			log_text = fp.read()
		self.log.info('Content of %r:\n%s', self.user_hook_log_path, log_text)

		occurences = 0
		self.log.debug('** Looking for lines ending with %r...', person.dn)
		for line in log_text.split('\n'):
			if line.endswith(person.dn):
				occurences += 1
		if occurences != 1:
			self.fail('Hook called {!r} times, expected 1.'.format(occurences))
		else:
			self.log.info('OK: Hook called %d times.', occurences)

	def test(self):
		self.test_ou_create_post_hook()
		self.test_user_create_post_hook()


if __name__ == '__main__':
	Test().run()
