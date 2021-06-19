#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: check performance of /ucsschool/apis/idbroker/user
## tags: []
## exposure: safe
## packages: []
## bugs: [53437]

CSV_FILE = "/root/idbroker_user_stats.csv"
URL_NAME = "/ucsschool/apis/idbroker/user"


def test_failure_count(check_failure_count):
    check_failure_count(CSV_FILE)


def test_rps(check_rps):
    check_rps(CSV_FILE, URL_NAME, 30.0)


def test_95_percentile(check_95_percentile):
    check_95_percentile(CSV_FILE, URL_NAME, 1000)
