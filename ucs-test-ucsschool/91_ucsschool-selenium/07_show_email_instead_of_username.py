#!/usr/share/ucs-test/runner /usr/share/ucs-test/playwright
# -*- coding: utf-8 -*-
## desc: |
##  Test that ucsschool/umc/show-email-instead-of-username makes the
##  UCS@school UMC modules identify users by their primary email address instead
##  of the username: the user wizard grid, the legal guardian / legal ward
##  selection of a user, and the password reset (schoolusers) grid.
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest, ucsschool,ucsschool_selenium,ucs-school-umc-wizards,ucs-school-umc-users]
## exposure: dangerous
## packages:
##   - ucs-school-multiserver | ucs-school-singleserver


import subprocess
import time
from collections import namedtuple

import pytest
from playwright.sync_api import expect

import univention.testing.ucsschool.ucs_test_school as utu
from univention.config_registry import handler_set, handler_unset
from univention.testing.browser.lib import UCSLanguage, UMCBrowserTest
from univention.testing.ucsschool.importusers import get_mail_domain

UCR_VAR = "ucsschool/umc/show-email-instead-of-username"

Env = namedtuple("Env", ["school", "ward_mail", "unassigned_mail", "guardian_mail"])


def _restart_umc():
    subprocess.call(["/bin/systemctl", "restart", "univention-management-console-server"])
    # wait for the UMC server to be ready again
    time.sleep(5)


@pytest.fixture(scope="module")
def email_mode_env():
    """
    Create the users (with email addresses) and enable the UCR variable.

    The UMC server is restarted so its cached UCR is refreshed. Everything is
    reverted and cleaned up on teardown.
    """
    with utu.UCSTestSchool() as schoolenv:
        mail_domain = get_mail_domain()
        ward_mail = "stu-ward-pw@%s" % mail_domain
        unassigned_mail = "stu-free-pw@%s" % mail_domain
        guardian_mail = "lg-mail-pw@%s" % mail_domain

        if schoolenv.ucr["server/role"] == "domaincontroller_slave":
            name_edudc = schoolenv.ucr["hostname"]
        else:
            name_edudc = None
        school, _ = schoolenv.create_ou(name_edudc=name_edudc)

        # one student assigned as the guardian's legal ward, one left unassigned
        # (the "Add objects" dialog hides already-assigned users)
        _ward_name, ward_dn = schoolenv.create_user(
            school, username="stu-ward-pw", firstname="StuWard", lastname="Test", mailaddress=ward_mail
        )
        schoolenv.create_user(
            school,
            username="stu-free-pw",
            firstname="StuFree",
            lastname="Test",
            mailaddress=unassigned_mail,
        )
        schoolenv.create_user(
            school,
            username="lg-mail-pw",
            firstname="LgMail",
            lastname="Test",
            mailaddress=guardian_mail,
            is_legal_guardian=True,
            legal_wards=[ward_dn],
        )

        handler_set(["%s=yes" % UCR_VAR])
        _restart_umc()
        try:
            yield Env(school, ward_mail, unassigned_mail, guardian_mail)
        finally:
            handler_unset([UCR_VAR])
            _restart_umc()


def test_user_wizard_email_display(umc_browser_test: UMCBrowserTest, email_mode_env) -> None:
    env = email_mode_env
    ward_username_label = "(stu-ward-pw)"
    unassigned_username_label = "(stu-free-pw)"
    guardian_label = "LgMail Test (%s)" % env.guardian_mail

    def no_school_users_found_popup_handler():
        page.get_by_label("Cancel").click()

    umc_browser_test.set_language(UCSLanguage.EN_US)
    umc_browser_test.login()
    page = umc_browser_test.page
    page.add_locator_handler(
        page.get_by_role("heading", name="No school users found"),
        no_school_users_found_popup_handler,
    )
    page.get_by_role("button", name="School administration").click()
    page.get_by_text("Users (schools)Management of").click()
    page.get_by_role("textbox", name="School").click()
    page.get_by_role("textbox", name="School").fill(env.school)
    page.get_by_role("button", name="Next").click()

    # 1) list view: the grid identifies the ward student by email, not username
    expect(page.get_by_role("gridcell", name=env.ward_mail)).to_be_visible(timeout=30000)
    expect(page.get_by_text(ward_username_label)).to_have_count(0)

    # 2) the guardian's already-assigned legal ward is shown by email
    page.get_by_text(guardian_label).click()
    expect(page.get_by_role("gridcell", name=env.ward_mail)).to_be_visible(timeout=30000)
    expect(page.get_by_text(ward_username_label)).to_have_count(0)

    # 3) the "Add objects" dialog when adding a legal ward lists the (still
    #    unassigned) student by email, not username
    page.get_by_role("button", name="Add").click()
    page.get_by_role("textbox", name="Name", exact=True).fill("stu-free-pw")
    page.get_by_role("dialog", name="Add objects").get_by_label("", exact=True).click()  # Search
    dialog = page.get_by_role("dialog", name="Add objects")
    expect(dialog.get_by_text("(%s)" % env.unassigned_mail)).to_be_visible(timeout=30000)
    expect(dialog.get_by_text(unassigned_username_label)).to_have_count(0)


def test_password_reset_grid_email_display(umc_browser_test: UMCBrowserTest, email_mode_env) -> None:
    env = email_mode_env
    ward_username_label = "(stu-ward-pw)"

    umc_browser_test.set_language(UCSLanguage.EN_US)
    umc_browser_test.login()
    page = umc_browser_test.page
    page.get_by_role("button", name="School administration").click()
    page.get_by_text("Passwords (students)Reset passwords").click()
    page.get_by_role("textbox", name="School").click()
    page.get_by_role("textbox", name="School").fill(env.school)
    # search for the ward student (also commits the school combobox value)
    page.get_by_role("textbox", name="Name", exact=True).fill("stu-ward-pw")
    page.get_by_role("textbox", name="Name", exact=True).press("Enter")

    # the password reset grid identifies the student by email, not username
    expect(page.get_by_role("gridcell", name=env.ward_mail)).to_be_visible(timeout=30000)
    expect(page.get_by_text(ward_username_label)).to_have_count(0)
