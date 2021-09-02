#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: ucs-school-workinggroup-module-check
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-groups]

from __future__ import print_function

import time

import univention.testing.utils as utils
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client


def test_workingroup_module(ucr, schoolenv):
    host = ucr.get("hostname")
    schoolName, oudn = schoolenv.create_ou(name_edudc=host)
    tea, teadn = schoolenv.create_user(schoolName, is_teacher=True)
    stu, studn = schoolenv.create_user(schoolName)
    klass, klassdn = schoolenv.create_school_class(schoolName)
    memberListdn = [teadn, studn]

    account = utils.UCSTestDomainAdminCredentials()
    passwd = account.bindpw

    utils.wait_for_replication_and_postrun()

    for user in [tea]:
        connection = Client(host)
        connection.authenticate(user, passwd)
        # 1 creating empty workgroup
        emptyGroup = Workgroup(schoolName, connection=connection)
        emptyGroup.create()
        # 2 checking the created workgroup and its file share object in ldap
        # import pdb; pdb.set_trace()
        utils.wait_for_replication()
        emptyGroup.verify_exists(group_should_exist=True, share_should_exist=True)

        # 3 creating unempty workgroup
        group = Workgroup(schoolName, connection=connection, members=memberListdn)
        group.create()

        # 4 checking the created workgroup and its file share object in ldap
        group.verify_exists(group_should_exist=True, share_should_exist=True)

        # 5 checking if the atrriputes for the group is correct in ldap
        group.verify_ldap_attributes()

        # 6 should fail: creating a new working group with a duplicate name
        group2 = Workgroup(schoolName, name=group.name, connection=connection)
        group2.create(expect_creation_fails_due_to_duplicated_name=True)

        # 7 add members to group
        emptyGroup.addMembers(memberListdn)

        # 8 checking if the atrriputes for the emptygroup is correct in ldap
        emptyGroup.verify_ldap_attributes()

        # 9 remove members from a group
        group.removeMembers([memberListdn[0]])

        # 10 checking if the atrriputes for the group is correct in ldap
        for wait in range(30):
            try:
                group.verify_ldap_attributes()
            except Exception as e:
                if group.dn() in str(e):
                    print(":::::::%r::::::" % wait)
                    print(str(e))
                    time.sleep(1)
                else:
                    raise
            else:
                break

        # 11 Change the members of a group
        group.set_members([memberListdn[0]])

        # 11 checking if the atrriputes for the group is correct in ldap
        for wait in range(30):
            try:
                group.verify_ldap_attributes()
            except Exception as e:
                if group.dn() in str(e):
                    print(":::::::%r::::::" % wait)
                    print(str(e))
                    time.sleep(1)
                else:
                    raise
            else:
                break

        # 12 remove the group
        group.remove()

        # 13 check if the object is removed from ldap
        group.verify_exists(group_should_exist=False, share_should_exist=False)

        # 14 Check group without share
        no_share_group = Workgroup(schoolName, create_share=False, connection=connection)
        no_share_group.create()
        no_share_group.verify_exists(group_should_exist=True, share_should_exist=False)
        no_share_group.verify_ldap_attributes()

        # 15 group with email
        email_group = Workgroup(
            schoolName,
            create_email=True,
            allowed_email_senders_users=[teadn],
            allowed_email_senders_groups=[klassdn],
        )
        email_group.email = "{}-{}@example.net".format(email_group.name, schoolName)
        email_group.create()
        email_group.verify_exists(group_should_exist=True, share_should_exist=True)
        email_group.verify_ldap_attributes()
        email_group.deactivate_email()
        email_group.verify_ldap_attributes()
