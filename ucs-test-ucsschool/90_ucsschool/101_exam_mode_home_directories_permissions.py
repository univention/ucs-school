#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Check permissions of home dirs of exam users during exam
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [49655]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

import re
from datetime import datetime, timedelta

from ldap.filter import escape_filter_chars

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm
import univention.testing.utils as utils
from ucsschool.lib.models.utils import exec_cmd
from univention.testing.ucs_samba import wait_for_drs_replication, wait_for_s4connector
from univention.testing.ucsschool.computerroom import (
    Computers,
    Room,
    check_change_permissions,
    check_create_folder,
    create_homedirs,
)
from univention.testing.ucsschool.exam import Exam


def test_permissions(member_dn_list, open_ldap_co):
    for dn in member_dn_list:
        samba_workstation = open_ldap_co.getAttr(dn, "sambaUserWorkstations")
        for home_dir in open_ldap_co.getAttr(dn, "homeDirectory"):
            rv, stdout, stderr = exec_cmd(
                ["samba-tool", "ntacl", "get", "--as-sddl", home_dir], log=True, raise_exc=True
            )
            if (
                not re.match(r"O:([^:]+).*?(D;OICI.*?;.*?WOWD[^)]+\1).*", stdout)
                or "(A;OICI;0x001301bf;;;S-1-3-4)" not in stdout
            ):
                utils.fail("The permissions of share {} can be changed for {}.".format(home_dir, dn))
        for samba_home in open_ldap_co.getAttr(dn, "sambaHomePath"):
            samba_home = samba_home.replace("\\", "/")
            samba_workstation = samba_workstation[0]
            uid = open_ldap_co.getAttr(dn, "uid")[0]
            new_folder = uts.random_string()
            samba_new_share_folder = "{} /".format(samba_home, new_folder)
            check_create_folder(
                username=uid, share=samba_home, dir_name=new_folder, samba_workstation=samba_workstation
            )
            check_change_permissions(
                file=samba_new_share_folder,
                user_name=uid,
                allowed=False,
                samba_workstation=samba_workstation,
            )


def main():
    with univention.testing.udm.UCSTestUDM() as udm, utu.UCSTestSchool() as schoolenv, ucr_test.UCSTestConfigRegistry() as ucr:
        open_ldap_co = schoolenv.open_ldap_connection()
        ucr.load()

        print("# create test users and classes")
        if ucr.is_true("ucsschool/singlemaster"):
            edudc = None
        else:
            edudc = ucr.get("hostname")
        school, oudn = schoolenv.create_ou(name_edudc=edudc)
        klasse_dn = udm.create_object(
            "groups/group",
            name="%s-AA1" % school,
            position="cn=klassen,cn=schueler,cn=groups,%s" % oudn,
        )

        stu1, studn1 = schoolenv.create_user(school)
        stu2, studn2 = schoolenv.create_user(school)
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn1, studn2]})

        print("# import random computers")
        computers = Computers(open_ldap_co, school, 2, 0, 0)
        pc1, pc2 = computers.create()

        print("# set 2 computer rooms to contain the created computers")
        room = Room(school, host_members=pc1.dn)
        schoolenv.create_computerroom(
            school, name=room.name, description=room.description, host_members=room.host_members,
        )

        create_homedirs([studn1, studn2], open_ldap_co)
        print("# Set an exam and start it")
        current_time = datetime.now()
        chosen_time = current_time + timedelta(hours=2)
        exam = Exam(
            school=school,
            room=room.dn,  # room dn
            examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
            recipients=[klasse_dn],  # list of classes dns
        )
        exam.start()

        exam_member_dns = [
            "uid=exam-%s,cn=examusers,%s" % (stu1, oudn),
            "uid=exam-%s,cn=examusers,%s" % (stu2, oudn),
        ]
        for uid in [stu1, stu2]:
            username = "exam-{}".format(uid)
            wait_for_drs_replication(
                "(sAMAccountName=%s)" % (escape_filter_chars(username),), attrs="objectSid"
            )
        wait_for_s4connector()
        print("# create home directories and check permissions")
        create_homedirs(exam_member_dns, open_ldap_co)
        test_permissions(exam_member_dns, open_ldap_co)
        print("# stopping exam")
        exam.finish()


if __name__ == "__main__":
    main()
