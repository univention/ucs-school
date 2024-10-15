#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check permissions of home dirs of exam users during exam
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [49655]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List  # noqa: F401

import PAM
from ldap.filter import escape_filter_chars

import univention.testing.strings as uts
from ucsschool.lib.models.utils import exec_cmd
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.ucs_samba import wait_for_drs_replication, wait_for_s4connector
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.computerroom import (
    CmdCheckFail,
    Room,
    check_change_permissions,
    check_create_share_folder,
    check_share_read,
    check_share_write,
    create_homedirs,
    retry_cmd,
)
from univention.testing.ucsschool.exam import Exam
from univention.testing.umc import Client

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType  # noqa: F401


def set_datatir_immutable_flag(directory: str, flag: bool = True):
    modifier = "+i" if flag else "-i"
    try:
        print(f'# Setting flag "{modifier}" for {directory}')
        subprocess.check_call(["/usr/bin/chattr", modifier, directory])  # nosec
    except subprocess.CalledProcessError:
        raise RuntimeError(f"# Could not set immutable flag on {directory}")


def get_nt_acls(filename):
    rv, stdout, stderr = exec_cmd(
        ["samba-tool", "ntacl", "get", "--as-sddl", filename], log=False, raise_exc=True
    )
    assert stdout is not None
    return stdout.strip()


def _check_for_nt_acl_duplicates(nt_acl_content: str):
    parts = [
        part for part in nt_acl_content.replace(")", "\n").replace("(", "\n").split("\n") if part != ""
    ]
    orig_len = len(parts)
    assert len(set(parts)) == orig_len, f"The given acl does contain duplicate aces: {parts}"


def check_nt_acls(filename):  # type: (str) -> None
    content = get_nt_acls(filename)

    assert re.match(
        r"O:(.+)G:.*\(D;OICI[^;]*;.*?WOWD[^)]+;\1\).*\(A;OICI[^;]*;0x001301bf;;;(S-1-3-4|OW)\)"
        r".*\(A;OICI[^;]*;0x001301bf;;;\1\)",
        content,
    ), "The permissions of share {} can be changed {}".format(filename, content)

    _check_for_nt_acl_duplicates(content)


@retry_cmd
def wait_for_files_to_exist(files):  # type: (List[str]) -> None
    if not all(os.path.exists(folder) for folder in files):
        raise CmdCheckFail("Expected files %r" % (files,))


def check_init_windows_profiles(member_dn_list, lo):  # type: (List[str], LoType) -> None
    for dn in member_dn_list:
        for home_dir in lo.getAttr(dn, "homeDirectory"):
            home_dir = home_dir.decode("UTF-8")
            print("# init_windows_profiles should log in and create files inside {}.".format(home_dir))
            print(os.listdir(home_dir))
            wait_for_files_to_exist(
                [
                    os.path.join(home_dir, "windows-profiles/default.V2"),
                    os.path.join(home_dir, "windows-profiles/default.V3"),
                    os.path.join(home_dir, "windows-profiles/default.V4"),
                    os.path.join(home_dir, "windows-profiles/default.V5"),
                    os.path.join(home_dir, "windows-profiles/default.V6"),
                ]
            )


def check_exam_user_home_dir_permissions(
    member_dn_list, lo, distribution_data_folder
):  # type: (List[str], LoType, str) -> None
    for dn in member_dn_list:
        samba_workstation = lo.getAttr(dn, "sambaUserWorkstations")[0].decode("UTF-8")
        for home_dir in lo.getAttr(dn, "homeDirectory"):
            home_dir = home_dir.decode("UTF-8")
            print("# check nt acls for {} and it's subfolders.".format(home_dir))
            for root, _sub, files in os.walk(home_dir):
                check_nt_acls(root)
                for f in files:
                    check_nt_acls(os.path.join(root, f))

        for samba_home in lo.getAttr(dn, "sambaHomePath"):
            samba_home = samba_home.decode("UTF-8").replace("\\", "/")
            uid = lo.getAttr(dn, "uid")[0].decode("UTF-8")
            new_folder = uts.random_string()
            samba_new_share_folder = "{} {}".format(samba_home, new_folder)
            print(
                "# check if user can create folder {} which inherits the correct rights".format(
                    new_folder
                )
            )
            check_create_share_folder(
                username=uid, share=samba_home, dir_name=new_folder, samba_workstation=samba_workstation
            )
            check_change_permissions(
                filename=samba_new_share_folder,
                user_name=uid,
                allowed=False,
                samba_workstation=samba_workstation,
            )
            new_sub_folder = "{}/{}".format(new_folder, uts.random_string())
            samba_new_share_folder = "{} {}".format(samba_home, new_sub_folder)
            print(
                "# check if user can create sub-folder {} which inherits the correct rights".format(
                    new_sub_folder
                )
            )
            check_create_share_folder(
                username=uid,
                share=samba_home,
                dir_name=new_sub_folder,
                samba_workstation=samba_workstation,
            )
            check_change_permissions(
                filename=samba_new_share_folder,
                user_name=uid,
                allowed=False,
                samba_workstation=samba_workstation,
            )
            print(
                "# check the correct rights on distribution folder: {!r}".format(
                    distribution_data_folder
                )
            )
            exam_share_folder = "{} {}".format(samba_home, distribution_data_folder)
            check_change_permissions(
                filename=exam_share_folder,
                user_name=uid,
                allowed=False,
                samba_workstation=samba_workstation,
            )
            # Since the -i flag is set during the exam-mode, it's not possible to create folders/ files.


