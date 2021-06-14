#!/usr/share/ucs-test/runner pytest -s -l -v
## bugs: [40471]
## desc: Check that the group "Domain Users $SCHOOL" is connected to the policy "default-umc-users"
## exposure: dangerous
## roles:
##  - domaincontroller_master
##  - domaincontroller_slave
## tags: [apptest,ucsschool,ucsschool_base1]

import univention.testing.utils as utils


def test_check_domain_users_policies(schoolenv, ucr):
    lo = utils.get_ldap_connection()

    policy_dn = "cn=default-umc-users,cn=UMC,cn=policies,%s" % (ucr.get("ldap/base"),)
    school, _ = schoolenv.create_ou(name_edudc=ucr.get("hostname"))

    domain_users = lo.get(
        "cn=Domain Users %s,cn=groups,ou=%s,%s" % (school, school, ucr.get("ldap/base"))
    )
    assert policy_dn.encode("UTF-8") in domain_users.get(
        "univentionPolicyReference", []
    ), "The policy %r is not connected to the 'Domain Users %s' group, but should be." % (
        policy_dn,
        school,
    )
