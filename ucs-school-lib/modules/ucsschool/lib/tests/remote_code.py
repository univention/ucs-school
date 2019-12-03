# -*- coding: utf-8 -*-

import json

from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.user import (
    ExamStudent,
    Staff,
    Student,
    Teacher,
    TeachersAndStaff,
    User,
)
from univention.admin.uexceptions import noObject
from univention.admin.uldap import getAdminConnection

lo, po = getAdminConnection()


async def create_school_class(**kwargs):
    sc = SchoolClass(**kwargs)
    print(sc.dn)
    await sc.create(lo)


async def school_class_to_dict(dn):
    sc = await SchoolClass.from_dn(dn, None, lo)
    print(json.dumps(sc.to_dict()))


async def remove_school_class(dn):
    sc = await SchoolClass.from_dn(dn, None, lo)
    print(await sc.remove(lo))


async def school_class_exits(dn):
    try:
        sc = await SchoolClass.from_dn(dn, None, lo)
        await sc.exists(lo)
        print("True")
    except noObject:
        print("False")


async def create_user(**kwargs):
    user_cls = kwargs.pop("user_cls")
    cls = globals()[user_cls]
    user = cls(**kwargs)
    print(user.dn)
    await user.create(lo)


async def user_to_dict(dn):
    user = await User.from_dn(dn, None, lo)
    print(json.dumps(user.to_dict()))


async def remove_user(dn):
    user = await User.from_dn(dn, None, lo)
    print(await user.remove(lo))


async def user_exits(dn):
    try:
        user = await User.from_dn(dn, None, lo)
        await user.exists(lo)
        print("True")
    except noObject:
        print("False")
