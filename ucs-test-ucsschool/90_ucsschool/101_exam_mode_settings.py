#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Exam mode settings
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [36251, 41568]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from __future__ import print_function

import os
import random
import tempfile
from datetime import datetime, timedelta

import univention.testing.strings as uts
from ucsschool.lib.models.user import Student
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.computerroom import Room
from univention.testing.ucsschool.exam import (
    Exam,
    get_s4_rejected,
    wait_replications_check_rejected_uniqueMember,
)
from univention.testing.ucsschool.internetrule import InternetRule


def test_exam_mode_settings(udm_session, schoolenv, ucr):
    udm = udm_session
    lo = schoolenv.open_ldap_connection()

    print(" ** Initial Status")
    existing_rejects = get_s4_rejected()

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

    print(" ** After Creating users and classes")
    wait_replications_check_rejected_uniqueMember(existing_rejects)

    # importing random computers
    computers = Computers(lo, school, 2, 0, 0)
    created_computers = computers.create()
    created_computers_dn = computers.get_dns(created_computers)

    # setting 2 computer rooms contain the created computers
    room1 = Room(school, host_members=created_computers_dn[0])
    room2 = Room(school, host_members=created_computers_dn[1])

    # Creating the rooms
    for room in [room1, room2]:
        schoolenv.create_computerroom(
            school,
            name=room.name,
            description=room.description,
            host_members=room.host_members,
        )

    # Defining internet rules
    rule1 = InternetRule(ucr=ucr)
    rule1.define()

    # Preparing tempfile to upload
    f = tempfile.NamedTemporaryFile("w+", suffix=".exam")  # , dir='/tmp')
    print("Tempfile created %s" % f.name)
    f.write("Temp exam file to upload")
    f.flush()

    current_time = datetime.now()
    chosen_time = current_time + timedelta(hours=2)

    print(" ** After creating the rooms")
    wait_replications_check_rejected_uniqueMember(existing_rejects)

    exam = Exam(
        school=school,
        room=room2.dn,  # room dn
        files=[os.path.basename(f.name)],
        examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
        recipients=[klasse_dn],  # list of classes dns
    )

    exam.uploadFile(f.name)
    exam.check_upload()

    exam.fetch_internetRule(rule1.name)
    exam.fetch_groups("AA1")
    exam.fetch_school(school)

    share_modes = ["home", "all"]
    current_internetRules = exam.get_internetRules()
    exam.internetRule = random.choice(current_internetRules)
    exam.shareMode = random.choice(share_modes)

    exam.start()
    print(" ** After starting the exam")
    wait_replications_check_rejected_uniqueMember(existing_rejects)

    exam.check_distribute()

    exam.collect()
    print(" ** After collecting the exam")
    wait_replications_check_rejected_uniqueMember(existing_rejects)
    exam.check_collect()

    f.close()
    exam.finish()
    print(" ** After finishing the exam")
    wait_replications_check_rejected_uniqueMember(existing_rejects)
    student2.remove(lo)
