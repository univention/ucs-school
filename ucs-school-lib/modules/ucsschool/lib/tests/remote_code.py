# -*- coding: utf-8 -*-

import json
from univention.admin.uldap import getAdminConnection
from univention.admin.uexceptions import noObject
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff, User

lo, po = getAdminConnection()


def create_school_class(**kwargs):
	sc = SchoolClass(**kwargs)
	print(sc.dn)
	sc.create(lo)


def school_class_to_dict(dn):
	sc = SchoolClass.from_dn(dn, None, lo)
	print(json.dumps(sc.to_dict()))


def remove_school_class(dn):
	sc = SchoolClass.from_dn(dn, None, lo)
	print(sc.remove(lo))


def school_class_exits(dn):
	try:
		sc = SchoolClass.from_dn(dn, None, lo)
		sc.exists(lo)
		print("True")
	except noObject:
		print("False")


def create_user(**kwargs):
	user_cls = kwargs.pop("user_cls")
	cls = globals()[user_cls]
	user = cls(**kwargs)
	print(user.dn)
	user.create(lo)


def user_to_dict(dn):
	user = User.from_dn(dn, None, lo)
	print(json.dumps(user.to_dict()))


def remove_user(dn):
	user = User.from_dn(dn, None, lo)
	print(user.remove(lo))


def user_exits(dn):
	try:
		user = User.from_dn(dn, None, lo)
		user.exists(lo)
		print("True")
	except noObject:
		print("False")
