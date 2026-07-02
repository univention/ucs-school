#!/usr/share/ucs-test/runner /usr/share/ucs-test/playwright
# -*- coding: utf-8 -*-
## desc: Test the legal guardian feature
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest, ucsschool,ucsschool_selenium,ucs-school-umc-wizards]
## exposure: dangerous
## packages:
##   - ucs-school-multiserver | ucs-school-singleserver


import time

from playwright.sync_api import expect

from univention.testing.browser.lib import UCSLanguage, UMCBrowserTest


def test_legal_guardian(umc_browser_test: UMCBrowserTest) -> None:
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
    page.get_by_role("textbox", name="School").fill("Demo School")
    page.get_by_role("button", name="Next").click()
    page.get_by_role("button", name="Add").click()
    page.get_by_role("textbox", name="Role").click()
    page.get_by_role("textbox", name="Role").press("ArrowDown")
    page.get_by_role("option", name="Student").click()
    page.get_by_role("button", name="Next").click()
    page.get_by_role("textbox", name="Firstname *").click()
    page.get_by_role("textbox", name="Firstname *").fill("stu-test-pw")
    page.get_by_role("textbox", name="Lastname *").click()
    page.get_by_role("textbox", name="Lastname *").fill("stu-test-pw")
    page.get_by_role("textbox", name="Username *").click()
    page.get_by_role("textbox", name="Username *").fill("stu-test-pw")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Cancel").click()
    page.get_by_role("button", name="Add").click()
    page.get_by_role("textbox", name="Role").click()
    page.get_by_role("textbox", name="Role").press("ArrowDown")
    page.get_by_role("option", name="Legal guardian").click()
    page.get_by_role("button", name="Next").click()
    page.get_by_role("textbox", name="Firstname *").click()
    page.get_by_role("textbox", name="Firstname *").fill("lg-test-pw")
    page.get_by_role("textbox", name="Lastname *").click()
    page.get_by_role("textbox", name="Lastname *").fill("lg-test-pw")
    page.get_by_role("textbox", name="Username *").click()
    page.get_by_role("textbox", name="Username *").fill("lg-test-pw")
    page.get_by_role("button", name="Add").click()
    page.get_by_role("textbox", name="Name", exact=True).fill("stu-test-pw")
    page.get_by_role("dialog", name="Add objects").get_by_label("", exact=True).click()  # Search
    page.get_by_role("checkbox", name="Row 1, multiple selection").click()
    page.get_by_role("dialog", name="Add objects").get_by_label("Add").click()
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Cancel").click()
    users_grid = page.get_by_label("Users (schools)Demo School")
    users_grid.get_by_text("stu-test-pw stu-test-pw (stu-").click()
    expect(page.get_by_role("gridcell", name="lg-test-pw")).to_be_visible()
    page.get_by_role("button", name="Cancel").click()
    users_grid.get_by_text("lg-test-pw lg-test-pw (lg-").click()
    page.get_by_role("button", name="Cancel").click()
    page.get_by_role("button", name="Delete").click()
    page.get_by_role("dialog", name="Confirmation").get_by_label("Delete").click()
    users_grid.get_by_text("stu-test-pw stu-test-pw (stu-").click()
    time.sleep(5)  # Wait for the page to render, because we have a negative check next.
    expect(page.get_by_role("gridcell", name="lg-test-pw")).to_have_count(0)
    page.get_by_role("button", name="Cancel").click()
    page.get_by_role("button", name="Delete").click()
    page.get_by_role("dialog", name="Confirmation").get_by_label("Delete").click()
