#!/usr/share/ucs-test/runner /usr/share/ucs-test/selenium
# -*- coding: utf-8 -*-
## desc: Test the existence of predefined internetrules
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_selenium,ucs-school-umc-internetrules]
## exposure: dangerous
## packages:
##   - ucs-school-replica | ucs-school-singleserver

from univention.admin import localization
from univention.testing import selenium

translator = localization.translation("ucs-test-selenium")
_ = translator.translate


class UMCTester(object):
    def __init__(self, *args, **kwargs):
        self.selenium = None  # type: selenium.UMCSeleniumTest
        super(UMCTester, self).__init__(*args, **kwargs)

    def test_umc(self):
        self.selenium.do_login()
        self.selenium.open_module(_("Define internet rules"), wait_for_standby=False)
        self.selenium.wait_until_standby_animation_appears_and_disappears(
            appear_timeout=15, disappear_timeout=60
        )
        self.selenium.wait_for_text(_("Unbeschränkt"))
        self.selenium.wait_for_text(_("Kein Internet"))


if __name__ == "__main__":
    with selenium.UMCSeleniumTest() as s:
        umc_tester = UMCTester()
        umc_tester.selenium = s

        umc_tester.test_umc()
