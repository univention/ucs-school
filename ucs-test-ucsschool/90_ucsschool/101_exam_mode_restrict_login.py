#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check login restrictions of exam users and original users during exam
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [49960]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from datetime import datetime, timedelta

import univention.testing.strings as uts
from ucsschool.lib.models.user import Student
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.ucsschool.computer import Computers, Room
from univention.testing.ucsschool.exam import Exam


def test_exam_mode_restrict_login(udm_session, schoolenv):
    ucr = schoolenv.ucr
    lo = schoolenv.open_ldap_connection()
    ucr.load()
    print("# create test users and classes")
    if ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = ucr.get("hostname")
    school, oudn = schoolenv.create_ou(name_edudc=edudc)
    search_base = SchoolSearchBase([school])
    klasse_dn = udm_session.create_object(
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
    orig_udm = student2.get_udm_object(lo)
    orig_udm["sambaUserWorkstations"] = ["OTHERPC"]
    orig_udm.modify()
    udm_session.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
    udm_session.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})
    udm_session.modify_object("groups/group", dn=klasse_dn, append={"users": [student2.dn]})

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
        "uid=exam-%s,%s" % (stu, search_base.examUsers),
        "uid=exam-%s,%s" % (student2.name, search_base.examUsers),
    ]

    for dn in exam_member_dns:
        result = lo.get(dn, ["sambaUserWorkstations"], True)
        assert result.get("sambaUserWorkstations") == [pc2.name.encode("UTF-8")]
    result = lo.get(student2.dn, ["sambaUserWorkstations"], True)
    assert result.get("sambaUserWorkstations") == [b"$OTHERPC"]
    print("# stopping exam")
    exam.finish()
    result = lo.get(student2.dn, ["sambaUserWorkstations"], True)
    assert result.get("sambaUserWorkstations") == [b"OTHERPC"]
