#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-assign-internet-rules-check
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave, memberserver]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: careful
## packages:  [ucs-school-umc-internetrules]

import random

import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from univention.testing.ucsschool.internetrule import Check, InternetRule
from univention.testing.ucsschool.klasse import Klasse
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client


# Assign internetrules to groups randomly
def assignRulesToGroupsRandomly(groupList, ruleList, school, groupType):
    assignedGroups = []
    for group in groupList:
        rule = random.choice(ruleList)
        rule.assign(school, group.name, groupType)
        assignedGroups.append((group.name, rule.name))
    utils.wait_for_replication_and_postrun()
    return assignedGroups


def test_assign_internet_rules(schoolenv, ucr):
    umc_connection = Client.get_test_connection()
    if ucr.get("server/role") == "domaincontroller_master":
        umc_connection_master = umc_connection
    else:
        umc_connection_master = Client.get_test_connection(ucr.get("ldap/master"))
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))

    # define many random internet rules
    newRules = []
    for _ in range(8):
        rule = InternetRule(ucr=ucr, connection=umc_connection)
        rule.define()
        rule.get(should_exist=True)
        newRules.append(rule)
    utils.wait_for_replication()

    # Create random workgroups
    newWorkgroups = []
    for _ in range(2):
        group = Workgroup(school, ucr=ucr, connection=umc_connection)
        group.create()
        newWorkgroups.append(group)
    utils.wait_for_replication()

    assignedGroups = [(g.name, None) for g in newWorkgroups]

    # Instantiate Check instance
    check1 = Check(school, assignedGroups, ucr=ucr, connection=umc_connection)

    # check the assigned internet rules UMCP
    check1.checkRules()
    # check ucr variables
    check1.checkUcr()

    # assign internetrules to groups randomly
    rules = newRules[:4]
    assignedGroups = assignRulesToGroupsRandomly(newWorkgroups, rules, school, "workgroup")

    # Instantiate another Check instance
    check2 = Check(school, assignedGroups, ucr=ucr, connection=umc_connection)

    # check the assigned internet rules UMCP
    check2.checkRules()
    # check ucr variables
    check2.checkUcr()

    # switch internetrules for groups randomly
    rules = newRules[4:]
    assignedGroups = assignRulesToGroupsRandomly(newWorkgroups, rules, school, "workgroup")

    # Instantiate another Check instance
    check3 = Check(school, assignedGroups, ucr=ucr, connection=umc_connection)

    # check the assigned internet rules UMCP
    check3.checkRules()
    # check ucr variables
    check3.checkUcr()

    # assign default internetrule to groups
    for group in newWorkgroups:
        rule.assign(school, group.name, "workgroup", default=True)

    # check the assigned internet rules UMCP
    check1.checkRules()
    # check ucr variables
    check1.checkUcr()

    # Create random classs
    newclasses = []
    for _ in range(2):
        klasse = Klasse(school, ucr=ucr, connection=umc_connection_master)
        klasse.create()
        newclasses.append(klasse)
    utils.wait_for_replication()

    assignedClasses = [(c.name, None) for c in newclasses]

    check1 = Check(school, assignedClasses, ucr=ucr, connection=umc_connection)

    # check the assigned internet rules UMCP
    check1.checkRules()
    # check ucr variables
    check1.checkUcr()

    # assign internetrules to classes randomly
    rules = newRules[:4]
    assignedClasses = assignRulesToGroupsRandomly(newclasses, rules, school, "class")

    check2 = Check(school, assignedClasses, ucr=ucr, connection=umc_connection)

    # check the assigned internet rules UMCP
    check2.checkRules()
    # check ucr variables
    check2.checkUcr()

    # switch internetrules for classes randomly
    rules = newRules[4:]
    assignedClasses = assignRulesToGroupsRandomly(newclasses, rules, school, "class")
    check3 = Check(school, assignedClasses, ucr=ucr, connection=umc_connection)

    # check the assigned internet rules UMCP
    check3.checkRules()
    # check ucr variables
    check3.checkUcr()

    # assign default internetrule to classes
    for c in newclasses:
        rule.assign(school, c.name, "class", default=True)

    # check the assigned internet rules UMCP
    check1.checkRules()
    # check ucr variables
    check1.checkUcr()


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

        def check_group_names(pattern, expected_group_names):  # type: (str, list[str]) -> None
            """Query for groups and check the result

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
