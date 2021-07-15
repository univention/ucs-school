#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Exam mode
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [36251, 41568]
## packages: [ucs-school-umc-computerroom, ucs-school-umc-exam, ucs-school-singlemaster]

from datetime import datetime, timedelta
from time import sleep

from ldap.filter import filter_format

from ucsschool.lib.models.user import Student
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.config_registry import handler_set
from univention.testing.ucs_samba import wait_for_drs_replication, wait_for_s4connector
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.ucsschool.exam import Exam


def is_user_disabled(user_dn, lo):
    user = Student.from_dn(user_dn, None, lo)
    obj = user.get_udm_object(lo)
    print("# user disabled value: {}".format(obj["disabled"]))
    return obj["disabled"] == "1"


def test_exam_mode_deactivate_user(udm_session, schoolenv, ucr):
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
    klasse2_dn = udm.create_object(
        "groups/group",
        name="%s-BB1" % school,
        position=search_base.classes,
    )
    tea, teadn = schoolenv.create_user(school, is_teacher=True)
    stu, studn = schoolenv.create_user(school)
    stu2, studn2 = schoolenv.create_user(school)
    wait_for_drs_replication(filter_format("cn=%s", (stu,)))

    udm.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
    udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})
    udm.modify_object("groups/group", dn=klasse2_dn, append={"users": [teadn]})
    udm.modify_object("groups/group", dn=klasse2_dn, append={"users": [studn2]})

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

    # Actual test starts here:

    print("# Set an exam and start it with ucsschool/exam/user/disable=no")
    current_time = datetime.now()
    chosen_time = current_time + timedelta(hours=2)
    exam = Exam(
        school=school,
        room=room1.dn,  # room dn
        examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
        recipients=[klasse_dn],  # list of classes dns
    )

    # check if user is enabled
    handler_set(["ucsschool/exam/user/disable=no"])
    assert not is_user_disabled(studn, lo), "disable=no: User was not enabled before exam"

    exam.start()
    print(" ** After starting the exam1")
    wait_for_drs_replication(filter_format("cn=exam-%s", (stu,)))

    # check if user is still enabled
    assert not is_user_disabled(studn, lo), "User was not enabled during exam"

    exam.finish()
    sleep(10)  # ensure this exam is finished before a new one starts
    print(" ** After finishing the exam1")

    # check if user is enabled
    assert not is_user_disabled(studn, lo), "disable=yes: User was not enabled after exam"

    print("# Set another exam and start it with ucsschool/exam/user/disable=yes")
    current_time = datetime.now()
    chosen_time = current_time + timedelta(hours=2)
    exam2 = Exam(
        school=school,
        room=room2.dn,  # room dn
        examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
        recipients=[klasse2_dn],  # list of classes dns
    )

    # check if user is enabled
    handler_set(["ucsschool/exam/user/disable=yes"])
    assert not is_user_disabled(studn2, lo), "disable=yes: User was not enabled before exam"

    exam2.start()
    print(" ** After starting the exam2")

    # check if user is disabled
    assert is_user_disabled(studn2, lo), "disable=yes: User was not disabled during exam"

    exam2.finish()
    print(" ** After finishing the exam2")

    # check if user is enabled
    assert not is_user_disabled(studn2, lo), "User was not enabled after exam"

    wait_for_s4connector()
