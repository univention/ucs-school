#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Self service user attributes ACL generation and enforcement
## tags: [apptest,ucsschool,ucsschool_base1]
## roles:
##  - domaincontroller_master
## exposure: dangerous
## packages:
##  - univention-self-service-master


import pytest

import univention.admin.uexceptions
import univention.admin.uldap
import univention.testing.utils as utils
from univention.config_registry import handler_set


def test_modify_userattributes_and_ldap_acl(schoolenv, udm_session, ucr):
    host = ucr.get("hostname")
    school, oudn = schoolenv.create_ou(name_edudc=host)

    handler_set(["umc/self-service/profiledata/enabled=true"])

    if "l" not in ucr.get("self-service/ldap_attributes", "").split(","):
        handler_set(["self-service/ldap_attributes=%s,l" % ucr.get("self-service/ldap_attributes", "")])

    _, user = schoolenv.create_teacher(school)
    utils.verify_ldap_object(user)

    lo = univention.admin.uldap.access(binddn=user, bindpw="univention")
    lo.modify(user, [("l", b"", b"Bremen")])
    utils.verify_ldap_object(user, {"l": ["Bremen"]})

    with pytest.raises(univention.admin.uexceptions.permissionDenied):
        lo.modify(user, [("sn", b"", b"mustfail")])
