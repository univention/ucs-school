#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: unittests for authorization of creating class lists using roles and capabilities
## tags: [apptest, ucsschool, base1]
## exposure: dangerous
## packages:
##   - python-ucs-school


from ucsschool.lib.authorization import Capability, is_authorized


def test_teacher_other_school_is_not_authorized(
		context_role,
		capability_create_class_list
):
	cr_teacher_demo = context_role("teacher", [capability_create_class_list], "DEMOSCHOOL")
	cr_school_demo = context_role("school", [], "DEMOSCHOOL2")

	assert not is_authorized([cr_teacher_demo], [cr_school_demo], Capability.CREATE_CLASS_LIST)


def test_teacher_same_school_is_authorized(
		context_role,
		capability_create_class_list
):
	cr_teacher_demo = context_role("teacher", [capability_create_class_list], "DEMOSCHOOL")
	cr_school_demo = context_role("school", [], "DEMOSCHOOL")

	assert is_authorized([cr_teacher_demo], [cr_school_demo], Capability.CREATE_CLASS_LIST)


def test_teacher_without_cap_same_school_is_not_authorized(
		context_role,
):
	cr_teacher_demo = context_role("teacher", [], "DEMOSCHOOL")
	cr_school_demo = context_role("school", [], "DEMOSCHOOL")

	assert not is_authorized([cr_teacher_demo], [cr_school_demo], Capability.CREATE_CLASS_LIST)
