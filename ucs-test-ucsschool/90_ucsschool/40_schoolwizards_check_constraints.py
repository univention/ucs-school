#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: Check the check constraints function for the admin workaround in the schoolwizard modules
## roles: [domaincontroller_master]
## exposure: safe
## tags: [apptest, ucsschool, unittest, base1]
## bugs: [52757]

import pytest

from univention.management.console.modules.schoolwizards import (
    OperationType,
    check_workaround_constraints,
)


def ids(param):
    if isinstance(param, OperationType):
        return param.name
    if isinstance(param, set):
        return "[{}]".format(",".join(param))


@pytest.mark.parametrize(
    "operation_type,subject_schools,old_object_schools,new_object_schools,expected_result",
    [
        (OperationType.CREATE, set(), set(), set(), False),  # No school user adds global user
        (
            OperationType.CREATE,
            {"A"},
            set(),
            {"A"},
            True,
        ),  # school user creates school user in own school
        (
            OperationType.CREATE,
            {"A"},
            set(),
            {"B"},
            False,
        ),  # school user creates school user in other school
        (
            OperationType.CREATE,
            {"A"},
            set(),
            {"A", "B"},
            False,
        ),  # school user creates user in own and other school
        (
            OperationType.CREATE,
            {"A", "B"},
            set(),
            {"A"},
            True,
        ),  # school user creates school user in one own school
        (
            OperationType.CREATE,
            {"A", "B", "C"},
            set(),
            {"A", "C"},
            True,
        ),  # school user creates school user in own schools
        (OperationType.MODIFY, set(), set(), set(), False),  # global user modifies global user
        (
            OperationType.MODIFY,
            {"A"},
            {"A"},
            {"A"},
            True,
        ),  # user edits user in own school, no school change
        (OperationType.MODIFY, {"A"}, {"B"}, {"A"}, False),  # user moves user in own school
        (OperationType.MODIFY, {"A"}, {"A"}, {"A", "B"}, False),  # user adds own school to user
        (OperationType.MODIFY, {"A"}, set(), {"A"}, False),  # user moves global user in own school
        (
            OperationType.MODIFY,
            {"A", "B"},
            {"A", "C"},
            {"A", "C"},
            True,
        ),  # user edits user that is in one own school
        (
            OperationType.MODIFY,
            {"A", "B"},
            {"A", "C"},
            {"A", "C", "B"},
            False,
        ),  # user adds own school to user in other own school
        (OperationType.DELETE, set(), set(), set(), False),  # global user deletes global user
        (OperationType.DELETE, set(), {"A"}, set(), False),  # global user deletes school user
        (OperationType.DELETE, {"A"}, set(), set(), False),  # school user deletes global user
        (
            OperationType.DELETE,
            {"A"},
            {"A"},
            set(),
            True,
        ),  # school user deletes user that is in own school only
        (
            OperationType.DELETE,
            {"A", "B"},
            {"A", "B"},
            set(),
            True,
        ),  # school user deletes user in own schools only
        (
            OperationType.DELETE,
            {"A", "B"},
            {"B"},
            set(),
            True,
        ),  # school user deletes user that is in one own school
        (
            OperationType.DELETE,
            {"A"},
            {"A", "B"},
            set(),
            False,
        ),  # user deletes user that is also in another school
        (99, set(), set(), set(), False),
        (99, {"A"}, {"A"}, {"A"}, False),
    ],
    ids=ids,
)
def test_check_constraints(
    operation_type, subject_schools, old_object_schools, new_object_schools, expected_result
):
    assert (
        check_workaround_constraints(
            subject_schools, old_object_schools, new_object_schools, operation_type
        )
        == expected_result
    )
