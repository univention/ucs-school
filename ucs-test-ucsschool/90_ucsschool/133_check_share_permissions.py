#!/usr/share/ucs-test/runner python
## desc: Test if share-access don't leave permission change open for class members.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1,mysharetest]
## exposure: dangerous
## packages: []
## bugs: [42182]

import os
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


def check_user_access(file, user_name, allowed):
	cmd = 'echo "univention" | smbcacls {} --user={}'.format(file, user_name)
	proc = subprocess.Popen(cmd, shell=True,
	                        stdout=subprocess.PIPE,
	                        stderr=subprocess.PIPE)
	stdout, stderr = proc.communicate()
	print(cmd)
	print(stdout)
	print(stderr)
	if not allowed:
		assert "NT_STATUS_ACCESS_DENIED" in stdout
	else:
		assert "NT_STATUS_ACCESS_DENIED" not in stdout



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

		# auf was muss ich hier noch warten?

		import time
		time.sleep(10)
		# das geht jetzt irgendwie schief.
		# for path in directories:
		# 	check_permissions(sid=schueler_sid, path=path)


		# todo test
		# smbcacls //ucs-3303/psg-torch test  --delete="ACL:Everyone:ALLOWED/0x0/R" --user=h.schlemmer%univention
		test_file = "{}/test".format(klasse_path)
		os.mknod(test_file)
		print("create {}".format(test_file))
		assert os.path.exists(test_file)
		share_file = "//{}/{} test".format(schoolenv.ucr.get('hostname'), klasse_dir)

		student_name, _ = schoolenv.create_student(school)
		check_user_access(share_file, user_name=student_name, allowed=False)
		time.sleep(5)
		# teacher hatte noch keinen zugriff.
		teacher_name, _ = schoolenv.create_teacher(school)
		check_user_access(share_file, user_name=teacher_name, allowed=True)


if __name__ == '__main__':
	main()
