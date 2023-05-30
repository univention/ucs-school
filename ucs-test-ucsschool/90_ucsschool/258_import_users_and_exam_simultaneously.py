#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Importing users via CLI v2 and running an exam simultaneously
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
##   - ucs-school-umc-computerroom
##   - ucs-school-umc-exam
##   - univention-s4-connector
## bugs: [54228]

import subprocess
from copy import deepcopy
from datetime import datetime, timedelta

from ldap.filter import filter_format

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.user import Student, User
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.config_registry import handler_set
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.computerroom import Room
from univention.testing.ucsschool.exam import (
    Exam,
    get_s4_rejected,
    wait_replications_check_rejected_uniqueMember,
)
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester
from univention.testing.udm import UCSTestUDM


class Test(CLI_Import_v2_Tester):
    ou_B = None
    ou_C = None

    def test(self):
        """
        for role in ('student', 'teacher', 'staff', 'teacher_and_staff') with 10 users each:
            import user with role <role>
            modify user with role <role> → changing group memberships
            remove user with role <role>
        """
        with UCSTestUDM() as udm, utu.UCSTestSchool() as schoolenv:
            ucr = schoolenv.ucr
            ucr.load()
            handler_set(["ucsschool/stop_notifier=False"])
            self.log.info("*** Import a new user of each role...")

            source_uid = "source_uid-%s" % (uts.random_string(),)
            config = deepcopy(self.default_config)
            config.update_entry("csv:mapping:record_uid", "record_uid")
            config.update_entry("csv:mapping:role", "__role")
            config.update_entry("source_uid", source_uid)
            config.update_entry("user_role", None)

            n_users_of_each_role = 10
            person_list = []
            for role in ("student", "teacher", "staff", "teacher_and_staff"):
                for _ in range(n_users_of_each_role):
                    person = Person(self.ou_A.name, role)
                    person.update(
                        record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid
                    )
                    person_list.append(person)

            fn_csv = self.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
            config.update_entry("input:filename", fn_csv)
            fn_config = self.create_config_json(values=config)
            self.save_ldap_status()
            cmd = ["/usr/share/ucs-school-import/scripts/ucs-school-user-import", "-v", "-c", fn_config]
            # run command in background
            self.log.info("Running command: %s", " ".join(cmd))
            import_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # start exam
            print(" ** Start exam")
            lo = schoolenv.open_ldap_connection()
            existing_rejects = get_s4_rejected()

            school = self.ou_A.name
            search_base = SchoolSearchBase([school])
            klasse_dn = udm.create_object(
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

            udm.modify_object("groups/group", dn=klasse_dn, append={"users": [teadn]})
            udm.modify_object("groups/group", dn=klasse_dn, append={"users": [studn]})
            udm.modify_object("groups/group", dn=klasse_dn, append={"users": [student2.dn]})

            print(" ** After Creating users and classes")
            wait_replications_check_rejected_uniqueMember(existing_rejects)

            # importing random computers
            computers = Computers(lo, school, 2, 0, 0)
            created_computers = computers.create()
            created_computers_dn = computers.get_dns(created_computers)

            # setting 2 computer rooms contain the created computers
            room1 = Room(school, host_members=created_computers_dn[0])
            room2 = Room(school, host_members=created_computers_dn[1])

            # Creating the rooms
            for room in [room1, room2]:
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
                room=room2.dn,  # room dn
                examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
                recipients=[klasse_dn],  # list of classes dns
            )

            exam.start()
            print(" ** After starting the exam")
            wait_replications_check_rejected_uniqueMember(existing_rejects)

            exam.finish()
            print(" ** After finishing the exam")
            wait_replications_check_rejected_uniqueMember(existing_rejects)
            User.from_dn(teadn, school, lo).remove(lo)
            User.from_dn(studn, school, lo).remove(lo)
            student2.remove(lo)

            self.log.info("Waiting for import to finish...")
            print(import_proc.stderr.read().decode("utf-8"))
            try:
                import_proc.wait(timeout=300)
            except subprocess.TimeoutExpired:
                self.fail("Import did not finish in time")
            self.check_new_and_removed_users((4 * n_users_of_each_role), 0)

            filter_src = filter_format(
                "(objectClass=ucsschoolType)(ucsschoolSourceUID=%s)", (source_uid,)
            )
            for person in person_list:
                filter_s = "(&{}{})".format(
                    filter_src, filter_format("(ucsschoolRecordUID=%s)", (person.record_uid,))
                )
                res = self.lo.search(filter=filter_s)
                if len(res) != 1:
                    self.fail(
                        "Search with filter={!r} did not return 1 result:\n{}".format(
                            filter_s, "\n".join(repr(res))
                        )
                    )
                try:
                    dn = res[0][0]
                    attrs = res[0][1]
                except KeyError as exc:
                    self.log.exception("Error searching for user: %s res=%r", exc, res)
                    raise
                username = attrs["uid"][0].decode("UTF-8")
                email = attrs["mailPrimaryAddress"][0].decode("UTF-8")
                self.log.debug("role=%r username=%r email=%r dn=%r", person.role, username, email, dn)
                person.update(dn=dn, username=username, mail=email)
                person.update(firstname=person.firstname.strip(), lastname=person.lastname.strip())
                person.verify()

            self.log.info("*** Modify each user...")

            for person in person_list:
                if person.role == "student":
                    person.school_classes = {}
                if person.role != "staff":
                    person.append_random_class()

            self.create_csv_file(
                person_list=person_list, mapping=config["csv"]["mapping"], fn_csv=fn_csv
            )
            # save ldap state for later comparison
            self.save_ldap_status()

            # start import
            self.run_import(["-c", fn_config])

            # check for new users in LDAP
            self.check_new_and_removed_users(0, 0)

            # verify LDAP attributes
            for person in person_list:
                person.verify()

            self.log.info("*** Remove all users...")

            # mark as removed
            for person in person_list:
                person.set_mode_to_delete()
            self.create_csv_file(person_list=[], mapping=config["csv"]["mapping"], fn_csv=fn_csv)
            # save ldap state for later comparison
            self.save_ldap_status()

            # start import
            self.run_import(["-c", fn_config])

            # check for new users in LDAP
            self.check_new_and_removed_users(0, 4 * n_users_of_each_role)

            # verify LDAP attributes
            for person in person_list:
                person.verify()


if __name__ == "__main__":
    Test().run()
