#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: check number of squid helper process children
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master,domaincontroller_slave]
## bugs: [40092]
## exposure: safe
## packages:
##   - ucs-school-webproxy

from __future__ import print_function


def test_check_number_of_squid_children(ucr):
    for key, value in {
        "squid/basicauth/children": "50",
        "squid/krb5auth/children": "50",
        "squid/ntlmauth/children": "50",
        "squid/rewrite/children": "20",
    }.items():
        assert ucr.get(key) == value
        print("UCR variable: %s=%r" % (key, value))
