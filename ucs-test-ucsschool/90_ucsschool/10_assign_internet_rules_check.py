#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: ucs-school-assign-internet-rules-check
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave, memberserver]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: careful
## packages:  [ucs-school-umc-internetrules]

import random

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
