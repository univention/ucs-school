#!/usr/share/ucs-test/runner python
## desc: Test if share-access don't leave permission change open for class members.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1,mysharetest]
## exposure: dangerous
## packages: []
## bugs: [42182]

import re
import subprocess

import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from univention.testing.ucsschool.klasse import Klasse
from univention.testing.ucs_samba import wait_for_s4connector


def main():
	with utu.UCSTestSchool() as schoolenv:
		school, oudn = schoolenv.create_ou()
		klasse = Klasse(school=school)
		klasse.create()
		klasse.check_existence(True)
		wait_for_s4connector()
		group_sid = schoolenv.lo.get(klasse.dn())['sambaSID'][0]
		path = "/home/{0}/groups/klassen/{0}-{1}".format(school, klasse.name)
		proc = subprocess.Popen(['samba-tool', 'ntacl', 'get', '--as-sddl', path], stdout=subprocess.PIPE)
		stdout, stderr = proc.communicate()
		if re.match(r'.*?(A.+?0x001f01ff[^)]+?S-1-5-21.*?).*', stdout):
			# Full control is ok, if it is stripped by the permission to change permissions
			# and take ownership -> WOWD.
			if not re.match(r'.*?(D;OICI;WOWD[^)]+?S-1-5-21.*?).*', stdout):
				utils.fail("The permissions of share {} can be changed for {}.".format(path, group_sid))


if __name__ == '__main__':
	main()
