#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: check performance of GET /ucsschool/kelvin/v1/users/USERNAME
## tags: []
## exposure: safe
## packages: []
## bugs: [53437]

CSV_FILE = "/root/kelvin_user_get_stats.csv"
URL_NAME = "/ucsschool/kelvin/v1/users"


def test_failure_count(check_failure_count):
    check_failure_count(CSV_FILE)


def test_rps(check_rps):
    check_rps(CSV_FILE, URL_NAME, 30.0)


def test_95_percentile(check_95_percentile):
    check_95_percentile(CSV_FILE, URL_NAME, 1000)
