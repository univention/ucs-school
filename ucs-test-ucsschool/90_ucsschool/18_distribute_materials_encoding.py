#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: distribute materials with encoding
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave, memberserver]
## tags: [apptest,ucsschool,ucsschool_base1]
## versions:
##  4.0-0: skip
## exposure: dangerous
## packages: [ucs-school-umc-distribution]

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.ucsschool.distribution import Distribution
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client


def test_distribute_materials_encoding(schoolenv, ucr):
    host = ucr.get("hostname")
    connection = Client(host)

    # Create ou, teacher, student, group
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    tea, teadn = schoolenv.create_user(school, is_teacher=True)
    stu, studn = schoolenv.create_user(school)
    group = Workgroup(school, members=[studn])
    group.create()
    utils.wait_for_replication_and_postrun()

    filename1 = b"%s%s%s%s" % (
        u"\xc4".encode("UTF-8"),  # Ä
        uts.random_name_special_characters(3).encode("UTF-8"),
        u"\u2192".encode("UTF-8"),  # →
        uts.random_name_special_characters(3).encode("UTF-8"),
    )
    filename2 = b"%s%s" % (
        u"\xc4".encode("UTF-8"),
        uts.random_name_special_characters(6).encode("UTF-8"),
    )
    filename3 = b"%s%s%s" % (
        uts.random_name_special_characters(3).encode("ASCII"),
        u"\xc4".encode("ISO8859-1"),
        uts.random_name_special_characters(3).encode("ASCII"),
    )
    filename4 = uts.random_name()

    files = [(filename1, "utf-8")]
    files.append((filename2, "utf-8"))
    files.append((filename3, "iso8859-1"))
    files.append((filename4, "utf-8"))

    connection.authenticate(tea, "univention")
    # Create new project
    project = Distribution(
        school,
        sender=tea,
        connection=connection,
        files=files,
        ucr=ucr,
        recipients=[group],
        flavor="teacher",
    )
    project.add()
    project.check_add()
    project.distribute()
    project.check_distribute([stu])
    project.collect()
    project.check_collect([stu])

    project.remove()
    project.check_remove()
