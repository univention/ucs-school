#!/usr/share/ucs-test/runner /usr/share/ucs-test/playwright
# -*- coding: utf-8 -*-
## desc: |
##  Click through every flavor of the UMC module schoolgroups (ucs-school-umc-groups):
##  "Assigning teachers", "Assigning classes", "Administrate workgroups" and, as a teacher,
##  "Edit workgroups". Each test reopens the saved object and checks the result in LDAP.
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest, ucsschool,ucsschool_selenium,ucs-school-umc-groups]
## bugs: [55267, 56589]
## exposure: dangerous
## packages:
##   - ucs-school-multiserver | ucs-school-singleserver

import subprocess
import time
from typing import NamedTuple

import pytest
from ldap.filter import filter_format
from playwright.sync_api import Locator, Page, expect

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.share import WorkGroupShare
from univention.admin.uldap import access
from univention.config_registry import handler_set, handler_unset
from univention.testing import utils
from univention.testing.browser.lib import UCSLanguage, UMCBrowserTest
from univention.testing.ucsschool.importusers import get_mail_domain

SENDER_USERS = "Restrict permission to send emails to this group to the following users"
SENDER_GROUPS = "Restrict permission to send emails to this group to the following groups"


class User(NamedTuple):
    name: str
    dn: str


class Env(NamedTuple):
    lo: access
    school: str
    mail_domain: str
    klass: str
    klass_dn: str
    klass_free: str
    wg: str
    wg_dn: str
    teacher_wg: User
    teacher_free: User
    teacher_cls: User
    student_member: User
    student_free: User
    sender_deleted: User


def _restart_umc():
    subprocess.call(["/bin/systemctl", "restart", "univention-management-console-server"])
    time.sleep(5)


def _restrict_teachers_to_edit_workgroups(schoolenv, school, ou_dn):
    """
    Point the OU's teacher group to a copy of the teacher policy without "Workgroup administration".

    "Administrate workgroups" overwrites "Edit workgroups", so teachers only see the latter without it.
    Returns the changed (group DN, old policy DN, new policy DN) tuples for the teardown.
    """
    base = schoolenv.ucr["ldap/base"]
    default_dn = "cn=ucsschool-umc-teachers-default,cn=UMC,cn=policies,%s" % base
    operations = "cn=operations,cn=UMC,cn=univention,%s" % base
    allow = [
        dn.decode("UTF-8")
        for dn in schoolenv.lo.get(default_dn)["umcPolicyGrantedOperationSet"]
        if not dn.decode("UTF-8").lower().startswith("cn=schoolgroups-workgroup-admin,")
    ]
    allow.append("cn=schoolgroups-workgroup,%s" % operations)
    policy_dn = schoolenv.udm.create_object(
        "policies/umc",
        position="cn=UMC,cn=policies,%s" % base,
        name="ucsschool-umc-teachers-%s-test" % school,
        allow=sorted(set(allow)),
    )
    swapped = []
    for group_dn, attrs in schoolenv.lo.search(
        filter_format("(univentionPolicyReference=%s)", [default_dn]),
        base=ou_dn,
        attr=["univentionPolicyReference"],
    ):
        old = next(
            ref
            for ref in attrs["univentionPolicyReference"]
            if ref.decode("UTF-8").lower() == default_dn.lower()
        )
        schoolenv.lo.modify(group_dn, [("univentionPolicyReference", old, policy_dn.encode("UTF-8"))])
        swapped.append((group_dn, old, policy_dn.encode("UTF-8")))
    assert swapped, "no group in %s references %s" % (ou_dn, default_dn)
    return swapped


