#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: check performance of GET /univention/udm/users/user/DN
## tags: []
## exposure: safe
## packages: []
## bugs: [53437]

CSV_FILE = "/root/udm_user_get_stats.csv"
URL_NAME = "/univention/udm/users/user/"


def test_failure_count(check_failure_count):
    check_failure_count(CSV_FILE)


def test_rps(check_rps):
    check_rps(CSV_FILE, URL_NAME, 300)


def test_95_percentile(check_95_percentile):
    check_95_percentile(CSV_FILE, URL_NAME, 100)