def test_exam_mode_home_directories(udm_session, schoolenv, ucr):
    udm = udm_session
    lo = schoolenv.open_ldap_connection()

    print("# create test users and classes")
    if ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = ucr.get("hostname")
    school, oudn = schoolenv.create_ou(name_edudc=edudc, use_cache=False)
    search_base = SchoolSearchBase([school])
    klasse_dn = udm.create_object(
        "groups/group",
        name="%s-AA1" % school,
        position=search_base.classes,
    )

    stu1, studn1 = schoolenv.create_user(school)
    stu2, studn2 = schoolenv.create_user(school)
    tea, teadn = schoolenv.create_user(school, is_teacher=True, password="univention")
    udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn1, studn2, teadn]})

    print("# import random computers")
    computers = Computers(lo, school, 2, 0, 0)
    pc1, pc2 = computers.create()

    print("# set 2 computer rooms to contain the created computers")
    room = Room(school, host_members=pc1.dn)
    schoolenv.create_computerroom(
        school,
        name=room.name,
        description=room.description,
        host_members=room.host_members,
    )

    create_homedirs([studn1, studn2], lo)
    print("# Getting NT acls of teachers home directory")

    try:
        p = PAM.pam()
        p.start("session")
        p.set_item(PAM.PAM_USER, tea)
        p.open_session()
        p.close_session()
    except PAM.error as err:
        raise RuntimeError(err)

    assert os.path.exists(f"/home/{school}/lehrer/{tea}")

    tea_homedir_nt_acls = get_nt_acls(f"/home/{school}/lehrer/{tea}")

    print("# Set an exam and start it")
    current_time = datetime.now()
    chosen_time = current_time + timedelta(hours=2)
    with tempfile.NamedTemporaryFile("w+", suffix=".exam") as f:
        f.write("Temp exam file to upload")
        f.flush()
        exam = Exam(
            school=school,
            room=room.dn,  # room dn
            examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
            recipients=[klasse_dn],  # list of classes dns
            files=[os.path.basename(f.name)],
            connection=Client(username=tea, password="univention"),
        )
        exam.uploadFile(f.name)
    print(f"# Setting immutable flag on {stu1} exam directory.")
    try:
        p = PAM.pam()
        p.start("session")
        p.set_item(PAM.PAM_USER, stu1)
        p.open_session()
        p.close_session()
    except PAM.error as err:
        raise RuntimeError(err)

    os.makedirs(f"/home/{school}/schueler/{stu1}/Klassenarbeiten")
    set_datatir_immutable_flag(f"/home/{school}/schueler/{stu1}/Klassenarbeiten")
    exam.start()

    exam_member_dns = [
        "uid=exam-%s,%s" % (stu1, search_base.examUsers),
        "uid=exam-%s,%s" % (stu2, search_base.examUsers),
    ]
    for uid in [stu1, stu2]:
        username = "exam-{}".format(uid)
        wait_for_drs_replication(
            "(sAMAccountName=%s)" % (escape_filter_chars(username),), attrs="objectSid"
        )
    wait_for_s4connector()

    print("# Checking for changes of NT acls of teachers home directory")
    assert tea_homedir_nt_acls == get_nt_acls(
        f"/home/{school}/lehrer/{tea}"
    ), "NT acls differ from before."
    assert tea_homedir_nt_acls != "", "No NT acls found."
    _check_for_nt_acl_duplicates(tea_homedir_nt_acls)

    print("# create home directories and check permissions")
    create_homedirs(exam_member_dns, lo)
    distribution_data_folder = ucr.get("ucsschool/exam/datadir/recipient", "Klassenarbeiten")
    check_init_windows_profiles(exam_member_dns, lo)
    check_exam_user_home_dir_permissions(exam_member_dns, lo, distribution_data_folder)
    exam_filename = os.path.join(distribution_data_folder, exam.name, "*.exam")
    exam_answer_filename = os.path.join(distribution_data_folder, exam.name, "my.answer")
    print("# check exam permissions for students")
    for uid in [stu1, stu2]:
        username = "exam-{}".format(uid)
        check_share_read(
            username,
            ucr.get("hostname"),
            username,
            passwd="univention",
            filename=exam_filename,
            expected_result=0,
        )
        check_share_write(
            username,
            ucr.get("hostname"),
            username,
            passwd="univention",
            remote_filename=exam_answer_filename,
            expected_result=0,
        )
    exam.collect()
    exam.check_collect()
    print("# check collected exam permissions for teacher")
    for uid in [stu1, stu2]:
        username = "exam-{}".format(uid)
        exam_filename = os.path.join(
            distribution_data_folder, exam.name + "-Ergebnisse", username + "-001", "*.exam"
        )
        exam_answer_filename = os.path.join(
            distribution_data_folder, exam.name + "-Ergebnisse", username + "-001", "my.answer"
        )
        check_share_read(
            tea, ucr.get("hostname"), tea, passwd="univention", filename=exam_filename, expected_result=0
        )
        check_share_read(
            tea,
            ucr.get("hostname"),
            tea,
            passwd="univention",
            filename=exam_answer_filename,
            expected_result=0,
        )
    print("# stopping exam")
    exam.finish()
