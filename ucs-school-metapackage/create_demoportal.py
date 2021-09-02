#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2018-2021 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import os
import random
import string
import subprocess
import sys

import univention.admin.modules as modules
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import Staff, Student, Teacher
from ucsschool.lib.models.utils import ucr
from univention.management.console.ldap import get_admin_connection

lo, pos = get_admin_connection()
modules.update()
module_groups = modules.get("groups/group")
module_users = modules.get("users/user")

is_single_master = ucr.is_true("ucsschool/singlemaster", False)
if is_single_master:
    hostname_demoschool = ucr.get("hostname")
else:
    hostname_demoschool = "DEMOSCHOOL"
hostdn = ucr.get("ldap/hostdn")
demo_secret_path = "/etc/ucsschool/demoschool.secret"
if os.path.isfile(demo_secret_path):
    with open(demo_secret_path, "r") as fd:
        demo_password = fd.read().strip()
else:
    _chars = string.ascii_letters + string.digits
    demo_password = "".join(random.choice(_chars) for _ in range(16))  # nosec
    with open(demo_secret_path, "w") as fd:
        os.fchmod(fd.fileno(), 0o640)
        fd.write(demo_password)

# (name, displayName)
SCHOOL = ("DEMOSCHOOL", "Demo School")


def create_school():
    school_exists = False
    schools = School.from_binddn(lo)
    for school in schools:
        if school.name == SCHOOL[0]:
            print("WARNING: A school with name {} already exists!".format(SCHOOL[0]))
            school_exists = True
            break
    if not school_exists:
        try:
            subprocess.check_call(  # nosec
                [
                    "/usr/share/ucs-school-import/scripts/create_ou",
                    "--displayName={}".format(SCHOOL[1]),
                    "--alter-dhcpd-base=false",
                    SCHOOL[0],
                    hostname_demoschool,
                ]
            )
        except subprocess.CalledProcessError as exc:
            print("The following error occured while creating the Demo School object: \n")
            print(exc)
            sys.exit(1)
    kls = SchoolClass(name="{}-Democlass".format(SCHOOL[0]), school=SCHOOL[0])
    kls.create(lo)
    student = Student(
        firstname="Demo",
        lastname="Student",
        name="demo_student",
        password=demo_password,
        school=SCHOOL[0],
    )
    student.school_classes[SCHOOL[0]] = ["Democlass"]
    student.create(lo)
    teacher = Teacher(
        firstname="Demo",
        lastname="Teacher",
        name="demo_teacher",
        password=demo_password,
        school=SCHOOL[0],
    )
    teacher.create(lo)
    staff = Staff(
        firstname="Demo", lastname="Staff", name="demo_staff", password=demo_password, school=SCHOOL[0]
    )
    staff.create(lo)
    # create school admin from teacher
    admin = Teacher(
        firstname="Demo", lastname="Admin", name="demo_admin", password=demo_password, school=SCHOOL[0]
    )
    admin.create(lo)
    admin_group = module_groups.lookup(None, lo, "name=admins-{}".format(SCHOOL[0]), pos.getBase())[0].dn
    admin_udm = admin.get_udm_object(lo)
    admin_udm.options.append("ucsschoolAdministrator")
    admin_udm["groups"].append(admin_group)
    admin_udm["description"] = "School Admin for {} created from teacher account.".format(SCHOOL[0])
    admin_udm["ucsschoolRole"].append("school_admin:school:{}".format(SCHOOL[0]))
    admin_udm.modify()


def run():
    """
    This function creates a demo school for testing and demonstration purposes.
    It used to create a demo portal, too. Hence, the name. But this is not done anymore.
    """
    create_school()
    sys.exit(0)


if __name__ == "__main__":
    run()
