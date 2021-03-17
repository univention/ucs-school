#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Exam mode
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [50588]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

import os
from datetime import datetime, timedelta

from ldap.filter import filter_format

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.roles import (
    context_type_exam,
    create_ucsschool_role_string,
    role_exam_user,
    role_student,
)
from ucsschool.lib.models.user import ExamStudent, Student
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.config_registry import handler_set
from univention.testing import utils
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.ucsschool.exam import (
    Exam,
    get_s4_rejected,
    wait_replications_check_rejected_uniqueMember,
)
from univention.testing.udm import UCSTestUDM


def main():
    with UCSTestUDM() as udm, utu.UCSTestSchool() as schoolenv:
        ucr = schoolenv.ucr
        open_ldap_co = schoolenv.open_ldap_connection()
        handler_set(["ucsschool/exam/user/homedir/autoremove=yes"])
        ucr.load()

        print(" ** Initial Status")
        existing_rejects = get_s4_rejected()

        if ucr.is_true("ucsschool/singlemaster"):
            edudc = None
        else:
            edudc = ucr.get("hostname")
        school, oudn = schoolenv.create_ou(ou_name=uts.random_name(), name_edudc=edudc)
        search_base1 = SchoolSearchBase([school])
        school2, oudn2 = schoolenv.create_ou(ou_name=uts.random_name(), name_edudc=edudc)
        search_base2 = SchoolSearchBase([school2])
        klasse_dn = udm.create_object(
            "groups/group",
            name="%s-%s" % (school, uts.random_name()),
            position=search_base1.classes,
        )
        klasse_dn2 = udm.create_object(
            "groups/group",
            name="%s-%s" % (school2, uts.random_name()),
            position=search_base2.classes,
        )

        tea, teadn = schoolenv.create_user(school, is_teacher=True)
        tea2, teadn2 = schoolenv.create_user(school2, is_teacher=True)
        stu, studn = schoolenv.create_user(school)
        student2 = Student(
            name=uts.random_username(),
            school=school2,
            firstname=uts.random_name(),
            lastname=uts.random_name(),
        )
        student2.schools.append(school)
        student2.ucsschool_roles.append(create_ucsschool_role_string(role_student, school))
        student2.create(open_ldap_co)

        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})
        udm.modify_object("groups/group", dn=klasse_dn, append={"users": [student2.dn]})
        udm.modify_object("groups/group", dn=klasse_dn2, append={"users": [student2.dn]})
        udm.modify_object("groups/group", dn=klasse_dn2, append={"users": [teadn2]})

        print(" ** After Creating users and classes")
        wait_replications_check_rejected_uniqueMember(existing_rejects)

        rooms = {}

        for s in (school, school2):
            # importing random computers
            computers = Computers(open_ldap_co, s, 1, 0, 0)
            created_computers = computers.create()
            created_computers_dn = computers.get_dns(created_computers)

            # setting 1 computer rooms contain the created computer
            room = Room(s, host_members=created_computers_dn[0])

            # Creating the room
            schoolenv.create_computerroom(
                s, name=room.name, description=room.description, host_members=room.host_members
            )
            rooms[s] = room

        current_time = datetime.now()
        chosen_time = current_time + timedelta(hours=2)

        print(" ** After creating the rooms")
        wait_replications_check_rejected_uniqueMember(existing_rejects)

        exam = Exam(
            school=school,
            room=rooms[school].dn,  # room dn
            examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
            recipients=[klasse_dn],  # list of classes dns
        )

        exam2 = Exam(
            school=school2,
            room=rooms[school2].dn,  # room dn
            examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
            recipients=[klasse_dn2],  # list of classes dns
        )

        exam.start()
        print(" ** After starting the exam")
        wait_replications_check_rejected_uniqueMember(existing_rejects)

        exam_role_str = create_ucsschool_role_string(
            role_exam_user, "{}-{}".format(exam.name, school), context_type_exam
        )
        exam2_role_str = create_ucsschool_role_string(
            role_exam_user, "{}-{}".format(exam2.name, school2), context_type_exam
        )
        exam_student2 = ExamStudent.get_all(
            open_ldap_co, school2, filter_format("uid=exam-%s", (student2.name,))
        )[0]
        exam_student2_home = exam_student2.get_udm_object(open_ldap_co)["unixhome"]
        assert exam_student2_home.startswith("/home/")
        assert os.path.isdir(exam_student2_home)
        assert exam_role_str in exam_student2.ucsschool_roles
        assert exam2_role_str not in exam_student2.ucsschool_roles
        assert all(s in exam_student2.schools for s in (school, school2))
        exam2.start()
        wait_replications_check_rejected_uniqueMember(existing_rejects)
        exam_student2 = ExamStudent.get_all(
            open_ldap_co, school2, filter_format("uid=exam-%s", (student2.name,))
        )[0]
        for school in (school, school2):
            assert school in exam_student2.schools
        assert all(r in exam_student2.ucsschool_roles for r in (exam_role_str, exam2_role_str))
        exam.finish()
        exam_student2 = ExamStudent.get_all(
            open_ldap_co, school, filter_format("uid=exam-%s", (student2.name,))
        )[0]
        assert os.path.isdir(exam_student2_home)
        assert all(s in exam_student2.schools for s in (school, school2))
        assert exam2_role_str in exam_student2.ucsschool_roles
        assert exam_role_str not in exam_student2.ucsschool_roles
        exam2.finish()
        print(" ** After finishing the exams")
        wait_replications_check_rejected_uniqueMember(existing_rejects)
        assert not os.path.isdir(exam_student2_home)
        utils.verify_ldap_object(exam_student2.dn, should_exist=False)
        student2.remove(open_ldap_co)


if __name__ == "__main__":
    main()
