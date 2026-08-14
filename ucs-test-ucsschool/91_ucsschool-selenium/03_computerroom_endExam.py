#!/usr/share/ucs-test/runner /usr/share/ucs-test/selenium
# -*- coding: utf-8 -*-
## desc: Test the computerroom module. Specifically exiting it during exam mode
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_selenium,ucs-school-umc-exam]
## exposure: dangerous
## packages:
##   - ucs-school-replica | ucs-school-singleserver

from datetime import datetime, timedelta

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm
from univention.admin import localization
from univention.testing import selenium
from univention.testing.selenium.utils import expand_path
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.computerroom import Room
from univention.testing.ucsschool.exam import (
    Exam,
    get_s4_rejected,
    wait_replications_check_rejected_uniqueMember,
)

translator = localization.translation("ucs-test-selenium")
_ = translator.translate

# The exam end time is passed as "HH:mm" without a date, and _acquireRoom() in
# computerroom.js resolves it against the current day. An exam that ends after
# midnight therefore looks like it ended hours ago, and the computer room opens
# the "The allowed time for this examination has been reached" dialog as soon as
# the room is acquired - which no step of this test closes. Keep the end time on
# the day the exam starts.
EXAM_DURATION = timedelta(hours=2)
MIN_EXAM_DURATION = timedelta(minutes=15)


def get_exam_end_time(start):
    """Exam end time for an exam started at `start`, never crossing midnight."""
    end_of_day = start.replace(hour=23, minute=59, second=0, microsecond=0)
    if end_of_day - start < MIN_EXAM_DURATION:
        raise RuntimeError(
            "This test cannot run within %d minutes of midnight (it is %s): the exam end time "
            "carries no date, so an exam ending after midnight is treated as already reached by "
            "the computer room module." % (MIN_EXAM_DURATION.total_seconds() // 60, start)
        )
    return min(start + EXAM_DURATION, end_of_day)


class UMCTester(object):
    def _open_computer_room(self, school, room_name):
        self.selenium.open_module(_("Computer room"), wait_for_standby=False)
        self.selenium.wait_until_standby_animation_appears_and_disappears(
            appear_timeout=15, disappear_timeout=60
        )
        self.selenium.wait_for_text(_("School"))
        self.selenium.wait_for_text(_("Computer room"))
        self.selenium.enter_input_combobox("school", school)
        try:
            self.selenium.wait_for_text(room_name, timeout=10)
        except Exception:
            pass
        self.selenium.enter_input_combobox("room", room_name)
        self.selenium.click_button(_("Select room"))
        self.selenium.wait_until_all_dialogues_closed()

    def test_umc(self):
        # fail before the setup instead of in the middle of the exam
        chosen_time = get_exam_end_time(datetime.now())
        with univention.testing.udm.UCSTestUDM() as udm:
            with utu.UCSTestSchool() as schoolenv:
                with ucr_test.UCSTestConfigRegistry() as ucr:
                    open_ldap_co = schoolenv.open_ldap_connection()
                    ucr.load()
                    print(" ** Initial Status")
                    existing_rejects = get_s4_rejected()

                    if ucr.is_true("ucsschool/singlemaster"):
                        edudc = None
                    else:
                        edudc = ucr.get("hostname")
                    school, oudn = schoolenv.create_ou(name_edudc=edudc)
                    klasse_dn = udm.create_object(
                        "groups/group",
                        name="%s-AA1" % school,
                        position="cn=klassen,cn=schueler,cn=groups,%s" % oudn,
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

                    self.selenium.do_login()
                    self._open_computer_room(school, room.name)
                    self.selenium.click_button(
                        _("Close")
                    )  # No exam running, should just close the module
                    self.selenium.wait_for_text(_("Education"))

                    print(" ** After creating the rooms")
                    wait_replications_check_rejected_uniqueMember(existing_rejects)

                    exam = Exam(
                        school=school,
                        room=room.dn,  # room dn
                        examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
                        recipients=[klasse_dn],  # list of classes dns
                    )

                    exam.start()
                    self._open_computer_room(school, room.name)
                    self.selenium.click_button(_("Close"))
                    self.selenium.click_button(_("Cancel"))
                    try:
                        self.selenium.wait_until_all_dialogues_closed()
                    except Exception:
                        pass
                    self.selenium.click_button(_("Close"))
                    self.selenium.click_button(_("Continue without finishing"))
                    self.selenium.wait_for_text(_("Education"))
                    self._open_computer_room(school, room.name)
                    self.selenium.click_button(_("Close"))
                    self.selenium.click_button(
                        "Finish exam",
                        xpath_prefix=expand_path(
                            '//*[text() = "Close exam mode"]/ancestor::*[@containsClass="dijitDialog"]'
                        ),
                    )
                    self.selenium.click_button(
                        "Finish exam",
                        xpath_prefix=expand_path(
                            '//*[text() = "Confirmation"]/ancestor::*[@containsClass="dijitDialog"]'
                        ),
                    )
                    self.selenium.wait_for_text(_("Notification"))


if __name__ == "__main__":
    with selenium.UMCSeleniumTest() as s:
        umc_tester = UMCTester()
        umc_tester.selenium = s

        umc_tester.test_umc()
