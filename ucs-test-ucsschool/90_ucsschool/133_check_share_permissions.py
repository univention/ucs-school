#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## desc: Test if share-access don't leave permission change open for class members.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-import]
## bugs: [42182]

import os
import re
import tempfile
import time

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.share import ClassShare, MarketplaceShare, WorkGroupShare
from ucsschool.lib.models.utils import exec_cmd
from univention.testing.decorators import SetTimeout


@SetTimeout
def check_deny_nt_acls_permissions(sid, path, allowed=False):  # type: (str, str, bool) -> bool
    rv, stdout, stderr = exec_cmd(
        ["samba-tool", "ntacl", "get", "--as-sddl", path], log=True, raise_exc=True
    )
    if re.match(r".*?(D;OICI.*?;.*?WOWD[^)]+{}).*".format(sid), stdout):
        if allowed:
            utils.fail("The permissions of share {} can not be changed for {}.".format(path, sid))
    elif not allowed:
        utils.fail("The permissions of share {} can be changed for {}.".format(path, sid))
    return True


def change_smbcacls_acls(file, user_name, allowed):  # type: (str, str, bool) -> None
    """
        test if user can change the permissions of a newly created file.
    """
    new_acl = "ACL:Everyone:ALLOWED/OI|CI|I/FULL"
    cmd = "echo 'univention' | smbcacls {} --user={} --add '{}'".format(file, user_name, new_acl)
    rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=False, shell=True)
    if not allowed and "NT_STATUS_ACCESS_DENIED" not in stdout:
        utils.fail(
            "Expected NT_STATUS_ACCESS_DENIED, user could change the permissions: {}".format(stdout)
        )
    elif allowed and "NT_STATUS_ACCESS_DENIED" in stdout:
        utils.fail(
            "Expected user to be able to change the permissions, got NT_STATUS_ACCESS_DENIED: {}".format(
                stdout
            )
        )


def check_create_folder(share, username, dir_name):  # type: (str, str, str) -> str
    """
        this is to make sure the folder is usable.
    """
    cmd = "smbclient -U {}%univention {} -c 'mkdir {}'".format(username, share, dir_name)
    rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=False, shell=True)
    if stderr:
        utils.fail("Failed to create folder inside of share.")
    return dir_name


