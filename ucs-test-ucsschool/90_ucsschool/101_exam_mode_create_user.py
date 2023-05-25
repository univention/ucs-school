#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test the
## roles: [domaincontroller_master, domaincontroller_backup]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [54848]
## packages: [ucs-school-umc-exam-master]

from __future__ import print_function

import univention.testing.strings as uts
from univention.testing.ucsschool.computerroom import Room
from univention.testing.umc import Client
from univention.udm import UDM


def test_exam_mode_create_exam_user(udm_session, schoolenv, ucr):
    """
    Test the 'schoolexam-master/create-exam-user' UMCP endpoint

    - Fix for Bug #54848 is verfied/tested by adding another user and modifying its SID
    """
    udm = udm_session
    client = Client.get_test_connection()

    print("# create test users and classes")
    if ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = ucr.get("hostname")

    school, oudn = schoolenv.create_ou(name_edudc=edudc, use_cache=False)
    room = Room(school)
    schoolenv.create_computerroom(
        school, name=room.name, description=room.description, host_members=room.host_members
    )

    student1_name, student1_dn = schoolenv.create_user(school)

    # Bug #54848 / Issue univention/ucs#1135
    print("# Create a user and increment its sambaRID, provoking Bug #54848")
    user_dn, user_name = udm.create_user()
    user_dn, user_attrs = udm.list_objects("users/user", filter="uid={}".format(user_name))[0]
    samba_rid = int(user_attrs["sambaRID"][0])
    uid_number = int(user_attrs["uidNumber"][0])

    # only modify the sambaRID if uidNumber and sambaRID are in sync
    if uid_number * 2 + 1000 == samba_rid:
        udm.modify_object("users/user", dn=user_dn, sambaRID=samba_rid + 2)

    response = client.umc_command(
        "schoolexam-master/create-exam-user",
        {"school": school, "userdn": student1_dn, "room": room.dn, "exam": uts.random_name()},
    )

    assert response.status == 200
    exam_user_dn = response.result["examuserdn"]

    _, exam_user_attrs = udm.list_objects("users/user", position=exam_user_dn)[0]

    print("# Extra cleanup: Remove created exam user")
    user_mod = UDM.admin().version(2).get("users/user")
    exam_user = user_mod.get(exam_user_dn)
    exam_user.delete()
