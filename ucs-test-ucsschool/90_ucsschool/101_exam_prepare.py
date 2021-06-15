#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Check exam adding, putting and getting
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: []
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

from datetime import datetime, timedelta
from unittest import TestCase, main

import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.lib.umc import HTTPError
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.ucsschool.exam import (
    Exam,
    ExamSaml,
    SaveFail,
    get_s4_rejected,
    wait_replications_check_rejected_uniqueMember,
)


class TestExamPrepare(TestCase):
    def __test_exam_prepare(self, Exam=Exam):
        with univention.testing.udm.UCSTestUDM() as udm, utu.UCSTestSchool() as schoolenv:
            ucr = schoolenv.ucr
            open_ldap_co = schoolenv.open_ldap_connection()
            ucr.load()

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
            computers = Computers(open_ldap_co, school, 1, 0, 0)
            created_computers = computers.create()
            created_computers_dn = computers.get_dns(created_computers)

            room = Room(school, host_members=created_computers_dn[0])

            schoolenv.create_computerroom(
                school,
                name=room.name,
                description=room.description,
                host_members=room.host_members,
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
            exam2 = Exam(
                school=school,
                room=room.dn,  # room dn
                examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
                recipients=[klasse_dn],  # list of classes dns
            )
            try:
                exam.save(fields=["recipients", "school"])
                raise Exception("Exam should not have been saved due to missing name")
            except HTTPError:
                print(" ** Save failed as expected")
            except SaveFail:
                print(" ** Save failed as expected")
            exam.save()
            try:
                exam.save()
            except HTTPError:
                print(" ** Save failed as expected due to existing name")
            exam.save(update=True, fields=["name", "room", "school", "directory"])
            result = exam.get()[0]
            for key in result.keys():
                if key in ["room", "name"]:
                    assert result[key] == getattr(exam, key)
            assert result["recipients"] == []
            assert not result["isDistributed"]
            assert result["examEndTime"] == ""
            # Testing exam deletion
            exam.start()
            result = exam.delete()
            assert not any(result)
            exam2.save(fields=["name", "room", "school", "directory"])
            result = exam2.delete()
            assert all(result)
            wait_replications_check_rejected_uniqueMember(existing_rejects)

    def test_saml_login(self):
        self.__test_exam_prepare(Exam=ExamSaml)

    def test_classic_login(self):
        self.__test_exam_prepare()


if __name__ == "__main__":
    main(verbosity=2)
