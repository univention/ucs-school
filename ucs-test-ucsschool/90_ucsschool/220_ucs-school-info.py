#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: simple test run of ucs-school-info
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master,domaincontroller_backup,domaincontroller_slave]
## exposure: safe
## packages:
##   - ucs-school-info

import subprocess
from univention.uldap import getMachineConnection
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils


def main():
	with ucr_test.UCSTestConfigRegistry() as ucr:
		lo = getMachineConnection()
		for dn, ou_attrs in lo.search(
			base=ucr['ldap/base'],
			filter='(objectClass=ucsschoolOrganizationalUnit)',
			scope='one',
			attr=['ou']
		):
			cmd = ['ucs-school-info', '-a', ou_attrs['ou'][0]]
			exitcode = subprocess.call(cmd)
			if exitcode:
				utils.fail('"%s" returned with non-zero exitcode! (%s)' % (' '.join(cmd)), dn)

if __name__ == '__main__':
	main()