@pytest.fixture(scope="module")
def groups_env():
    with utu.UCSTestSchool() as schoolenv:
        if schoolenv.ucr["server/role"] == "domaincontroller_slave":
            name_edudc = schoolenv.ucr["hostname"]
        else:
            name_edudc = None
        school, ou_dn = schoolenv.create_ou(name_edudc=name_edudc)
        mail_domain = get_mail_domain()

        teacher_wg = User(*schoolenv.create_user(school, is_teacher=True))
        teacher_free = User(*schoolenv.create_user(school, is_teacher=True))
        teacher_cls = User(*schoolenv.create_user(school, is_teacher=True))
        student_member = User(*schoolenv.create_user(school))
        student_free = User(*schoolenv.create_user(school))
        klass, klass_dn = schoolenv.create_school_class(school, users=[student_member.dn, teacher_wg.dn])
        klass_free, _ = schoolenv.create_school_class(school, users=[student_free.dn, teacher_free.dn])
        sender_deleted_dn, sender_deleted_name = schoolenv.udm.create_user()
        # create_workgroup() can't set the email attributes
        wg = "%s-%s" % (school, uts.random_name())
        wg_obj = WorkGroup(
            name=wg,
            school=school,
            users=[student_member.dn, teacher_wg.dn],
            email="%s@%s" % (wg, mail_domain),
            allowed_email_senders_users=[teacher_wg.dn, sender_deleted_dn],
            allowed_email_senders_groups=[klass_dn],
        )
        wg_obj.create(schoolenv.lo)
        schoolenv.udm.remove_object("users/user", dn=sender_deleted_dn)

        swapped = _restrict_teachers_to_edit_workgroups(schoolenv, school, ou_dn)
        try:
            with ucr_test.UCSTestConfigRegistry():
                handler_set(["ucsschool/workgroups/mailaddress={ou}-{name}@%s" % mail_domain])
                utils.wait_for_replication()
                # the module reads the mail address pattern from its cached UCR
                _restart_umc()
                yield Env(
                    schoolenv.lo,
                    school,
                    mail_domain,
                    klass,
                    klass_dn,
                    klass_free,
                    wg,
                    wg_obj.dn,
                    teacher_wg,
                    teacher_free,
                    teacher_cls,
                    student_member,
                    student_free,
                    User(sender_deleted_name, sender_deleted_dn),
                )
        finally:
            for group_dn, old, new in swapped:
                schoolenv.lo.modify(group_dn, [("univentionPolicyReference", new, old)])
            _restart_umc()


def relative(group_name, school):
    return group_name[len(school) + 1 :]


def open_module(umc: UMCBrowserTest, name: str, school: str | None = None) -> Page:
    umc.open_module(name)
    page = umc.page
    if school:
        school_box = page.get_by_role("textbox", name="School")
        # the form selects the first school once its values are loaded, which would override ours
        expect(school_box).not_to_have_value("")
        school_box.fill(school)
        page.get_by_role("option", name=school, exact=True).click()
    return page


def row(scope: Page | Locator, text: str) -> Locator:
    # a dgrid row matches twice: the row and its inner table row
    return scope.get_by_role("row").filter(has_text=text).first


def expect_class_cell(scope: Locator, env: Env) -> None:
    """The class is labeled like in the group search dialog, without the school prefix."""
    expect(row(scope, relative(env.klass, env.school))).to_be_visible()
    expect(row(scope, env.klass)).to_have_count(0)


def select_and_edit(page: Page, row_text: str) -> None:
    row(page, row_text).click()
    page.get_by_role("button", name="Edit").click()


def multi_select(page: Page, label: str) -> Locator:
    """The member widget (grid with its "Add" and "Remove" buttons) labeled `label`."""
    label_node = page.locator("label").filter(has_text=label).first
    expect(label_node).to_be_visible()
    widget_id = label_node.get_attribute("for")
    assert widget_id, "label %r is not linked to a widget" % label
    return page.locator("#" + widget_id)


def add_via_dialog(page: Page, widget: Locator, pick=(), absent=(), group: str | None = None) -> None:
    """
    Search "Add objects", check `absent` isn't offered, and add `pick`.

    `group` selects a class in "User group or class". The default entry ("All students" or
    "All teachers") limits the user type itself, so only a class can show a wrong user type.
    """
    widget.get_by_role("button", name="Add").click()
    dialog = page.get_by_role("dialog", name="Add objects")
    if group:
        dialog.get_by_role("textbox", name="User group or class").press("ArrowDown")
        page.get_by_role("option", name=group, exact=True).click()
    dialog.get_by_label("", exact=True).click()  # Search
    for text in pick:
        expect(row(dialog, text)).to_be_visible()
        row(dialog, text).get_by_role("checkbox").click()
    # the results are rendered once the first expected row is visible
    for text in absent:
        expect(dialog.get_by_role("row").filter(has_text=text)).to_have_count(0)
    dialog.get_by_role("button", name="Add").click()
    expect(dialog).to_be_hidden()


def save(page: Page) -> None:
    page.get_by_role("button", name="Save changes").click()
    expect(page.get_by_role("button", name="Edit")).to_be_visible()


