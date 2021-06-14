#!/usr/share/ucs-test/runner pytest -s -l -v
## bugs: [40470]
## desc: school-servers (except master and backup) not added to DNS forward and reverse lookup zones
## exposure: safe
## join: true
## roles:
##  - domaincontroller_slave
## tags: [apptest,ucsschool,ucsschool_base1]

from __future__ import print_function

from ldap.filter import filter_format

import univention.testing.utils as utils


def test_check_dns_settings(ucr):
    lo = utils.get_ldap_connection()
    zone_name = "%s.%s." % (ucr.get("hostname"), ucr.get("domainname"))
    print("Searching for DNS zones with nsRecord=%r" % (zone_name,))
    zones = lo.search(filter_format("nSRecord=%s", (zone_name,)))

    assert not zones, "A school server is listed as DNS server, which it must not be: %r" % (zones,)
