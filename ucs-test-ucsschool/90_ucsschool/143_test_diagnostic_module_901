#!/usr/share/ucs-test/runner python
## desc: Check ucschool import counter diagnose module
## tags: [ucsschool, diagnostic_test]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [50500]

import copy
from ldap.filter import filter_format
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers_cli_v2 import UniqueObjectTester
from univention.testing.ucsschool.importusers import Person

from univention.management.console.config import ucr
from univention.uldap import getAdminConnection
from univention.management.console.modules.diagnostic import Instance, ProblemFixed, Warning, Critical


class Test(UniqueObjectTester):
	def __init__(self):
		super(Test, self).__init__()
		self.ou_B = None

	def test(self):
		"""
		Test creation of email addresses from a special scheme (Bug #44993).
		"""
		config = copy.deepcopy(self.default_config)
		config.update_entry('csv:mapping:record_uid', 'record_uid')
		config.update_entry('csv:mapping:role', '__role')
		config.update_entry('user_role', None)
		del config['csv']['mapping']['E-Mail']
		scheme = "COUNTER2"
		# The module searches for all users with an ucsschoolRole:
		# '(&(univentionObjectType=users/user)(ucsschoolRole=*))'
		# so it suffices to only check against one.
		role = 'student'
		source_uid = 'source_uid-%s' % (uts.random_string(),)
		config.update_entry('source_uid', source_uid)
		self.log.info('*** Importing a user of each role and email scheme ', scheme)
		config.update_entry(
			'scheme:email',
			'<:umlauts><firstname>[0].<lastname>[{}]@{}'.format(scheme, self.maildomain)
		)
		config.update_entry(
			'scheme:username:default',
			'<:umlauts><firstname>[0].<lastname>[{}]'.format(scheme)
		)
		person_list = []
		for i in range(6):
			person = Person(self.ou_A.name, role)
			person.update(record_uid=uts.random_name(), source_uid=source_uid, username=None, mail=None)
			person.email_prefix = None
			person_list.append(person)

		fn_csv = self.create_csv_file(person_list=person_list, mapping=config['csv']['mapping'])
		config.update_entry('input:filename', fn_csv)
		fn_config = self.create_config_json(config=config)
		self.save_ldap_status()
		self.run_import(['-c', fn_config, '-i', fn_csv])
		self.check_new_and_removed_users(6, 0)
		for person in person_list:
			person.update_from_ldap(self.lo, ['dn', 'username', 'mail'])
			self.log.debug('person.dn=%r person.username=%r person.mail=%r', person.dn, person.username, person.mail)
			wait_for_drs_replication(filter_format('cn=%s', (person.username,)))
			person.verify()

		for person in person_list:
			person.update_from_ldap(self.lo, ['dn', 'username', 'mail'])
			self.log.debug('person.dn=%r person.username=%r person.mail=%r', person.dn, person.username, person.mail)
			wait_for_drs_replication(filter_format('cn=%s', (person.username,)))
			person.verify()

			person.email_prefix = '{}.{}'.format(person.firstname[0], person.lastname)
			self.log.info("Calculated person.email_prefix is %r.", person.email_prefix)
			self.unique_basenames_to_remove.append(person.email_prefix)
			person.update(mail='{}{}@{}'.format(person.email_prefix, '', self.maildomain))
			self.log.debug('person.dn=%r person.username=%r person.mail=%r', person.dn, person.username, person.mail)
			person.verify()
			self.check_unique_obj('unique-email', person.email_prefix, '2')

			person.username_prefix = '{}.{}'.format(person.firstname[0], person.lastname)
			self.log.info("Calculated person.username_prefix is %r.", person.username_prefix)
			self.unique_basenames_to_remove.append(person.username_prefix)
			if person.username != "{}{}".format(person.username_prefix, ""):
				self.fail('username %r is not expected string "%s%s"' % (person.username, person.username_prefix, "1" if scheme == "ALWAYSCOUNTER" else ""))
			self.log.info('Username %r is expected with string "%s%s"', person.username, person.username_prefix, "1" if scheme == "ALWAYSCOUNTER" else "")
			self.check_unique_obj('unique-usernames', person.username_prefix, '2')

		# Change ldap-values, such that the diagnose-modul should raise a warning.
		expected_warnings =[]
		for i, person in enumerate(person_list):
			if i == 0:
				new_mail = '{}{}@{}'.format(person.email_prefix, 3, self.maildomain)
				new_uid = '{}{}'.format(person.username_prefix, 3)
				change = [('mailPrimaryAddress', person.mail, new_mail)]
				obj_dn = person.dn
				expected_warnings.append("cn={0},cn=unique-email,cn=ucsschool,cn=univention,{1}: email counter='2' but found user with uid {2}".format(person.username, ucr.get('ldap/base'), new_uid))
			elif i == 1:
				new_uid = '{}{}'.format(person.username_prefix, 3)
				change = [('uid', person.username, new_uid)]
				obj_dn = person.dn
				expected_warnings.append("cn={0},cn=unique-usernames,cn=ucsschool,cn=univention,{1}: usernames counter='2' but found user with uid {2}".format(person.username, ucr.get('ldap/base'), new_uid))
			else:
				unique_obj = 'unique-email' if i % 2 == 0 else 'unique-usernames'
				if i < 4:
					new_value = ['0']
					expected_warnings.append("cn={},cn={},cn=ucsschool,cn=univention,{}: counter='0'".format(person.username, unique_obj,ucr.get('ldap/base')))
				else:
					new_value = []
					expected_warnings.append("cn={},cn={},cn=ucsschool,cn=univention,{}: counter=''".format(person.username, unique_obj,ucr.get('ldap/base')))
				obj_list = self.lo.searchDn(
					base='cn={},cn=ucsschool,cn=univention,{}'.format(unique_obj,ucr.get('ldap/base')),
					filter='cn={}'.format(person.username), scope='one')
				obj_dn = obj_list[0]
				change = [('ucsschoolUsernameNextNumber', ['2'], new_value)]

			self.lo.modify(obj_dn, change)
			self.log.info('change {}: {}'.format(obj_dn,change))

		# Run diagnostic tool, capture and test if exceptions were thrown.
		module_name = '901_ucsschool_import_counter'
		instance = Instance()
		instance.init()
		module = instance.get(module_name)
		out = None
		try:
			out = module.execute(None)
		except Critical:
			pass

		assert out and out['success'] is False
		for warning in expected_warnings:
			if warning.strip() not in out['description']:
				raise Exception('diagnostic tool {} did not raise warning {}!\n'.format(module_name, warning))
		self.log.info('Ran diagnostic tool {} successfully.'.format(module_name))

if __name__ == '__main__':
	Test().run()