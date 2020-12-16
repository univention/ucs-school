#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test the branch test
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool_base1]
## exposure: careful


def test_that_fails():
    print("I fail")
    assert False
