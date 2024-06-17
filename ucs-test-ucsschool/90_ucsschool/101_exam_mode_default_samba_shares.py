#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Invalid smb conf files should raise UMC erros
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [57367]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]
from datetime import datetime, timedelta

import univention.testing.strings as uts
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.lib.umc import BadRequest
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.computerroom import Room
from univention.testing.ucsschool.exam import Exam
from univention.testing.umc import Client


def test_exam_broken_share_conf(udm_session, schoolenv, ucr):
    udm = udm_session
    lo = schoolenv.open_ldap_connection()
    if ucr.is_true("ucsschool/singlemaster"):
        edudc = None
    else:
        edudc = ucr.get("hostname")
    school, _ = schoolenv.create_ou(name_edudc=edudc)
    class_dn = udm.create_object(
        "groups/group",
        name="{}-{}".format(school, uts.random_name()),
        position=SchoolSearchBase([school]).classes,
    )
    _, teadn = schoolenv.create_user(school, is_teacher=True)
    _, studn = schoolenv.create_user(school)
    udm.modify_object("groups/group", dn=class_dn, append={"users": [teadn]})
    udm.modify_object("groups/group", dn=class_dn, append={"users": [studn]})
    computers = Computers(lo=lo, school=school, nr_windows=2)
    pc1, pc2 = computers.create()
    room = Room(school, host_members=[pc1.dn, pc2.dn])
    schoolenv.create_computerroom(
        school,
        name=room.name,
        description=room.description,
        host_members=room.host_members,
    )
    chosen_time = datetime.now() + timedelta(hours=2)

    client = Client.get_test_connection(language="en-US")

    with open("/etc/samba/shares.conf") as fin:
        old_config = fin.read()

    # Messing up shares.conf will raise an UMC error.
    try:
        with open("/etc/samba/shares.conf", "w") as fout:
            fout.write(old_config + "\n include = funky-conf")
        exam = Exam(
            school=school,
            room=room.dn,
            connection=client,
            examEndTime=chosen_time.strftime("%H:%M"),
            recipients=[class_dn],
        )
        raised_exception = False
        exam.start()
    except BadRequest as exc:
        raised_exception = True
        assert exc.status == 400
        assert (
            "An error occurred while loading one of the samba share configuration files"
        ) in exc.message
    finally:
        with open("/etc/samba/shares.conf", "w") as fout:
            fout.write(old_config)
    assert raised_exception
