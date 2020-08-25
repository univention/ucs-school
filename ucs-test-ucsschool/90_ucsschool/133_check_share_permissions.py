#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## desc: Test if share-access don"t leave permission change open for class members.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1,mysharetest]
## exposure: dangerous
## packages: []
## bugs: [42182]

import os
import re
import subprocess

import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from univention.management.console.config import ucr
from univention.testing.ucsschool.klasse import Klasse
from univention.testing.ucsschool.workgroup import Workgroup


def check_permissions(sid, path, allowed=False):
    # test if listener works. for this we need the sid of the pupils
    # and the sid of the teachers.
    # todo replace with exec_cmd
    proc = subprocess.Popen(["samba-tool", "ntacl", "get", "--as-sddl", path], stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if stderr and allowed:
        utils.fail("Error during samba-tool execution {}".format(stderr))
    elif not allowed:
        return True
    # Full control is ok, if it is stripped by the permission to change permissions
    # and take ownership -> WOWD.
    if not re.match(r".*?(D;OICI;.*?WOWD[^)]+{}).*".format(sid), stdout) and not allowed:
        print(stdout)
        utils.fail("The permissions of share {} can be changed for {}.".format(path, sid))
    return True


def check_user_access(file, user_name, allowed):
    cmd = "echo 'univention' | smbcacls {} --user={}".format(file, user_name)
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    print(cmd)
    print(stdout)
    print(stderr)
    if not allowed:
        assert "NT_STATUS_ACCESS_DENIED" in stdout
    else:
        assert "NT_STATUS_ACCESS_DENIED" not in stdout


def test_class_permissions(ucr_hostname):
    with utu.UCSTestSchool() as schoolenv:
        school, oudn = schoolenv.create_ou(use_cache=False, name_edudc=ucr_hostname)
        klasse = Klasse(school=school)
        klasse.create()
        klasse_dir = "{0}-{1}".format(school, klasse.name)
        # todo -> ggf. nicht ueberall aufrufen.
        # auf .50 liegt das auf dem schulserver.
        klasse_path = "/home/{0}/groups/klassen/{1}".format(school, klasse_dir)

        # sids for listener-test
        schueler_dn = "cn=schueler-{},cn=groups,{}".format(school, oudn)
        schueler_sid = schoolenv.lo.get(schueler_dn)["sambaSID"][0]
        lehrer_dn = "cn=lehrer-{},cn=groups,{}".format(school, oudn)
        lehrer_sid = schoolenv.lo.get(lehrer_dn)["sambaSID"][0]
        admin_dn = "cn=admins-{},cn=ouadmins,cn=groups,{}".format(school, oudn)
        # fails?
        # admin_sid = schoolenv.lo.get(admin_dn)["sambaSID"][0]

        workgroup = Workgroup(school=school)
        workgroup.create()
        workgroup_dir = "{0}-{1}".format(school, workgroup.name)
        workgroup_path = "/home/{0}/groups/{1}".format(school, workgroup_dir)

        student_name, student_dn = schoolenv.create_student(school)
        teacher_name, teacher_dn = schoolenv.create_teacher(school)
        workgroup.set_members([student_dn, teacher_dn])

        utils.wait_for_listener_replication()
        assert os.path.isdir("/home/{0}".format(school))

        test_file = "{}/test".format(klasse_path)
        os.mknod(test_file)
        print("create {}".format(test_file))
        assert os.path.exists(test_file)

        check_permissions(schueler_sid, allowed=False, path=test_file)
        check_permissions(lehrer_sid, allowed=True, path=test_file)
        # check_permissions(admin_sid, allowed=True, path=test_file)

        share_file = "//{}/{} test".format(ucr_hostname, klasse_dir)
        check_user_access(share_file, user_name=student_name, allowed=False)
        check_user_access(share_file, user_name=teacher_name, allowed=True)
        # check_user_access(share_file, user_name=admin_name, allowed=True)

        test_file = "{}/test".format(workgroup_path)
        os.mknod(test_file)
        print("create {}".format(test_file))
        assert os.path.exists(test_file)
        share_file = "//{}/{} test".format(ucr_hostname, workgroup_dir)
        check_user_access(share_file, user_name=student_name, allowed=False)
        # check_user_access(share_file, user_name=teacher_name, allowed=True)
        # check_user_access(share_file, user_name=admin_name, allowed=True)

        check_permissions(schueler_sid, allowed=False, path=test_file)
        check_permissions(lehrer_sid, allowed=True, path=test_file)
        # check_permissions(admin_sid, allowed=True, path=test_file)

        marketplace_dir = "Marktplatz"
        marketplace_path = "/home/{0}/groups/{1}".format(school, marketplace_dir)
        test_file = "{}/test".format(marketplace_path)
        os.mknod(test_file)
        print("create {}".format(test_file))
        assert os.path.exists(test_file)
        share_file = "//{}/{} test".format(ucr_hostname, marketplace_dir)
        # check_user_access(share_file, user_name=student_name, allowed=False)
        # check_user_access(share_file, user_name=teacher_name, allowed=True)

        # check_permissions(schueler_sid, allowed=False, path=test_file)
        # check_permissions(lehrer_sid, allowed=True, path=test_file)
        # check_permissions(admin_sid, allowed=True, path=test_file)
