#!/usr/share/ucs-test/runner python
## desc: Test if share-access don't leave permission change open for class members.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1,mysharetest]
## exposure: dangerous
## packages: []
## bugs: [42182]

import re
import subprocess

from univention.management.console.config import ucr
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from univention.testing.ucsschool.klasse import Klasse
from univention.testing.ucsschool.workgroup import Workgroup


def check_permissions(sid, path, allowed=False):
	proc = subprocess.Popen(['samba-tool', 'ntacl', 'get', '--as-sddl', path],
	                        stdout=subprocess.PIPE)
	stdout, stderr = proc.communicate()
	if stderr and allowed:
		utils.fail("Error during samba-tool execution {}".format(stderr))
	elif not allowed:
		return True
	# Full control is ok, if it is stripped by the permission to change permissions
	# and take ownership -> WOWD.
	if not re.match(r'.*?(D;OICI;.*?WOWD[^)]+{}).*'.format(sid), stdout):
		utils.fail("The permissions of share {} can be changed for {}.".format(path, sid))
	return True


def main():
	with utu.UCSTestSchool() as schoolenv:
		directories = []
		school, oudn = schoolenv.create_ou()
		klasse = Klasse(school=school)
		klasse.create()
		klasse_dir = "{0}-{1}".format(school, klasse.name)
		klasse_path = "/home/{0}/groups/klassen/{1}".format(school, klasse_dir)
		directories.append(klasse_path)
		schueler_dn = 'cn=schueler-{},cn=groups,{}'.format(school, oudn)
		schueler_sid = schoolenv.lo.get(schueler_dn)['sambaSID'][0]

		workgroup = Workgroup(school=school)
		workgroup.create()
		workgroup_dir = "{0}-{1}".format(school, workgroup.name)
		workgroup_path = "/home/{0}/groups/{0}-{1}".format(school, workgroup_dir)
		directories.append(workgroup_path)

		utils.wait_for_listener_replication()
		import time

		# das geht jetzt irgendwie schief.
		# for path in directories:
		# 	check_permissions(sid=schueler_sid, path=path)

		# setfacl with user
		# setfacl -m "user:h.schlemmer:--" /home/psg/groups/klassen/psg-hmhm

		user_name, user_dn = schoolenv.create_student(school)
		import os

		# smbcacls //ucs-3303/psg-torch test   --user=h.schlemmer%univention
		# smbcacls //ucs-3303/psg-torch test  --delete="ACL:Everyone:ALLOWED/0x0/R" --user=h.schlemmer%univention
		# Failed to open \test: NT_STATUS_ACCESS_DENIED
		# touch test file
		test_file = "{}/test".format(klasse_path)
		os.mknod(test_file)
		assert os.path.exists(test_file)
		share_file = "//{}/{} test".format(schoolenv.ucr.get('hostname'), klasse_dir)
		# share does not exist?
		cmd = 'echo "univention" | smbcacls {} --user={}'.format(share_file, user_name)
		print(cmd)
		proc = subprocess.Popen(cmd, shell=True,
		                        stdout=subprocess.PIPE,
		                        stderr=subprocess.PIPE)
		stdout, stderr = proc.communicate()

		print("#"*10)
		print(stdout)
		print('#'*10)
		print(stderr)
		print('#'*10)



if __name__ == '__main__':
	main()
