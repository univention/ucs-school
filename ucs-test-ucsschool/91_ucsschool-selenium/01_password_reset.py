#!/usr/share/ucs-test/runner /usr/share/ucs-test/selenium
# -*- coding: utf-8 -*-
## desc: Test the password reset module
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_selenium, ucs-school-umc-users]
## exposure: dangerous
## packages:
##   - ucs-school-multiserver | ucs-school-singleserver | ucs-school-replica

import univention.testing.ucsschool.ucs_test_school as utu
from univention.admin import localization
from univention.testing import selenium, utils

translator = localization.translation("ucs-test-selenium")
_ = translator.translate


def get_pw_change_time(userdn, lo):
    try:
        pw_change = lo.getAttr(userdn, "pwdChangedTime")[0]
    except IndexError:
        pw_change = b"0Z"
    return pw_change


def compare_pw_change_times(last_pw_change, userdn, lo):
    if not last_pw_change < get_pw_change_time(userdn, lo):
        raise ValueError


class UMCTester(object):
    def test_umc(self):
        with utu.UCSTestSchool() as schoolenv:
            reset_password = "uni1vention1"
            if schoolenv.ucr["server/role"] == "domaincontroller_slave":
                name_edudc = schoolenv.ucr["hostname"]
            else:
                name_edudc = None
            schoolname, schooldn = schoolenv.create_ou(name_edudc=name_edudc)
            username, userdn = schoolenv.create_user(schoolname)
            last_pw_change = get_pw_change_time(userdn, schoolenv.lo)

            # Reset password for user
            self.selenium.do_login()
            self.selenium.open_module(_("Passwords (students)"), wait_for_standby=False)
            self.selenium.wait_until_standby_animation_appears_and_disappears(
                appear_timeout=15, disappear_timeout=60
            )
            self.selenium.enter_input_combobox("school", schoolname)
            self.selenium.submit_input("pattern")
            self.selenium.wait_for_text(username, timeout=60)
            self.selenium.click_checkbox_of_grid_entry(username)
            self.selenium.click_button(_("Reset password"))
            self.selenium.click_text(_("User has to change password on next login"))
            self.selenium.enter_input("newPassword", reset_password)
            self.selenium.click_button("Reset")
            utils.retry_on_error(
                lambda: compare_pw_change_times(last_pw_change, userdn, schoolenv.lo),
                exceptions=(ValueError,),
                retry_count=5,
            )
            self.selenium.end_umc_session()
            self.selenium.do_login(username=username, password=reset_password)
            self.selenium.end_umc_session()

            # Reset password for user and require password reset
            reset_password = "uni2vention2"
            self.selenium.do_login()
            self.selenium.open_module(_("Passwords (students)"), wait_for_standby=False)
            self.selenium.wait_until_standby_animation_appears_and_disappears(
                appear_timeout=15, disappear_timeout=60
            )
            self.selenium.enter_input_combobox("school", schoolname)
            self.selenium.submit_input("pattern")
            self.selenium.wait_for_text(username, timeout=60)
            self.selenium.click_checkbox_of_grid_entry(username)
            self.selenium.click_button(_("Reset password"))
            self.selenium.enter_input("newPassword", reset_password)
            self.selenium.click_button("Reset")
            utils.verify_ldap_object(userdn, {"shadowMax": ("1",)}, retry_count=3)
            self.selenium.end_umc_session()
            self.selenium.do_login(username, reset_password, check_successful_login=False)
            self.selenium.wait_for_text("The password has expired and must be renewed.", timeout=10)
            self.selenium.end_umc_session()

            # TODO: Test for the proper separation of users regarding schools and working groups?


if __name__ == "__main__":
    with selenium.UMCSeleniumTest() as s:
        umc_tester = UMCTester()
        umc_tester.selenium = s

        umc_tester.test_umc()
