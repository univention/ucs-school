#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: distribute_materials_teacher_exclusion
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave, memberserver]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-distribution]

from __future__ import print_function

import os
from collections import namedtuple

import pytest

from univention.config_registry import handler_set
from univention.testing import utils
from univention.testing.ucsschool.distribution import Distribution
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client

User = namedtuple("User", ["object", "dn"])


@pytest.mark.parametrize("exclude_teachers", [True, False])
def test_exclude_teachers_from_distribution(
    schoolenv, schedule_restart_umc, restart_umc, ucr, exclude_teachers
):
    def _check_recipients(users, project_name, school, should_exist):
        for user in users:
            if "lehrer" in user.dn:
                path = os.path.join(
                    "/home", school, "lehrer", user.object, "Unterrichtsmaterial", project_name
                )
            elif "schueler" in user.dn:
                path = os.path.join(
                    "/home", school, "schueler", user.object, "Unterrichtsmaterial", project_name
                )

            if should_exist != os.path.exists(path):
                return False, user, path

        return True, None, None

    host = ucr.get("hostname")
    handler_set(["umc/http/session/timeout=1200"])
    handler_set(["umc/module/timeout=1200"])

    ucr["ucsschool/datadistribution/exclude_teachers"] = str(exclude_teachers)
    ucr.save()

    restart_umc()

    connection = Client(host)

    # Create ou, teacher, student, group
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    teachers = []
    students = []
    for _ in range(10):
        tea, teadn = schoolenv.create_user(school, is_teacher=True)
        stu, studn = schoolenv.create_user(school)
        teachers.append(User(tea, teadn))
        students.append(User(stu, studn))

    group = Workgroup(school, members=[user.dn for user in (teachers + students)])
    group.create()
    utils.wait_for_replication_and_postrun()

    creating_teacher = teachers[0]
    connection.authenticate(creating_teacher.object, "univention")

    expected_recipients = []
    excluded_recipients = []

    for user in teachers + students:
        if not (exclude_teachers and user in teachers) or user is creating_teacher:
            expected_recipients.append(user)
        else:
            excluded_recipients.append(user)

    # Creating new project
    project = Distribution(
        school,
        sender=creating_teacher.object,
        connection=connection,
        ucr=ucr,
        files=[("file_name", "utf8")],
        flavor="teacher",
        recipients=[group],
    )
    project.add()
    project.check_add()

    project.distribute()

    # Cannot use 'check_distribute' here, since it only checks students and mapps
    # all users to students even if they are not.
    result, user, path = _check_recipients(expected_recipients, project.name, school, True)
    assert (
        result
    ), f"Expected files for user {user.object} of project {project.name} not found! \
        Distribution failed cannot find: {path}"

    result, user, path = _check_recipients(excluded_recipients, project.name, school, False)
    assert (
        result
    ), f"Unexpected files for user {user.object} of project {project.name} found! \
        Distribution failed found: {path}"

    project.remove()
    project.check_remove()
