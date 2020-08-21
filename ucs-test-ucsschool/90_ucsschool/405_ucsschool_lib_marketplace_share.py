#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.share.MarketplaceShare
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python-ucs-school

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./404_ucsschool_lib_models_main.py
#

try:
    from typing import Dict, List, Tuple
except ImportError:
    pass

import pytest

import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models.share import MarketplaceShare
from ucsschool.lib.models.utils import exec_cmd
from ucsschool.lib.roles import create_ucsschool_role_string, role_marketplace_share


@pytest.fixture(scope="session")
def exp_ldap_attr(ucr_domainname, ucr_hostname, ucr_is_singlemaster):
    def _func(ou_name):  # type: (str) -> Dict[str, List[str]]
        if ucr_is_singlemaster:
            share_host = ["{}.{}".format(ucr_hostname, ucr_domainname)]
        else:
            share_host = ["dc{}-01.{}".format(ou_name, ucr_domainname)]
        return {
            "objectClass": ["univentionShareSamba"],
            "univentionSharePath": ["/home/{}/groups/Marktplatz".format(ou_name)],
            "ucsschoolRole": [create_ucsschool_role_string(role_marketplace_share, ou_name)],
            "univentionShareSambaDirectorySecurityMode": ["0777"],
            "univentionShareHost": share_host,
        }

    return _func


def test_get_all(exp_ldap_attr, ucr_hostname):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr_hostname)
        objs = MarketplaceShare.get_all(schoolenv.lo, ou_name)
        assert len(objs) == 1
        obj = objs[0]
        assert isinstance(obj, MarketplaceShare)
        utils.verify_ldap_object(
            obj.dn, expected_attr=exp_ldap_attr(ou_name), strict=False,
        )


def test_create(exp_ldap_attr, ucr_hostname, ucr_ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(use_cache=False, name_edudc=ucr_hostname)
        dn = "cn=Marktplatz,cn=shares,ou={},{}".format(ou_name, ucr_ldap_base)
        cmd = [
            "python",
            "-m",
            "ucsschool.lib.models",
            "--debug",
            "delete",
            "MarketplaceShare",
            "--dn",
            dn,
        ]
        exec_cmd(cmd, log=True, raise_exc=True)
        utils.verify_ldap_object(dn, should_exist=False)

        obj = MarketplaceShare(school=ou_name)
        res = obj.create(schoolenv.lo)
        assert res
        utils.verify_ldap_object(
            obj.dn, expected_attr=exp_ldap_attr(ou_name), strict=False,
        )


def test_delete(exp_ldap_attr, ucr_hostname, ucr_ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(use_cache=False, name_edudc=ucr_hostname)
        dn = "cn=Marktplatz,cn=shares,ou={},{}".format(ou_name, ucr_ldap_base)
        utils.verify_ldap_object(
            dn, expected_attr=exp_ldap_attr(ou_name), strict=False, should_exist=True
        )
        obj = MarketplaceShare.from_dn(dn, ou_name, schoolenv.lo)
        res = obj.remove(schoolenv.lo)
        assert res
        utils.verify_ldap_object(dn, should_exist=False)
