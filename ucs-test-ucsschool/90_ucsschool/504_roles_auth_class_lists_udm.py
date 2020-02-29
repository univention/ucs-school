#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test authorization function for creating class lists using roles and capabilities
## tags: [apptest, ucsschool, base1]
## exposure: dangerous
## packages:
##   - python-ucs-school

from ucsschool.lib.authorization import Capability, croles_from_dn, is_authorized


# def test_administrator_user_is_authorized(ldap_base):
# 	user_dn, username = "uid=Administrator,cn=users,{}".format(ldap_base), "Administrator"
#
#
# def test_domain_administrator_is_authorized(ldap_base, ucr, udm):
# 	password = uts.random_name()
# 	user_dn, username = udm.create_user(
# 		password=password,
# 		primaryGroup="cn={},cn=groups,{}".format(
# 			ucr.get("groups/default/domainadmins", "Domain Admins"), ldap_base
# 		),
# 		wait_for=True
# 	)
#
#
# def test_school_administrator_other_school_is_not_authorized(hostname, schoolenv):
# 	host = ucr["hostname"]
# 	(ou_name1, ou_dn1), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(
# 		2,
# 		name_edudc=hostname
# 	)
# 	username, user_dn = schoolenv.create_school_admin(
# 		ou_name1,
# 		is_staff=False,
# 		is_teacher=False,
# 	)
#
#
# def test_school_administrator_same_school_is_authorized(hostname, schoolenv):
# 	(ou_name1, ou_dn1), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(
# 		2,
# 		name_edudc=hostname
# 	)
# 	username, user_dn = schoolenv.create_school_admin(
# 		school,
# 		is_staff=False,
# 		is_teacher=False,
# 	)


def test_teacher_other_school_is_not_authorized(context_role, hostname, schoolenv):
	(ou_name1, ou_dn1), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(
		2,
		name_edudc=hostname
	)
	teacher_name, teacher_dn = schoolenv.create_teacher(ou_name1)
	teacher_roles = croles_from_dn(teacher_dn)
	school_roles = context_role("school", [], ou_name2)
	assert not is_authorized(teacher_roles, [school_roles], Capability.CREATE_CLASS_LIST)


def test_teacher_same_school_is_authorized(context_role, hostname, schoolenv):
	ou_name, ou_dn = schoolenv.create_ou(name_edudc=hostname)
	teacher_name, teacher_dn = schoolenv.create_teacher(ou_name)
	teacher_roles = croles_from_dn(teacher_dn)
	school_roles = context_role("school", [], ou_name)
	assert is_authorized(teacher_roles, [school_roles], Capability.CREATE_CLASS_LIST)


def test_teacher_second_school_is_authorized(context_role, hostname, schoolenv):
	(ou_name1, ou_dn1), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(
		2,
		name_edudc=hostname
	)
	teacher_name, teacher_dn = schoolenv.create_teacher(ou_name2, schools=[ou_name1, ou_name2])
	assert ou_name2 in teacher_dn
	assert ou_name1 not in teacher_dn
	teacher_roles = croles_from_dn(teacher_dn)
	school_roles = context_role("school", [], ou_name1)
	assert is_authorized(teacher_roles, [school_roles], Capability.CREATE_CLASS_LIST)
