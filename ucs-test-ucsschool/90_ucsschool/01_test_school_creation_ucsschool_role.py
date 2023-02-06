#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: test if ucsschool role is set correct
## roles: []
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

import pytest

from univention.testing.utils import verify_ldap_object


def test_set_ucsschool_role(schoolenv):
    ucr = schoolenv.ucr
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr["hostname"], use_cache=False)
    ou_lower = ou_name.lower()
    ldap_hostdn = ucr["ldap/hostdn"]
    if ucr.is_true("ucsschool/singlemaster", False):
        expected_attr = {"ucsschoolRole": ["single_master:school:{}".format(ou_name)]}
        verify_ldap_object(ldap_hostdn, expected_attr=expected_attr, strict=False)
    else:
        base = "cn=ucsschool,cn=groups,{}".format(ucr["ldap/base"])
        for ldap_filter, role in [
            ("cn=OU{}-DC-Verwaltungsnetz".format(ou_lower), "dc_slave_admin"),
            ("cn=OU{}-DC-Edukativnetz".format(ou_lower), "dc_slave_edu"),
        ]:
            res = schoolenv.lo.search(base=base, filter=ldap_filter, attr=["uniqueMember"])
            if res and res[0][1]:
                server_dn = res[0][1]["uniqueMember"][0].decode("UTF-8")
                uot = schoolenv.lo.get(server_dn, attr=["univentionObjectType"])["univentionObjectType"][
                    0
                ].decode("UTF-8")
                if uot == "computers/domaincontroller_slave":
                    expected_attr = {"ucsschoolRole": ["{}:school:{}".format(role, ou_name)]}
                    verify_ldap_object(server_dn, expected_attr=expected_attr, strict=False)
                    break
        else:
            pytest.fail('no edu or adm server with type "computers/domaincontroller_slave"')
