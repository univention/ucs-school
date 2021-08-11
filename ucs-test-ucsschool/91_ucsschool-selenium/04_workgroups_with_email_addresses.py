#!/usr/share/ucs-test/runner /usr/share/ucs-test/selenium
# -*- coding: utf-8 -*-
## desc: Test the creation of workgroups with email addresses.
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_selenium]
## exposure: dangerous
## packages:
##   - ucs-school-master | ucs-school-singlemaster

import time

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.group import WorkGroup
from ucsschool.lib.models.share import WorkGroupShare
from univention.admin import localization
from univention.admin.uldap import getAdminConnection
from univention.config_registry import handler_set, handler_unset
from univention.testing import selenium
from univention.testing.ucr import UCSTestConfigRegistry
from univention.testing.udm import UCSTestUDM

translator = localization.translation("ucs-test-selenium")
_ = translator.translate


class UMCTester(object):
    def __init__(self, *args, **kwargs):
        self.selenium = None  # type: selenium.UMCSeleniumTest
        super(UMCTester, self).__init__(*args, **kwargs)

    def open_wg_module(self, open_edit_dialog=True):
        self.selenium.open_module(_("Administrate workgroups"), wait_for_standby=False)
        time.sleep(1)
        self.selenium.wait_until_all_standby_animations_disappeared()
        if open_edit_dialog:
            self.selenium.click_button(_("Add workgroup"))
            self.selenium.wait_for_text(_("Create share"), timeout=5)

    def enter_wg_details(
        self, school, name, create_share=True, create_email=True, group_senders=[], user_senders=[]
    ):
        self.selenium.enter_input_combobox("school", school)
        self.selenium.enter_input("name", name)
        if not create_share:
            self.selenium.click_text(_("Create share"))
        if create_email:
            self.selenium.click_text(_("Activate Email Address"))

    @staticmethod
    def check_wg(lo, school, name, share_exists=True, email="", group_senders=[], user_senders=[]):
        work_group = WorkGroup.get_all(lo, school, filter_str="name={}-{}".format(school, name))[0]
        assert work_group.name == "{}-{}".format(school, name), "{} != {}".format(
            work_group.name, "{}-{}".format(school, name)
        )
        assert work_group.email == email, "{} != {}".format(work_group.email, email)
        assert work_group.allowed_email_senders_groups == group_senders, "{} != {}".format(
            work_group.allowed_email_senders_groups, group_senders
        )
        assert work_group.allowed_email_senders_users == user_senders, "{} != {}".format(
            work_group.allowed_email_senders_users, user_senders
        )
        wg_share = WorkGroupShare.from_school_group(work_group)
        assert wg_share.exists(lo) == share_exists, "{} != {}".format(wg_share.exists(lo), share_exists)

    def test_umc(self):
        with utu.UCSTestSchool() as schoolenv, UCSTestConfigRegistry(), UCSTestUDM() as udm:
            lo, po = getAdminConnection()
            handler_set(["ucsschool/workgroups/autosearch=no"])
            school_name, schooldn = schoolenv.create_ou()

            #  Test that mailaddress checkbox is not visible if UCR empty
            handler_unset(["ucsschool/workgroups/mailaddress"])
            self.selenium.do_login()
            self.open_wg_module()
            assert not self.selenium.elements_visible("//label[text() = 'Activate Email Address']")

            #  Test that mailaddress is visible if UCR is set
            handler_set(["ucsschool/workgroups/mailaddress={ou}-{name}@test.de"])
            self.open_wg_module()
            assert self.selenium.elements_visible("//label[text() = 'Activate Email Address']")

            #  Test for creating a workgroup without share and email address
            wg_name = uts.random_string(6)
            self.enter_wg_details(school_name, wg_name, False, False)
            self.selenium.click_button(_("Save changes"))
            self.selenium.wait_for_text(
                _(
                    "This module allows to create, modify and delete class comprehensive workgroups. "
                    "Arbitrary students and teacher of the school can be selected as group members."
                )
            )
            self.check_wg(lo, school_name, wg_name, False, None, [], [])

            #  Test for creating a workgroup with share and email address
            udm.create_object("mail/domain", name="test.de")
            self.open_wg_module()
            wg_name2 = uts.random_string(6)
            self.enter_wg_details(school_name, wg_name2, True, True)
            self.selenium.click_button(_("Save changes"))
            self.selenium.wait_for_text(
                _(
                    "This module allows to create, modify and delete class comprehensive workgroups. "
                    "Arbitrary students and teacher of the school can be selected as group members."
                )
            )
            self.check_wg(
                lo, school_name, wg_name2, True, "{}-{}@test.de".format(school_name, wg_name2), [], []
            )

            #  Test that email is still shown if UCR is deactivated, but toggle is gone
            handler_unset(["ucsschool/workgroups/mailaddress"])
            self.open_wg_module(False)
            self.selenium.enter_input_combobox("school", school_name)
            self.selenium.submit_input("pattern")
            self.selenium.click_text(wg_name2)
            time.sleep(5)
            assert self.selenium.elements_visible("//input[@name = 'email']")
            assert not self.selenium.elements_visible("//label[text() = 'Activate Email Address']")


if __name__ == "__main__":
    with selenium.UMCSeleniumTest() as s:
        umc_tester = UMCTester()
        umc_tester.selenium = s

        umc_tester.test_umc()
