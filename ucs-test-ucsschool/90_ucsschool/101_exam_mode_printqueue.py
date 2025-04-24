#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Exam mode
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1,ucs-school-umc-exam]
## exposure: dangerous
## bugs: []
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from __future__ import print_function

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


class Test_ExamMode(object):
    def test_printing_in_exam_mode(
        self,
        udm_session,
        schoolenv,
        create_ou,
        list_pdfprinter_jobs,
        send_pdfprinter_job,
        check_pdfprinter_spool_permissions,
    ):
        ucr = schoolenv.ucr
        lo = schoolenv.open_ldap_connection()
        ucr.load()

        print(" ** Initial Status")
        existing_rejects = get_s4_rejected()

        school, oudn = create_ou()
        search_base = SchoolSearchBase([school])
        klasse_dn = udm_session.create_object(
            "groups/group", name="%s-AA1" % school, position=search_base.classes
        )

        tea, teadn = schoolenv.create_user(school, is_teacher=True)
        stu, studn = schoolenv.create_user(school)
        student2 = Student(
            name=uts.random_username(),
            school=school,
            firstname=uts.random_name(),
            lastname=uts.random_name(),
        )
        student2.position = "cn=users,%s" % ucr["ldap/base"]
        student2.create(lo)

        udm_session.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
        udm_session.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})
        udm_session.modify_object("groups/group", dn=klasse_dn, append={"users": [student2.dn]})

        print(" ** After Creating users and classes")
        wait_replications_check_rejected_uniqueMember(existing_rejects)

        # importing random computers
        computers = Computers(lo, school, 2, 0, 0)
        created_computers = computers.create()
        created_computers_dn = computers.get_dns(created_computers)

        # setting 1 computer rooms contain the created computers
        room = Room(school, host_members=created_computers_dn[0])

        # Creating the room
        schoolenv.create_computerroom(
            school,
            name=room.name,
            description=room.description,
            host_members=room.host_members,
        )

        current_time = datetime.now()
        chosen_time = current_time + timedelta(hours=2)

        print(" ** After creating the room")
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

        # send print job as exam user
        default_printer = "PDFDrucker"
        test_file = "testpage.ps"
        host = ucr.get("hostname")
        send_pdfprinter_job(default_printer, host, f"exam-{stu}", test_file)

        # spool directory should be owned by the exam user
        # (checked after print job, because directory might be missing before sending the print job)
        check_pdfprinter_spool_permissions(f"exam-{stu}")

        exam.finish()
        print(" ** After finishing the exam")
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

        # spool directory should be owned by the new/recreated exam user
        check_pdfprinter_spool_permissions(f"exam-{stu}")

        # send print job as exam user
        send_pdfprinter_job(default_printer, host, f"exam-{stu}", test_file)

        exam.finish()
        print(" ** After finishing the exam")
        wait_replications_check_rejected_uniqueMember(existing_rejects)
        student2.remove(lo)
