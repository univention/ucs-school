#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test if the Import HTTP API (Newton) accepts a hostname matching its fqdn, but with differing case
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: safe
## packages:
##   - ucs-school-import-http-api-client
## bugs: [51606]

import string

from ucsschool.http_api.client import Client


def test_matching_server_name(admin_username, admin_password, fqdn, ucr):
    Client(name=admin_username, password=admin_password, server=fqdn)


def test_camel_case_server_name(admin_username, admin_password, fqdn, ucr):
    def other_case(s):
        return s.upper() if s in string.ascii_lowercase else s.lower()

    server = "".join(
        [other_case(fqdn[i]) if i in range(0, len(fqdn), 2) else fqdn[i] for i in range(len(fqdn))]
    )
    assert server != fqdn
    Client(name=admin_username, password=admin_password, server=server)
