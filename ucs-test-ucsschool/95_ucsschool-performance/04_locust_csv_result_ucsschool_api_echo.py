#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: check performance of POST /ucsschool/apis/echo/echo
## tags: []
## exposure: safe
## packages: []
## bugs: [53437]

CSV_FILE = "/root/ucsschool_api_echo_stats.csv"
URL_NAME = "/ucsschool/apis/echo/echo"


def test_failure_count(check_failure_count):
    check_failure_count(CSV_FILE)


def test_rps(check_rps):
    check_rps(CSV_FILE, URL_NAME, 600)


def test_95_percentile(check_95_percentile):
    check_95_percentile(CSV_FILE, URL_NAME, 50)
