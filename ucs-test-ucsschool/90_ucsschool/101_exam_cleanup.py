#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: tests for exam-cleanup script
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [50636]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from datetime import datetime, timedelta

from ldap.filter import filter_format

import univention.testing.strings as uts
from ucsschool.lib.models.user import User
from ucsschool.lib.models.utils import exec_cmd
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.ucsschool.exam import (
    Exam,
    get_s4_rejected,
    wait_replications_check_rejected_uniqueMember,
)
from univention.udm import UDM as SysUDM

try:
    from typing import List  # noqa: F401

    from univention.udm.modules.users_user import UsersUserModule  # noqa: F401
except ImportError:
    pass


def get_user_work_stations(mod_user, stu):  # type: (UsersUserModule, str) -> List[str]
    res = list(mod_user.search(filter_format("uid=%s", [stu])))
    assert len(res) == 1
    orig_udm = res[0]
    return orig_udm.props.sambaUserWorkstations


def test_user_restore_after_exam(udm_session, schoolenv):
        udm = udm_session
        # UCSTestUDM does not search, so I have to use the normal UDM
        mod_user = SysUDM(schoolenv.lo, 1).get("users/user")
        lo = schoolenv.open_ldap_connection()
        schoolenv.ucr.load()
        existing_rejects = get_s4_rejected()
        if schoolenv.ucr.is_true("ucsschool/singlemaster"):
            edudc = None
        else:
            edudc = schoolenv.ucr.get("hostname")
        school, oudn = schoolenv.create_ou(name_edudc=edudc)
        search_base = SchoolSearchBase([school])
        klasse_dn = udm.create_object(
            "groups/group",
            name="%s-AA1" % school,
            position=search_base.classes,
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

        computers = Computers(lo, school, 1, 0, 0)
        created_computers = computers.create()
        created_computers_dn = computers.get_dns(created_computers)

        room = Room(school, host_members=created_computers_dn[0])

        schoolenv.create_computerroom(
            school, name=room.name, description=room.description, host_members=room.host_members
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

        samba_user_workstations_user1 = get_user_work_stations(mod_user, stu)[0]
        samba_user_workstations_user2 = get_user_work_stations(mod_user, stu2)
        assert samba_user_workstations_user1.startswith("$")
        assert all([s.startswith("$") for s in samba_user_workstations_user2])

        exec_cmd(
            ["/usr/share/ucs-school-exam/exam-and-room-cleanup", "--skip-exam-shutdown"],
            log=True,
            raise_exc=True,
        )
        samba_user_workstations_user1 = get_user_work_stations(mod_user, stu)
        samba_user_workstations_user2 = get_user_work_stations(mod_user, stu2)
        assert not samba_user_workstations_user1
        assert not any([s.startswith("$") for s in samba_user_workstations_user2])
        assert samba_user_workstations_user2 == orig_value_user2
        exam.finish()

        wait_replications_check_rejected_uniqueMember(existing_rejects)
