#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test of the umc search in the internet module
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages:  [ucs-school-umc-internetrules]

from typing import List  # noqa: F401

import univention.testing.ucsschool.ucs_test_school as utu
from univention.testing.umc import Client


def test_search_with_wildcards_in_assign_internetrules(ucr):
    # Set the groupprefix to something that is not the default and
    # does not have a dash or space at the end.
    # See Bug #55034
    arbitrary_delimiter = "$$$"
    default_groups = ["teachers", "pupils", "staff"]
    for role in default_groups:
        ucr.handler_set({f"ucsschool/ldap/default/groupprefix/{role}={role}{arbitrary_delimiter}"})

    umc_connection = Client.get_test_connection()

    # Create a test school
    with utu.UCSTestSchool() as test_school:

        # use_cli=True, as UCSTestSchool does not seem to respect
        # the groupprefix setting otherwise
        ou_name, _ = test_school.create_ou(use_cache=False, use_cli=True)

        # default group names (excluding the admin group)
        default_names = [f"{role}{arbitrary_delimiter}{ou_name}" for role in default_groups]
        default_names = default_names + ["Domain Users", f"{ou_name}-import-all"]

        # arbitrary class names
        class_names = ["1a", "2f", "10d", "10a"]
        for class_name in class_names:
            test_school.create_school_class(ou_name, class_name)

        # arbitrary work group names
        work_group_names = ["Chess", "Poetry", "Robotics", "Poetry_2", "Robotics_2"]
        for work_group_name in work_group_names:
            test_school.create_workgroup(ou_name, work_group_name)

        all_group_names = work_group_names + class_names + default_names

        def check_group_names(pattern, expected_group_names):  # type: (str, List[str]) -> None
            """
            Query for groups and check the result

            - Do a group query with `pattern`
            - Check if all `expected_group_names` are within the group query result
            - Check if there are any unexpected group names in the group query result
            """
            param = {"school": ou_name, "pattern": pattern}
            request_result = umc_connection.umc_command("internetrules/groups/query", param)

            listed_group_names = [sub_result["name"] for sub_result in request_result.result]
            for group_name in expected_group_names:
                assert group_name in listed_group_names

            unexpected_group_names = set(all_group_names).difference(expected_group_names)
            for group_name in unexpected_group_names:
                assert group_name not in listed_group_names

        # Test if all groups are shown
        check_group_names("*", all_group_names)

        # Test wildcard search results
        check_group_names("oet", ["Poetry", "Poetry_2"])
        check_group_names("P*y", ["Poetry"])
        check_group_names("Rob*", ["Robotics", "Robotics_2"])
        check_group_names("*ess", ["Chess"])
        check_group_names("10*", ["10a", "10d"])
        check_group_names("*a", ["10a", "1a"])
        check_group_names("*2", ["Robotics_2", "Poetry_2"])
