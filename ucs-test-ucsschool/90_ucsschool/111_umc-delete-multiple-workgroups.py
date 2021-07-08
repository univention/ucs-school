#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v -s
## -*- coding: utf-8 -*-
## desc: test deleting multiple workgroups
## roles: [domaincontroller_slave]
## tags: [ucsschool,apptest,ucsschool_base1]
## bugs: [47393]
## exposure: dangerous
## packages: [ucs-school-umc-groups]

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./......py::test_create

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client


def test_delete_multiple_workgroups():
    # Create 6 workgroups and remove 4 at once. Check if exactly 2 groups remain
    ucr = ucr_test.UCSTestConfigRegistry()
    ucr.load()
    host = ucr.get("hostname")
    total_groups = 6
    remaining_groups = 2
    with utu.UCSTestSchool() as schoolenv:
        school, oudn = schoolenv.create_ou(name_edudc=host)
        connection = Client.get_test_connection()
        hitlist = []
        for i in range(total_groups):
            work_group = Workgroup(school, connection=connection)
            work_group.create()
            utils.wait_for_replication()
            work_group.verify_exists(group_should_exist=True, share_should_exist=True)
            if i < total_groups - remaining_groups:  # groups to be deleted
                hitlist.append(work_group.dn())

        res_remove = connection.umc_command(
            "schoolgroups/remove", [{"object": hitlist}], "workgroup-admin"
        ).result
        assert res_remove[0]["success"]

        res_query = connection.umc_command(
            "schoolgroups/query", {"school": school, "pattern": ""}, "workgroup-admin"
        ).result
        assert len(res_query) == remaining_groups
