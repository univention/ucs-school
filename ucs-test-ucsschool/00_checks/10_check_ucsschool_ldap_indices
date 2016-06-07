#!/usr/share/ucs-test/runner python
## desc: Check if all required LDAP indices for UCS@school are set up
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest,ucsschool]
## exposure: safe
## packages:
##    - ucs-school-master | ucs-school-singlemaster | ucs-school-slave

import univention.config_registry
import univention.testing.utils as utils

EXPECTED_ATTRS = {
	'pres': ['ucsschoolSchool', 'ucsschoolRecordUID', 'ucsschoolSourceUID'],
	'eq': ['ucsschoolSchool', 'ucsschoolRecordUID', 'ucsschoolSourceUID'],
	'sub': ['ucsschoolRecordUID'],
}


def main():
	ucr = univention.config_registry.ConfigRegistry()
	ucr.load()

	for index in ('pres', 'eq', 'sub', 'approx'):
		attr_list = ucr.get('ldap/index/%s' % (index,), '').split(',')
		for expected_attr in EXPECTED_ATTRS.get(index, []):
			if expected_attr not in attr_list:
				print 'ldap/index/%s=%r' % (index, attr_list)
				utils.fail('Expected attribute %r to be found LDAP index ldap/index/%s, but this was not the case.' % (expected_attr, index))
			print 'OK: %r found in ldap/index/%s' % (expected_attr, index)


if __name__ == '__main__':
	main()
