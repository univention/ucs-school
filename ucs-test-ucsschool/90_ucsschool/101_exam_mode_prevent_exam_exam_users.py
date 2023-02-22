#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check that exam-exam- users are not created
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [55619]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from datetime import datetime, timedelta

from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.computerroom import Room
from univention.testing.ucsschool.exam import Exam


def test_exam_mode_no_exam_exam_users(udm_session, schoolenv, ucr):
    udm = udm_session

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
    udm.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
    udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})

    # import random computers
    computers = Computers(schoolenv.lo, school, 3, 0, 0)
    pc1, pc2, pc3 = computers.create()

    # set 2 computer rooms to contain the created computers
    room1 = Room(school, host_members=pc1.dn)
    room2 = Room(school, host_members=[pc2.dn, pc3.dn], teacher_computers=[pc2.dn])
    for room in [room1, room2]:
        schoolenv.create_computerroom(
            school,
            name=room.name,
            description=room.description,
            host_members=room.host_members,
            teacher_computers=room.teacher_computers,
        )

    # Set an exam and start it
    current_time = datetime.now()
    chosen_time = current_time + timedelta(hours=2)
    exam1 = Exam(
        school=school,
        room=room1.dn,  # room dn
        examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
        recipients=[klasse_dn],  # list of classes dns
    )
    exam1.start()
    # start another exam with the same user
    current_time = datetime.now()
    chosen_time = current_time + timedelta(hours=2)
    exam2 = Exam(
        school=school,
        room=room2.dn,  # room dn
        examEndTime=chosen_time.strftime("%H:%M"),  # in format HH:mm"
        recipients=[klasse_dn],  # list of classes dns
    )
    exam2.start()

    try:
        results = schoolenv.lo.search(base=search_base.examUsers, filter=f"uid=*{stu}")

        assert len(results) == 1

    finally:
        exam1.finish()
        exam2.finish()
