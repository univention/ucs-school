#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check the consistency of exam users in unix, ldap and the ownership of their home directories
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [52307]
## packages: [ucs-school-umc-computerroom, ucs-school-umc-exam]

from __future__ import print_function

import os
import pwd
import time
from datetime import datetime, timedelta

from ldap.filter import filter_format

import univention.testing.strings as uts
import univention.testing.utils as utils
from ucsschool.lib.models.user import Student
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.admin.uexceptions import noObject
from univention.testing.ucs_samba import wait_for_drs_replication, wait_for_s4connector
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.ucsschool.exam import Exam

SLEEP_INTERVAL = 10
SLEEP_TIMEOUT = 300


def check_uids(member_dn_list, open_ldap_co):
    # check that the uids in ldap, unix and home dir ownership are consistent
    for dn in member_dn_list:
        print("Waiting for replication of {!r}...".format(dn))
        timeout = SLEEP_TIMEOUT
        get_attrs = ["uid", "uidNumber", "homeDirectory"]
        replicated = False
        attrs = {}
        while timeout > 0:
            try:
                attrs = open_ldap_co.get(dn, attr=get_attrs)
                if set(get_attrs).issubset(set(attrs.keys())):
                    print("Replication complete: {!r} -> {!r}".format(dn, attrs))
                    replicated = True
                else:
                    print("Replication incomplete: {!r} -> {!r}".format(dn, attrs))
            except noObject:
                print("Not yet replicated: {!r}".format(dn))
            if replicated:
                break
            else:
                print("Sleeping {}s...".format(SLEEP_INTERVAL))
                time.sleep(SLEEP_INTERVAL)
                timeout -= SLEEP_INTERVAL
                assert timeout > 0, "replication timed out... check logs of schoolexam Directory Node!"

        user_name = attrs["uid"][0].decode("UTF-8")
        ldap_uid = attrs["uidNumber"][0].decode("UTF-8")
        unix_uid = str(pwd.getpwnam(user_name).pw_uid)
        for homedir in attrs["homeDirectory"]:
            assert os.path.exists(homedir), "homeDirectory {} for {} does not exist".format(homedir, dn)
            dir_owner = str(os.stat(homedir).st_uid)
            assert ldap_uid == unix_uid == dir_owner, "uids of ldap object ({}), unix ({}) and home directory ownership ({}) are not consistent!".format(ldap_uid, unix_uid, dir_owner)


def test_exam_mode_uids(udm_session, schoolenv, ucr):
        udm = udm_session
        open_ldap_co = schoolenv.open_ldap_connection()

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
        tea, teadn = schoolenv.create_user(school, is_teacher=True)
        stu, studn = schoolenv.create_user(school)
        wait_for_drs_replication(filter_format("cn=%s", (stu,)))
        student2 = Student(
            name=uts.random_username(),
            school=school,
            firstname=uts.random_name(),
            lastname=uts.random_name(),
        )
        student2.position = search_base.students
        student2.create(open_ldap_co)
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [student2.dn]})
        wait_for_drs_replication(filter_format("cn=%s", (student2.name,)))

        print("# import random computers")
        computers = Computers(open_ldap_co, school, 2, 0, 0)
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

        try:
            exam_member_dns = [
                "uid=exam-%s,%s" % (stu, search_base.examUsers),
                "uid=exam-%s,%s" % (student2.name, search_base.examUsers),
            ]

            check_uids(exam_member_dns, open_ldap_co)

            print("# stopping exam")
        finally:
            exam.finish()

        print("# Set another exam and start it")
        current_time = datetime.now()
        chosen_time = current_time + timedelta(hours=2)
        exam2 = Exam(
            school=school,
            room=room1.dn,  # room dn
            examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
            recipients=[klasse_dn],  # list of classes dns
        )
        exam2.start()
        try:
            attrs = ["uidNumber", "homeDirectory"]
            wait_for_drs_replication(filter_format("cn=exam-%s", (stu,)), attrs=attrs)
            wait_for_drs_replication(filter_format("cn=exam-%s", (student2.name,)), attrs=attrs)
            utils.wait_for_replication()
            wait_for_s4connector()
            check_uids(exam_member_dns, open_ldap_co)
        finally:
            exam2.finish()
