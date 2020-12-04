#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Check the consistency of exam users in unix, ldap and the ownership of their home directories
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [52307]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

import os
import pwd
from datetime import datetime, timedelta

from ldap.filter import filter_format

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm
import univention.testing.utils as utils
from ucsschool.lib.models import Student
from univention.testing.ucs_samba import wait_for_drs_replication, wait_for_s4connector
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.ucsschool.exam import Exam


def check_uids(member_dn_list, open_ldap_co):
    # check that the uids in ldap, unix and home dir ownership are consistent
    for dn in member_dn_list:
        user_name = open_ldap_co.getAttr(dn, "uid")[0]
        ldap_uid = str(open_ldap_co.getAttr(dn, "uidNumber")[0])
        unix_uid = str(pwd.getpwnam(user_name).pw_uid)
        for homedir in open_ldap_co.getAttr(dn, "homeDirectory"):
            if not os.path.exists(homedir):
                utils.fail("homeDirectory {} for {} does not exist".format(homedir, dn))
            dir_owner = str(os.stat(homedir).st_uid)
            if not (ldap_uid == unix_uid == dir_owner):
                utils.fail(
                    "uids of ldap object ({}), unix ({}) and home directory ownership ({}) are not "
                    "consistent!".format(ldap_uid, unix_uid, dir_owner)
                )


def main():
    with univention.testing.udm.UCSTestUDM() as udm:
        with utu.UCSTestSchool() as schoolenv:
            with ucr_test.UCSTestConfigRegistry() as ucr:
                open_ldap_co = schoolenv.open_ldap_connection()
                ucr.load()

                print "# create test users and classes"
                if ucr.is_true("ucsschool/singlemaster"):
                    edudc = None
                else:
                    edudc = ucr.get("hostname")
                school, oudn = schoolenv.create_ou(name_edudc=edudc, use_cache=False)
                klasse_dn = udm.create_object(
                    "groups/group",
                    name="%s-AA1" % school,
                    position="cn=klassen,cn=schueler,cn=groups,%s" % oudn,
                )
                tea, teadn = schoolenv.create_user(school, is_teacher=True)
                stu, studn = schoolenv.create_user(school)
                wait_for_drs_replication(filter_format("cn=%s", (stu,)))
                student2 = Student(
                    name=uts.random_username(),
                    school=school,
                    firstname=uts.random_name(),
                    lastname=uts.random_name(),
                )
                student2.position = "cn=users,%s" % ucr["ldap/base"]
                student2.create(open_ldap_co)
                udm.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
                udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})
                udm.modify_object("groups/group", dn=klasse_dn, append={"users": [student2.dn]})
                wait_for_drs_replication(filter_format("cn=%s", (student2.name,)))

                print "# import random computers"
                computers = Computers(open_ldap_co, school, 2, 0, 0)
                pc1, pc2 = computers.create()

                print "# set 2 computer rooms to contain the created computers"
                room1 = Room(school, host_members=pc1.dn)
                room2 = Room(school, host_members=pc2.dn)
                for room in [room1, room2]:
                    schoolenv.create_computerroom(
                        school,
                        name=room.name,
                        description=room.description,
                        host_members=room.host_members,
                    )

                print "# Set an exam and start it"
                current_time = datetime.now()
                chosen_time = current_time + timedelta(hours=2)
                exam = Exam(
                    school=school,
                    room=room2.dn,  # room dn
                    examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
                    recipients=[klasse_dn],  # list of classes dns
                )
                exam.start()

                exam_member_dns = [
                    "uid=exam-%s,cn=examusers,%s" % (stu, oudn),
                    "uid=exam-%s,cn=examusers,%s" % (student2.name, oudn),
                ]

                check_uids(exam_member_dns, open_ldap_co)

                print "# stopping exam"
                exam.finish()

                print "# Set another exam and start it"
                current_time = datetime.now()
                chosen_time = current_time + timedelta(hours=2)
                exam2 = Exam(
                    school=school,
                    room=room1.dn,  # room dn
                    examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
                    recipients=[klasse_dn],  # list of classes dns
                )
                exam2.start()
                wait_for_drs_replication(filter_format("cn=exam-%s", (stu,)))
                wait_for_drs_replication(filter_format("cn=exam-%s", (student2.name,)))
                utils.wait_for_replication()
                wait_for_s4connector()
                check_uids(exam_member_dns, open_ldap_co)
                exam2.finish()


if __name__ == "__main__":
    main()