def test_assign_teachers(umc_browser_test: UMCBrowserTest, groups_env: Env) -> None:
    """
    Add a teacher to a class in "Assigning teachers".

    - Edit the class: "Teachers" lists its teacher.
    - "Add" with another class selected in "User group or class": the dialog offers the teacher of
      that class, but not its student.
    - Save: the class has the added teacher and keeps its teacher and student.
    - Edit the class again: "Teachers" lists both teachers.
    """
    env = groups_env
    umc_browser_test.set_language(UCSLanguage.EN_US)
    umc_browser_test.login()
    page = open_module(umc_browser_test, "Assigning teachers", env.school)

    select_and_edit(page, relative(env.klass, env.school))
    teachers = multi_select(page, "Teachers")
    expect(row(teachers, "(%s)" % env.teacher_wg.name)).to_be_visible()
    add_via_dialog(
        page,
        teachers,
        pick=["(%s)" % env.teacher_free.name],
        absent=["(%s)" % env.student_free.name],
        group=relative(env.klass_free, env.school),
    )
    save(page)

    users = set(SchoolClass.from_dn(env.klass_dn, env.school, env.lo).users)
    assert {env.teacher_free.dn, env.teacher_wg.dn, env.student_member.dn} <= users, users

    select_and_edit(page, relative(env.klass, env.school))
    teachers = multi_select(page, "Teachers")
    for teacher in (env.teacher_wg, env.teacher_free):
        expect(row(teachers, "(%s)" % teacher.name)).to_be_visible()


def test_assign_classes(umc_browser_test: UMCBrowserTest, groups_env: Env) -> None:
    """
    Add a class to a teacher in "Assigning classes".

    - Edit the teacher and add the class: "Classes" lists it as "<class> (<school>)".
    - Save: the teacher's row shows "<school>: <class>", and the teacher is a member of the class.
    - Edit the teacher again: "Classes" lists the class.
    """
    env = groups_env
    klass = relative(env.klass, env.school)
    umc_browser_test.set_language(UCSLanguage.EN_US)
    umc_browser_test.login()
    page = open_module(umc_browser_test, "Assigning classes", env.school)

    select_and_edit(page, "(%s)" % env.teacher_cls.name)
    classes = multi_select(page, "Classes")
    add_via_dialog(page, classes, pick=[klass])
    expect(row(classes, "%s (%s)" % (klass, env.school))).to_be_visible()
    save(page)

    expect(row(page, "(%s)" % env.teacher_cls.name)).to_contain_text("%s: %s" % (env.school, klass))
    assert env.teacher_cls.dn in SchoolClass.from_dn(env.klass_dn, env.school, env.lo).users

    select_and_edit(page, "(%s)" % env.teacher_cls.name)
    expect(row(multi_select(page, "Classes"), "%s (%s)" % (klass, env.school))).to_be_visible()


def test_administrate_workgroups(umc_browser_test: UMCBrowserTest, groups_env: Env) -> None:
    """
    Create and delete a workgroup in "Administrate workgroups".

    - "Add workgroup": fill in name and description and add a teacher and a student as members.
      "Create share" is checked by default.
    - Check "Activate Email Address": "Email address" shows the address generated from
      ucsschool/workgroups/mailaddress.
    - Save: the grid lists the workgroup, which has the two members, the address and a share.
    - Edit it again: the form shows the description, both members, the checked "Share created"
      and "Activate Email Address", and the address.
    - Delete it: a success message appears and the workgroup is gone.
    """
    env = groups_env
    name = uts.random_name()
    full_name = "%s-%s" % (env.school, name)
    email = "%s@%s" % (full_name, env.mail_domain)
    umc_browser_test.set_language(UCSLanguage.EN_US)
    umc_browser_test.login()
    page = open_module(umc_browser_test, "Administrate workgroups", env.school)

    page.get_by_role("button", name="Add workgroup").click()
    page.get_by_role("textbox", name="Workgroup *").fill(name)
    page.get_by_role("textbox", name="Description").fill("click path")
    add_via_dialog(
        page,
        multi_select(page, "Members"),
        pick=["(%s)" % env.teacher_free.name, "(%s)" % env.student_free.name],
    )
    expect(page.get_by_role("checkbox", name="Create share")).to_be_checked()
    page.get_by_role("checkbox", name="Activate Email Address").click()
    expect(page.get_by_role("textbox", name="Email address")).to_have_value(email)
    save(page)

    wg_row = row(page, name)
    expect(wg_row).to_be_visible()
    wg = WorkGroup.from_dn(WorkGroup(name=full_name, school=env.school).dn, env.school, env.lo)
    assert {env.teacher_free.dn, env.student_free.dn} == set(wg.users), wg.users
    assert wg.email == email
    assert WorkGroupShare.from_school_group(wg).exists(env.lo)

    select_and_edit(page, name)
    expect(page.get_by_role("textbox", name="Description")).to_have_value("click path")
    members = multi_select(page, "Members")
    for user in (env.teacher_free, env.student_free):
        expect(row(members, "(%s)" % user.name)).to_be_visible()
    expect(page.get_by_role("checkbox", name="Share created")).to_be_checked()
    expect(page.get_by_role("checkbox", name="Activate Email Address")).to_be_checked()
    expect(page.get_by_role("textbox", name="Email address")).to_have_value(email)
    page.get_by_role("button", name="Back to overview").click()

    wg_row.get_by_role("checkbox").check()
    page.get_by_role("button", name="Delete").click()
    page.get_by_role("dialog", name="Confirmation").get_by_label("Delete").click()
    expect(page.get_by_text("The workgroups have been deleted successfully")).to_be_visible()
    assert not WorkGroup(name=full_name, school=env.school).exists(env.lo)