def test_class_permissions(ucr_hostname, ucr_ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        school, oudn = schoolenv.create_ou(
            use_cache=False, name_edudc=ucr_hostname, name_share_file_server=ucr_hostname
        )

        schueler_group_dn = "cn=schueler-{},cn=groups,{}".format(school, oudn)
        schueler_group_sid = schoolenv.lo.get(schueler_group_dn)["sambaSID"][0]
        lehrer_group_dn = "cn=lehrer-{},cn=groups,{}".format(school, oudn)
        lehrer_group_sid = schoolenv.lo.get(lehrer_group_dn)["sambaSID"][0]
        admin_group_dn = "cn=admins-{},cn=ouadmins,cn=groups,{}".format(school, ucr_ldap_base)
        admin_group_sid = schoolenv.lo.get(admin_group_dn)["sambaSID"][0]

        klasse_name = "{}-{}".format(school, uts.random_string())
        teacher_name, teacher_dn = schoolenv.create_user(
            school, classes=klasse_name, is_teacher=True, is_staff=False
        )
        student_name, student_dn = schoolenv.create_user(
            school, classes=klasse_name, is_teacher=False, is_staff=False
        )
        admin_name, admin_group_dn = schoolenv.create_school_admin(school)
        klasse = SchoolClass(school=school, name=klasse_name)
        klasse.create(schoolenv.lo)
        workgroup_name = "{}-{}".format(school, uts.random_string())
        workgroup = WorkGroup(school=school, users=[teacher_dn, student_dn], name=workgroup_name)
        workgroup.create(schoolenv.lo)

        utils.wait_for_listener_replication()
        klasse_share = ClassShare.from_school_class(klasse)
        klasse_path = klasse_share.get_share_path()
        workgroup_share = WorkGroupShare.from_school_group(workgroup)
        workgroup_path = workgroup_share.get_share_path()
        marketplace_shares = MarketplaceShare.get_all(schoolenv.lo, school=school)
        assert len(marketplace_shares) == 1
        marketplace_path = marketplace_shares[0].get_share_path()

        ready = False
        for i in range(50):
            ready = all(
                [
                    os.path.isdir(klasse_path),
                    os.path.isdir(workgroup_path),
                    os.path.isdir(marketplace_path),
                ]
            )
            if not ready:
                time.sleep(1)
        assert ready

        klasse_share = "//{}/{}".format(ucr_hostname, klasse_share.name)
        klasse_folder = uts.random_string()
        new_klasse_share_folder = "{} {}".format(klasse_share, klasse_folder)
        new_klasse_folder = os.path.join(klasse_path, klasse_folder)

        work_group_share = "//{}/{}".format(ucr_hostname, workgroup_share.name)
        work_group_folder = uts.random_string()
        new_workgroup_share_folder = "{} {}".format(work_group_share, work_group_folder)
        new_workgroup_folder = os.path.join(workgroup_path, work_group_folder)

        marketplace_share = "//{}/Marktplatz".format(ucr_hostname)
        marketplace_folder = uts.random_string()
        marketplace_share_folder = "{} {}".format(marketplace_share, marketplace_folder)
        new_marketplace_folder_path = os.path.join(marketplace_path, marketplace_folder)

        check_create_folder(username=student_name, share=klasse_share, dir_name=klasse_folder)
        check_create_folder(username=teacher_name, share=work_group_share, dir_name=work_group_folder)
        check_create_folder(username=admin_name, share=marketplace_share, dir_name=marketplace_folder)

        nt_acl_cases = [(schueler_group_sid, False), (lehrer_group_sid, True), (admin_group_sid, True)]
        for sid, allowed in nt_acl_cases:
            check_deny_nt_acls_permissions(sid=sid, allowed=allowed, path=klasse_path)
            check_deny_nt_acls_permissions(sid=sid, allowed=allowed, path=workgroup_path)
            check_deny_nt_acls_permissions(sid=sid, allowed=allowed, path=marketplace_path)
            check_deny_nt_acls_permissions(sid=sid, allowed=allowed, path=new_klasse_folder)
            check_deny_nt_acls_permissions(sid=sid, allowed=allowed, path=new_workgroup_folder)
            check_deny_nt_acls_permissions(sid=sid, allowed=allowed, path=new_marketplace_folder_path)

        smbcacls_cases = [(student_name, False), (teacher_name, True), (admin_name, True)]
        for user_name, allowed in smbcacls_cases:
            change_smbcacls_acls(file=new_klasse_share_folder, user_name=user_name, allowed=allowed)
            change_smbcacls_acls(file=new_workgroup_share_folder, user_name=user_name, allowed=allowed)
            change_smbcacls_acls(file=marketplace_share_folder, user_name=user_name, allowed=allowed)

        # rename class and check if the permissions are still the same.
        new_class_name = "{}-{}".format(school, uts.random_string())
        klasse_share = "//{}/{}".format(ucr_hostname, new_class_name)
        new_klasse_share_folder = "{} {}".format(klasse_share, klasse_folder)
        with tempfile.NamedTemporaryFile(suffix=".import", dir="/tmp/") as fp:
            fp.write("{}\t{}".format(klasse.name, new_class_name))
            fp.flush()
            fp.seek(0)
            cmd = ["/usr/share/ucs-school-import/scripts/rename_class", fp.name]
            rv, stdout, stderr = exec_cmd(cmd, log=True, raise_exc=True)
            if rv == 0:
                utils.wait_for_replication_and_postrun()
            klasse = SchoolClass.get_all(
                school=school, lo=schoolenv.lo, filter_str="name={}".format(new_class_name)
            )
            assert len(klasse) == 1
            klasse_share = ClassShare.from_school_class(klasse[0])
            klasse_path = klasse_share.get_share_path()
            for sid, allowed in nt_acl_cases:
                check_deny_nt_acls_permissions(sid=sid, allowed=allowed, path=klasse_path)
            for user_name, allowed in smbcacls_cases:
                change_smbcacls_acls(file=new_klasse_share_folder, user_name=user_name, allowed=allowed)
