#!/usr/share/ucs-test/runner /usr/bin/pytest -l -s -v
## -*- coding: utf-8 -*-
## desc: test create_demoportal
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: safe
## packages:
##   - ucs-school-master

import os
import imp
from io import StringIO
from mock import call, patch
import pytest
from univention.admin.handlers import simpleLdap
from univention.admin.uldap import getAdminConnection
import univention.testing.ucr as ucr_test
import univention.testing.strings as uts
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
		is_single_master = ucr.is_true('ucsschool/singlemaster', False)
		if is_single_master:
			return ucr.get('hostname')
		else:
			return "DEMOSCHOOL"


@pytest.fixture()
def random_school():
	return SchoolMock()


@pytest.fixture()
def entries():
	return [
		[uts.random_name() for _ in range(7)] + ["domainadmin"],
		[uts.random_name() for _ in range(7)] + ["domainadmin"],
		[uts.random_name() for _ in range(7)] + ["domainadmin"],
	]


@pytest.fixture()
def categories():
	return [
		[uts.random_name() for _ in range(3)],
		[uts.random_name() for _ in range(3)],
		[uts.random_name() for _ in range(3)],
	]


def first_item_if_list(obj):
	if isinstance(obj, list):
		return obj[0]
	else:
		return obj


def check_create_demoportal_call_lists(
		random_school, demo_password, teacher_mock, student_mock, staff_mock, school_class_mock, from_binddn_mock
):
	assert teacher_mock.call_args_list == [
		call(firstname='Demo', lastname='Teacher', name='demo_teacher', password=demo_password, school=random_school.name),
		call(firstname='Demo', lastname='Admin', name='demo_admin', password=demo_password, school=random_school.name)
	]
	assert student_mock.call_args_list == [call(
		firstname='Demo',
		lastname='Student',
		name='demo_student',
		password=demo_password,
		school=random_school.name)]
	assert staff_mock.call_args_list == [call(
		firstname='Demo',
		lastname='Staff',
		name='demo_staff',
		password=demo_password,
		school=random_school.name)]
	assert school_class_mock.call_args_list == [call(
		name='{}-Democlass'.format(random_school.name),
		school=random_school.name)]
	assert from_binddn_mock.call_args_list == [call(lo)]


@patch("subprocess.check_call")
def test_create_school_doesnt_create_existing_school(
		subprocess_check_call_mock,
		random_school,
		create_demoportal_module,
):
	with patch.object(create_demoportal_module, "SCHOOL", (random_school.name, random_school.display_name)), \
			patch("ucsschool.lib.models.School.from_binddn", return_value=[random_school]) as from_binddn_mock, \
			patch.object(create_demoportal_module, "SchoolClass") as school_class_mock, \
			patch.object(create_demoportal_module, "Staff") as staff_mock, \
			patch.object(create_demoportal_module, "Student") as student_mock, \
			patch.object(create_demoportal_module, "Teacher") as teacher_mock, \
			patch.object(create_demoportal_module.module_groups, "lookup", return_value=[SchoolMock()]), \
			patch.object(create_demoportal_module, "demo_password", uts.random_string()) as demo_password, \
			patch.object(create_demoportal_module, "lo", lo):
		create_demoportal_module.create_school()

	check_create_demoportal_call_lists(
		random_school, demo_password, teacher_mock, student_mock, staff_mock, school_class_mock, from_binddn_mock
	)
	subprocess_check_call_mock.assert_not_called()  # when school exists, "create_ou" script should not be executed


@patch("subprocess.check_call")
def test_create_school_creates_missing_school(
		subprocess_check_call_mock,
		random_school,
		create_demoportal_module,
		hostname_demoschool
):
	with patch.object(create_demoportal_module, "SCHOOL", (random_school.name, random_school.display_name)), \
			patch("ucsschool.lib.models.School.from_binddn", return_value=[]) as from_binddn_mock, \
			patch.object(create_demoportal_module, "SchoolClass") as school_class_mock, \
			patch.object(create_demoportal_module, "Staff") as staff_mock, \
			patch.object(create_demoportal_module, "Student") as student_mock, \
			patch.object(create_demoportal_module, "Teacher")as teacher_mock, \
			patch.object(create_demoportal_module.module_groups, "lookup", return_value=[SchoolMock()]), \
			patch.object(create_demoportal_module, "demo_password", uts.random_string()) as demo_password, \
			patch.object(create_demoportal_module, "lo", lo):
		create_demoportal_module.create_school()

	check_create_demoportal_call_lists(
		random_school, demo_password, teacher_mock, student_mock, staff_mock, school_class_mock, from_binddn_mock
	)
	# when does not school exists, "create_ou" script should be executed
	assert subprocess_check_call_mock.call_args_list == [call([
		'python', '/usr/share/ucs-school-import/scripts/create_ou', '--displayName={}'.format(random_school.display_name),
		'--alter-dhcpd-base=false', random_school.name, hostname_demoschool])]


def test_create_portal(create_demoportal_module, entries, categories):
	with patch.object(create_demoportal_module.module_groups, "lookup", return_value=[SchoolMock()]), \
			patch.object(create_demoportal_module, "already_exists", return_value=True) as already_exists, \
			patch.object(create_demoportal_module, "ENTRIES", entries), \
			patch.object(create_demoportal_module, "CATEGORIES", categories), \
			patch.object(create_demoportal_module, "open") as open_mock:
		# context manager and iterator protocols for open()
		open_mock.return_value.__enter__ = lambda x: StringIO(unic(uts.random_string()))
		open_mock.return_value.__exit__ = open_mock.close()

		create_demoportal_module.create_portal()

	udm_objects = []
	for acall in already_exists.call_args_list:
		args, kwargs = acall
		assert isinstance(args[0], simpleLdap)
		udm_objects.append(args[0])
	expected = [
		{"module": "settings/portal_entry", "props": {"name": entry[0], "link": entry[5]}}
		for entry in entries
	]
	expected.extend([
		{"module": "settings/portal_category", "props": {"name": category[0]}}
		for category in categories
	])
	expected.append({"module": "settings/portal", "props": {"name": "ucsschool_demo_portal"}})
	assert len(udm_objects) == len(expected)
	for udm_object, expect in zip(udm_objects, expected):
		assert udm_object.module == expect["module"]
		for prop, val in expect["props"].items():
			assert first_item_if_list(udm_object[prop]) == val
