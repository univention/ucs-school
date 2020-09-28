#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: tests for exam-cleanup script
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [50636]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from datetime import datetime, timedelta

from ldap.filter import escape_filter_chars, filter_format

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm
from ucsschool.lib.models import User
from ucsschool.lib.models.utils import exec_cmd
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.ucsschool.exam import (
    Exam,
    get_s4_rejected,
    wait_replications_check_rejected_uniqueMember,
)

try:
    from typing import List
    from univention.admin.uldap import access as LoType
except ImportError:
    pass


def get_user_work_stations(lo, stu):  # type: (LoType, str) -> List
    mod_user = univention.udm.UDM(lo, 1).get("users/user")
    res = list(mod_user.search(filter_format("uid=%s", [stu])))
    assert len(res) == 1
    orig_udm = res[0]
    return orig_udm.props.sambaUserWorkstations


def test_user_restore_after_exam():
    with univention.testing.udm.UCSTestUDM() as udm:
        with utu.UCSTestSchool() as schoolenv:
            open_ldap_co = schoolenv.open_ldap_connection()
            schoolenv.ucr.load()
            existing_rejects = get_s4_rejected()
            if schoolenv.ucr.is_true("ucsschool/singlemaster"):
                edudc = None
            else:
                edudc = schoolenv.ucr.get("hostname")
            school, oudn = schoolenv.create_ou(name_edudc=edudc)
            klasse_dn = udm.create_object(
                "groups/group",
                name="%s-AA1" % school,
                position="cn=klassen,cn=schueler,cn=groups,%s" % oudn,
            )

            stu, studn = schoolenv.create_user(school)
            stu2, studn2 = schoolenv.create_user(school)
            udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn, studn2]})
            user = User.from_dn(studn2, school, schoolenv.lo)
            user_udm = user.get_udm_object(schoolenv.lo)
            orig_value_user2 = [uts.random_string() for _ in range(3)]
            user_udm["sambaUserWorkstations"] = orig_value_user2
            user_udm.modify()

            wait_replications_check_rejected_uniqueMember(existing_rejects)

            computers = Computers(open_ldap_co, school, 1, 0, 0)
            created_computers = computers.create()
            created_computers_dn = computers.get_dns(created_computers)

            room = Room(school, host_members=created_computers_dn[0])

            schoolenv.create_computerroom(
                school, name=room.name, description=room.description, host_members=room.host_members,
            )

            wait_replications_check_rejected_uniqueMember(existing_rejects)
            chosen_time = datetime.now() + timedelta(hours=2)
            exam = Exam(
                school=school,
                room=room.dn,
                examEndTime=chosen_time.strftime("%H:%M"),
                recipients=[klasse_dn],
            )

            exam.start()
            wait_replications_check_rejected_uniqueMember(existing_rejects)

            samba_user_workstations_user1 = get_user_work_stations(schoolenv.lo, stu)[0]
            samba_user_workstations_user2 = get_user_work_stations(schoolenv.lo, stu2)
            assert samba_user_workstations_user1.startswith("$")
            assert all([s.startswith("$") for s in samba_user_workstations_user2])

            exec_cmd(
                ["/usr/share/ucs-school-exam/exam-and-room-cleanup", "--skip-exam-shutdown"],
                log=True,
                raise_exc=True,
            )
            samba_user_workstations_user1 = get_user_work_stations(schoolenv.lo, stu)
            samba_user_workstations_user2 = get_user_work_stations(schoolenv.lo, stu2)
            assert not samba_user_workstations_user1
            assert not any([s.startswith("$") for s in samba_user_workstations_user2])
            assert samba_user_workstations_user2 == orig_value_user2
            exam.finish()

            wait_replications_check_rejected_uniqueMember(existing_rejects)
