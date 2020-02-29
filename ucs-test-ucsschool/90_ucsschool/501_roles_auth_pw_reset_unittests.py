#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: unittests for authorization for password reset using roles and capabilities
## tags: [apptest, ucsschool, base1]
## exposure: dangerous
## packages:
##   - python-ucs-school


from ucsschool.lib.authorization import Capability, is_authorized


def test_teacher_other_school_is_not_authorized(
		context_role,
		capability_pw_reset_student
):
	cr_student_demo = context_role("student", [], "DEMOSCHOOL2")
	cr_teacher_demo = context_role("teacher", [capability_pw_reset_student], "DEMOSCHOOL")

	assert not is_authorized([cr_teacher_demo], [cr_student_demo], Capability.PASSWORD_RESET)


def test_teacher_same_school_is_authorized(
		context_role,
		capability_pw_reset_student
):
	print("capability_pw_reset_student.name={!r} capability_pw_reset_student.target_role={!r}".format(
		capability_pw_reset_student.name, capability_pw_reset_student.target_role
	))
	cr_student_demo = context_role("student", [], "DEMOSCHOOL")
	cr_teacher_demo = context_role("teacher", [capability_pw_reset_student], "DEMOSCHOOL")

	assert is_authorized([cr_teacher_demo], [cr_student_demo], Capability.PASSWORD_RESET)


def test_teacher_without_cap_same_school_is_not_authorized(
		context_role,
):
	cr_student_demo = context_role("student", [], "DEMOSCHOOL")
	cr_teacher_demo = context_role("teacher", [], "DEMOSCHOOL")

	assert not is_authorized([cr_teacher_demo], [cr_student_demo], Capability.PASSWORD_RESET)
