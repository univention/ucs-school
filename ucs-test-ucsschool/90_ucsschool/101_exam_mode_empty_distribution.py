#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check file collection from exams without prior distribution of files
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [47160]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from __future__ import print_function

import os
import subprocess
from datetime import datetime, timedelta

from ldap.filter import filter_format

import univention.testing.strings as uts
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.computerroom import Room
from univention.testing.ucsschool.exam import (
    Exam,
    get_s4_rejected,
    wait_replications_check_rejected_uniqueMember,
)


# Flakes when UMC server can't be reached
def test_FLAKY_exam_mode_empty_distribution(udm_session, schoolenv, ucr):
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

    udm.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
    udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})

    print(" ** After Creating users and classes")
    wait_replications_check_rejected_uniqueMember(existing_rejects)

    # importing random computer
    computers = Computers(lo, school, 1, 0, 0)
    created_computers = computers.create()
    created_computers_dn = computers.get_dns(created_computers)

    room = Room(school, host_members=created_computers_dn[0])

    schoolenv.create_computerroom(
        school, name=room.name, description=room.description, host_members=room.host_members
    )

    current_time = datetime.now()
    chosen_time = current_time + timedelta(hours=2)

    print(" ** After creating the rooms")
    wait_replications_check_rejected_uniqueMember(existing_rejects)

    exam = Exam(
        school=school,
        room=room.dn,  # room dn
        examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
        recipients=[klasse_dn],  # list of classes dns
    )

    exam.start()
    print(" ** After starting the exam")
    wait_replications_check_rejected_uniqueMember(existing_rejects)
    filename = uts.random_string()
    exam_stu_homedir = lo.search(filter_format("uid=%s", ("exam-" + stu,)), attr=("homeDirectory",))[0][
        1
    ]["homeDirectory"][0].decode("UTF-8")
    subprocess.check_call(
        [
            "touch",
            os.path.join(exam_stu_homedir, "Klassenarbeiten/", exam.directory, filename),
        ]
    )
    exam.files.append(filename)
    exam.finish()
    exam.check_collect()
    print(" ** After finishing the exam")
    wait_replications_check_rejected_uniqueMember(existing_rejects)