@pytest.mark.parametrize("group_mail", [True, False], ids=["with_group_mail", "without_group_mail"])
def test_administrate_workgroups_shows_email_address(
    umc_browser_test: UMCBrowserTest, groups_env: Env, group_mail: bool
) -> None:
    """
    Edit a workgroup with an email address in "Administrate workgroups" (Bug #56589).

    "Email address" shows the address of the workgroup. "Activate Email Address" is checked if
    ucsschool/workgroups/mailaddress is set, and hidden if not. The allowed senders list a deleted
    user by its username (Bug #55267).
    """
    env = groups_env
    with ucr_test.UCSTestConfigRegistry():
        if not group_mail:
            handler_unset(["ucsschool/workgroups/mailaddress"])
        umc_browser_test.set_language(UCSLanguage.EN_US)
        umc_browser_test.login()
        page = open_module(umc_browser_test, "Administrate workgroups", env.school)

        select_and_edit(page, relative(env.wg, env.school))
        expect(page.get_by_role("textbox", name="Email address")).to_have_value(
            "%s@%s" % (env.wg, env.mail_domain)
        )
        checkbox = page.get_by_role("checkbox", name="Activate Email Address", include_hidden=True)
        expect(checkbox).to_be_attached()
        if group_mail:
            expect(checkbox).to_be_checked()
        else:
            expect(checkbox).to_be_hidden()
        expect(row(multi_select(page, SENDER_USERS), env.sender_deleted.name)).to_be_visible()


