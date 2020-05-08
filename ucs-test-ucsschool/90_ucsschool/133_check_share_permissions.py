#!/usr/share/ucs-test/runner python
## desc: Test if share-access don't leave permission change open for class members.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: []
## bugs: [42182]

import re
import subprocess
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models import School, Share


def main():
	with utu.UCSTestSchool() as schoolenv:
		for school in School.get_all(schoolenv.lo):
			for share in Share.get_all(schoolenv.lo, school.name):
				share_udm = share.get_udm_object(schoolenv.lo)
				if share.name in ["Marktplatz", "iTALC-Installation"]:
					print("*** Ignoring //{}/{} (Bug #42514)".format(school.name, share.name))
				else:
					# better test -> if permissions can be altered
					proc = subprocess.Popen(['samba-tool', 'ntacl', 'get', '--as-sddl', share_udm["path"]], stdout=subprocess.PIPE)
					stdout, stderr = proc.communicate()
					sid_map = [
						('S-1-1-0', 'everyone'),
						('S-1-5-21', 'group'),
					]
					for sid, name in sid_map:
						if re.match(r'.*?(A.+?0x001f01ff[^)]+?{}.*?).*'.format(sid), stdout):
							# Full control is ok, if it is stripped by the permission to change permissions.
							if not re.match(r'.*?(D.+?0x00140000[^)]+?{}.*?).*'.format(sid), stdout):
								utils.fail("The permissions of share {} can be changed.".format(share_udm["path"], name))


if __name__ == '__main__':
	main()
