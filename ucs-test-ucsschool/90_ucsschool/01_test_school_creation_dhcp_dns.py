#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: test if dhcp search base and dhcp dns policy are correct
## tags: [apptest, ucsschool]
## roles: [domaincontroller_master, domaincontroller_backup]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm as udm_test
from univention.testing.utils import verify_ldap_object


def test_dhcp_search_base():
    with utu.UCSTestSchool() as schoolenv, udm_test.UCSTestUDM() as udm:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"], use_cache=False)
        objs = udm.list_objects("policies/registry")
        policy_name = "ou-default-ucr-policy"
        policy_dn = "cn={},cn=policies,{}".format(policy_name, ou_dn)
        for dn, props in objs:
            if policy_dn != dn:
                continue
            assert "dhcpd/ldap/base cn=dhcp,{}".format(ou_dn) in props["registry"]
            break
        else:
            # test also fails if there is no policy.
            assert True is False
        expected_attr = {"univentionPolicyReference": [policy_dn]}
        verify_ldap_object(ou_dn, expected_attr=expected_attr, strict=False)


def test_dhcp_dns_policy():
    with utu.UCSTestSchool() as schoolenv:
        ucr = schoolenv.ucr
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr["hostname"], use_cache=False)
        ou_lower = ou_name.lower()
        policy_dn = "cn=dhcp-dns-{},cn=policies,{}".format(ou_lower, ou_dn)
        expected_attr = {
            "emptyAttributes": ["univentionDhcpDomainNameServers"],
            "cn": ["dhcp-dns-{}".format(ou_lower)],
        }
        if (
            ucr.is_true("ucsschool/singlemaster", False)
            and ucr.get("server/role") == "domaincontroller_master"
        ):
            # todo: when creating schools with ucs_test the ip is left blank in school.py
            # but not here.
            # expected_attr["univentionDhcpDomainNameServers"] = [
            #     str(Interfaces().get_default_ip_address().ip)
            # ]
            expected_attr["univentionDhcpDomainName"] = [ucr["domainname"]]
        verify_ldap_object(policy_dn, expected_attr=expected_attr, strict=False)
        expected_attr = {"univentionPolicyReference": [policy_dn]}
        verify_ldap_object("cn=dhcp,{}".format(ou_dn), expected_attr=expected_attr, strict=False)