def test_edit_workgroups_as_teacher(umc_browser_test: UMCBrowserTest, groups_env: Env) -> None:
    """
    Add a student to a workgroup as a teacher in "Edit workgroups".

    - "School administration" lists "Edit workgroups", but not "Administrate workgroups".
    - Edit the workgroup: name and description are disabled. "Students" lists the student
      member, but not the teacher member. "Activate Email Address" is checked and "Email address"
      shows the address. The allowed senders list the teacher by name and the class by its name
      without the school prefix, not by DN,
      and a deleted user by its username.
    - "Add" in "Students": "User group or class" offers "All students", but neither "All teachers"
      nor "All users". With another class selected, the dialog offers its student, but not its
      teacher.
    - "Add" in the allowed sender groups: searching by name finds the workgroup.
    - Save: the workgroup has the added student and keeps its address and allowed senders.
    - Edit it again: "Students" lists both students, and the form still shows the address and the
      allowed senders.
    """
    env = groups_env
    umc_browser_test.set_language(UCSLanguage.EN_US)
    umc_browser_test.login(env.teacher_wg.name, "univention")
    page = umc_browser_test.page

    page.get_by_role("button", name="School administration").click()
    expect(page.get_by_text("Edit workgroups", exact=True)).to_be_visible()
    expect(page.get_by_text("Administrate workgroups", exact=True)).to_have_count(0)

    # a teacher of a single school has no school selection
    page = open_module(umc_browser_test, "Edit workgroups")
    select_and_edit(page, relative(env.wg, env.school))
    expect(page.get_by_role("textbox", name="Workgroup *")).to_be_disabled()
    expect(page.get_by_role("textbox", name="Description")).to_be_disabled()
    students = multi_select(page, "Students")
    expect(row(students, "(%s)" % env.student_member.name)).to_be_visible()
    expect(students.get_by_role("row").filter(has_text="(%s)" % env.teacher_wg.name)).to_have_count(0)
    expect(page.get_by_role("checkbox", name="Activate Email Address")).to_be_checked()
    expect(page.get_by_role("textbox", name="Email address")).to_have_value(
        "%s@%s" % (env.wg, env.mail_domain)
    )
    sender_users = multi_select(page, SENDER_USERS)
    expect(row(sender_users, "(%s)" % env.teacher_wg.name)).to_be_visible()
    expect(row(sender_users, env.sender_deleted.name)).to_be_visible()
    sender_groups = multi_select(page, SENDER_GROUPS)
    expect_class_cell(sender_groups, env)

    students.get_by_role("button", name="Add").click()
    dialog = page.get_by_role("dialog", name="Add objects")
    dialog.get_by_role("textbox", name="User group or class").press("ArrowDown")
    expect(page.get_by_role("option", name="All students")).to_be_visible()
    expect(page.get_by_role("option", name="All teachers")).to_have_count(0)
    expect(page.get_by_role("option", name="All users")).to_have_count(0)
    page.keyboard.press("Escape")
    dialog.get_by_role("button", name="Cancel").last.click()
    add_via_dialog(
        page,
        students,
        pick=["(%s)" % env.student_free.name],
        absent=["(%s)" % env.teacher_free.name],
        group=relative(env.klass_free, env.school),
    )

    # the group search used to fail with "Forbidden" for teachers
    sender_groups.get_by_role("button", name="Add").click()
    # the pattern matches the full group name; the class is hidden, it is a sender already
    dialog.get_by_role("textbox", name="Name", exact=True).fill(env.wg)
    dialog.get_by_label("", exact=True).click()  # Search
    expect(row(dialog, relative(env.wg, env.school))).to_be_visible()
    dialog.get_by_role("button", name="Cancel").last.click()
    save(page)

    wg = WorkGroup.from_dn(env.wg_dn, env.school, env.lo)
    assert {env.student_member.dn, env.teacher_wg.dn, env.student_free.dn} == set(wg.users), wg.users
    assert wg.email == "%s@%s" % (env.wg, env.mail_domain)
    assert set(wg.allowed_email_senders_users) == {env.teacher_wg.dn, env.sender_deleted.dn}
    assert wg.allowed_email_senders_groups == [env.klass_dn]

    select_and_edit(page, relative(env.wg, env.school))
    students = multi_select(page, "Students")
    for student in (env.student_member, env.student_free):
        expect(row(students, "(%s)" % student.name)).to_be_visible()
    expect(page.get_by_role("checkbox", name="Activate Email Address")).to_be_checked()
    expect(page.get_by_role("textbox", name="Email address")).to_have_value(
        "%s@%s" % (env.wg, env.mail_domain)
    )
    expect(row(multi_select(page, SENDER_USERS), "(%s)" % env.teacher_wg.name)).to_be_visible()
    expect_class_cell(multi_select(page, SENDER_GROUPS), env)


def test_edit_workgroups_activates_email_address(
    umc_browser_test: UMCBrowserTest, groups_env: Env
) -> None:
    """
    Activate the email address of a workgroup without one as a teacher in "Edit workgroups".

    The pattern in ucsschool/workgroups/mailaddress changes after the module opened. "Email address"
    shows the address from the new pattern, and the workgroup gets it (Bug #55267).
    """
    env = groups_env
    name = uts.random_name()
    wg = WorkGroup(name="%s-%s" % (env.school, name), school=env.school, users=[env.student_member.dn])
    wg.create(env.lo)
    email = "new-%s-%s@%s" % (env.school, name, env.mail_domain)
    with ucr_test.UCSTestConfigRegistry():
        umc_browser_test.set_language(UCSLanguage.EN_US)
        umc_browser_test.login(env.teacher_wg.name, "univention")
        page = open_module(umc_browser_test, "Edit workgroups")
        expect(row(page, name)).to_be_visible()
        handler_set(["ucsschool/workgroups/mailaddress=new-{ou}-{name}@%s" % env.mail_domain])

        select_and_edit(page, name)
        page.get_by_role("checkbox", name="Activate Email Address").click()
        expect(page.get_by_role("textbox", name="Email address")).to_have_value(email)
        save(page)
        assert WorkGroup.from_dn(wg.dn, env.school, env.lo).email == email
