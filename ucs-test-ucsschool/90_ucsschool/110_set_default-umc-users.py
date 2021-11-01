#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: set default umc users
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: []

import univention.testing.utils as utils
from univention.config_registry import handler_set


def test_set_default_umc_users(ucr):
    handler_set(["ucsschool/import/attach/policy/default-umc-users=no"])
    # UCR variables are loaded for ucsschool at the import stage
    # That's why the import should be after setting the ucr variable
    import univention.testing.ucsschool.ucs_test_school as utu

    with utu.UCSTestSchool() as schoolenv:
        from ucsschool.lib.models.utils import ucr

        ucr.load()

        school, oudn = schoolenv.create_ou(use_cache=False)
        utils.wait_for_replication_and_postrun()
        base = "cn=Domain Users %s,cn=groups,%s" % (
            school.lower(),
            schoolenv.get_ou_base_dn(school),
        )
        print("*** Checking school {!r}".format(school))
        expected_attr = "cn=default-umc-users,cn=UMC,cn=policies,%s" % (ucr.get("ldap/base"),)
        found_attr = schoolenv.lo.search(
            base=base, scope="base", attr=["univentionPolicyReference"]
        )[0][1].get("univentionPolicyReference", [])
        assert expected_attr.encode("UTF-8") not in found_attr
