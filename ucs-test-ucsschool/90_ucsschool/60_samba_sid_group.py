#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Check if a new group gets a domain sid
## tags: [apptest,ucsschool,ucsschool_base1]
## roles:
##  - domaincontroller_master
##  - domaincontroller_backup,
##  - domaincontroller_slave,
##  - memberserver
## exposure: dangerous
## bugs: [33677]


def test_samba_sid_group(udm, ucr, lo):
        # create a group which is ignored by the connector
        position = "cn=univention,%s" % ucr.get("ldap/base")
        group_dn, groupname = udm.create_group(position=position, check_for_drs_replication=False)

        group_sid = lo.get(group_dn)["sambaSID"][0]
        assert group_sid.startswith(b"S-1-5-21-")
