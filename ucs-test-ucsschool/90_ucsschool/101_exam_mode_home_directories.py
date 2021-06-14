#!/usr/share/ucs-test/runner pytest -s -l -v
## -*- coding: utf-8 -*-
## desc: Check home dirs of exam users during exam
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [37955]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from __future__ import print_function

import os
from datetime import datetime, timedelta

import univention.testing.strings as uts
from ucsschool.lib.models.user import Student
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.ucsschool.exam import Exam


def create_homedirs(member_dn_list, lo):
    # create home directories
    for dn in member_dn_list:
        for homedir in lo.getAttr(dn, "homeDirectory"):
            homedir = homedir.decode("UTF-8")
            assert homedir, "No homeDirectory attribute found for %r" % (dn,)
            if not os.path.exists(homedir):
                print("# Creating %r for %r" % (homedir, dn))
                os.makedirs(homedir)


def check_homedirs(member_dn_list, lo, should_exist=True):
    # create home directories
    for dn in member_dn_list:
        for homedir in lo.getAttr(dn, "homeDirectory"):
            homedir = homedir.decode("UTF-8")
            print("# Checking %r for %r" % (homedir, dn))
            assert homedir, "No homeDirectory attribute found for %r" % (dn,)
            assert os.path.exists(homedir) == should_exist


def test_exam_mode_home_directories(udm_session, schoolenv, ucr):
        udm = udm_session
        lo = schoolenv.open_ldap_connection()

        print("# create test users and classes")
        if ucr.is_true("ucsschool/singlemaster"):
            edudc = None
        else:
            edudc = ucr.get("hostname")
        school, oudn = schoolenv.create_ou(name_edudc=edudc)
        search_base = SchoolSearchBase([school])
        klasse_dn = udm.create_object(
            "groups/group",
            name="%s-AA1" % school,
            position=search_base.classes,
        )
        tea, teadn = schoolenv.create_user(school, is_teacher=True)
        stu, studn = schoolenv.create_user(school)
        student2 = Student(
            name=uts.random_username(),
            school=school,
            firstname=uts.random_name(),
            lastname=uts.random_name(),
        )
        student2.position = search_base.students
        student2.create(lo)
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [student2.dn]})

        print("# import random computers")
        computers = Computers(lo, school, 2, 0, 0)
        pc1, pc2 = computers.create()

        print("# set 2 computer rooms to contain the created computers")
        room1 = Room(school, host_members=pc1.dn)
        room2 = Room(school, host_members=pc2.dn)
        for room in [room1, room2]:
            schoolenv.create_computerroom(
                school,
                name=room.name,
                description=room.description,
                host_members=room.host_members,
            )

        print("# create home directories and check existance")
        create_homedirs([teadn, studn, student2.dn], lo)
        check_homedirs([teadn, studn, student2.dn], lo, should_exist=True)

        print("# Set an exam and start it")
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
            "uid=exam-%s,%s" % (tea, search_base.examUsers),
            "uid=exam-%s,%s" % (stu, search_base.examUsers),
            "uid=exam-%s,%s" % (student2.name, search_base.examUsers),
        ]

        print("# recheck existance of home directories of original users")
        check_homedirs([teadn, studn, student2.dn], lo, should_exist=True)
        print("# create home directories and check existance of exam users")
        create_homedirs(exam_member_dns, lo)
        check_homedirs(exam_member_dns, lo, should_exist=True)

        print("# stopping exam")
        exam.finish()

        print("# recheck existance of home directories of original users")
        check_homedirs([teadn, studn, student2.dn], lo, should_exist=True)
        print("# check removal of home directories of exam users")
        check_homedirs(exam_member_dns, lo, should_exist=False)
