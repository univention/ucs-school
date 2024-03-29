#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test create_demoportal
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: safe
## packages:
##   - ucs-school-singleserver

import imp
import os

import pytest
from mock import call, patch

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
from univention.admin.uldap import getAdminConnection

try:
    unic = unicode
except NameError:
    unic = str


SCRIPT_PATH = "/usr/share/ucs-school-metapackage/scripts/create_demoportal.py"
lo, pos = getAdminConnection()


class SchoolMock:
    def __init__(self, name=None, dn=None, display_name=None):
        self.name = name or uts.random_username()
        if dn:
            self.dn = dn
        else:
            with ucr_test.UCSTestConfigRegistry() as ucr:
                self.dn = "cn={},{}".format(uts.random_username(), ucr["ldap/base"])
        self.display_name = display_name or uts.random_username()


@pytest.fixture(scope="module")
def create_demoportal_module():
    module_name = os.path.basename(SCRIPT_PATH)[:-3]
    module_path = os.path.dirname(SCRIPT_PATH)
    info = imp.find_module(module_name, [module_path])
    return imp.load_module(module_name, *info)


@pytest.fixture(scope="module")
def hostname_demoschool():
    with ucr_test.UCSTestConfigRegistry() as ucr:
        is_single_master = ucr.is_true("ucsschool/singlemaster", False)
        if is_single_master:
            return ucr.get("hostname")
        else:
            return "DEMOSCHOOL"


@pytest.fixture()
def random_school():
    return SchoolMock()


def check_create_demoportal_call_lists(
    random_school,
    demo_password,
    teacher_mock,
    student_mock,
    staff_mock,
    school_class_mock,
    from_binddn_mock,
):
    assert teacher_mock.call_args_list == [
        call(
            firstname="Demo",
            lastname="Teacher",
            name="demo_teacher",
            password=demo_password,
            school=random_school.name,
            email="demo_teacher@demoschool.example.com",
        ),
        call(
            firstname="Demo",
            lastname="Admin",
            name="demo_admin",
            password=demo_password,
            school=random_school.name,
            email="demo_admin@demoschool.example.com",
        ),
    ]
    assert student_mock.call_args_list == [
        call(
            firstname="Demo",
            lastname="Student",
            name="demo_student",
            password=demo_password,
            school=random_school.name,
            email="demo_student@demoschool.example.com",
        )
    ]
    assert staff_mock.call_args_list == [
        call(
            firstname="Demo",
            lastname="Staff",
            name="demo_staff",
            password=demo_password,
            school=random_school.name,
            email="demo_staff@demoschool.example.com",
        )
    ]
    assert school_class_mock.call_args_list == [
        call(name="{}-Democlass".format(random_school.name), school=random_school.name)
    ]
    assert from_binddn_mock.call_args_list == [call(lo)]


@patch("subprocess.check_call")
def test_create_school_doesnt_create_existing_school(
    subprocess_check_call_mock, random_school, create_demoportal_module
):
    with patch.object(
        create_demoportal_module, "SCHOOL", (random_school.name, random_school.display_name)
    ), patch(
        "ucsschool.lib.models.School.from_binddn", return_value=[random_school]
    ) as from_binddn_mock, patch.object(
        create_demoportal_module, "SchoolClass"
    ) as school_class_mock, patch.object(
        create_demoportal_module, "Staff"
    ) as staff_mock, patch.object(
        create_demoportal_module, "Student"
    ) as student_mock, patch.object(
        create_demoportal_module, "Teacher"
    ) as teacher_mock, patch.object(
        create_demoportal_module.module_groups, "lookup", return_value=[SchoolMock()]
    ), patch.object(
        create_demoportal_module, "demo_password", uts.random_string()
    ) as demo_password, patch.object(
        create_demoportal_module, "lo", lo
    ):
        create_demoportal_module.create_school()

    check_create_demoportal_call_lists(
        random_school,
        demo_password,
        teacher_mock,
        student_mock,
        staff_mock,
        school_class_mock,
        from_binddn_mock,
    )
    # when school exists, "create_ou" script should not be executed
    subprocess_check_call_mock.assert_not_called()


@patch("subprocess.check_call")
def test_create_school_creates_missing_school(
    subprocess_check_call_mock, random_school, create_demoportal_module, hostname_demoschool
):
    with patch.object(
        create_demoportal_module, "SCHOOL", (random_school.name, random_school.display_name)
    ), patch(
        "ucsschool.lib.models.School.from_binddn", return_value=[]
    ) as from_binddn_mock, patch.object(
        create_demoportal_module, "SchoolClass"
    ) as school_class_mock, patch.object(
        create_demoportal_module, "Staff"
    ) as staff_mock, patch.object(
        create_demoportal_module, "Student"
    ) as student_mock, patch.object(
        create_demoportal_module, "Teacher"
    ) as teacher_mock, patch.object(
        create_demoportal_module.module_groups, "lookup", return_value=[SchoolMock()]
    ), patch.object(
        create_demoportal_module, "demo_password", uts.random_string()
    ) as demo_password, patch.object(
        create_demoportal_module, "lo", lo
    ):
        create_demoportal_module.create_school()

    check_create_demoportal_call_lists(
        random_school,
        demo_password,
        teacher_mock,
        student_mock,
        staff_mock,
        school_class_mock,
        from_binddn_mock,
    )
    # when does not school exists, "create_ou" script should be executed
    assert subprocess_check_call_mock.call_args_list == [
        call(
            [
                "/usr/share/ucs-school-import/scripts/create_ou",
                "--displayName={}".format(random_school.display_name),
                "--alter-dhcpd-base=false",
                random_school.name,
                hostname_demoschool,
            ]
        )
    ]
