#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check if a new user gets a domain sid
## tags: [apptest,ucsschool,ucsschool_base1]
## roles:
##  - domaincontroller_master
##  - domaincontroller_backup,
##  - domaincontroller_slave,
##  - memberserver
## exposure: dangerous
## bugs: [33677]


def test_samba_sid_user(udm_session, ucr, lo):
    # create an user who is ignored by the connector
    position = "cn=univention,%s" % ucr.get("ldap/base")
    user_dn, username = udm_session.create_user(
        position=position, check_for_drs_replication=False, wait_for=False
    )

    user_sid = lo.get(user_dn)["sambaSID"][0]
    assert user_sid.startswith(b"S-1-5-21-")
